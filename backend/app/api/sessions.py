"""
Research Agent — Sessions API Blueprint

Handles conversational research threads (sessions) and chat message history.
Enables multi-turn conversational agents with relative context.
"""

import json
import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..models.memory import ResearchSession, ResearchMessage
from ..extensions import db
from ..utils.responses import success_response, error_response

logger = logging.getLogger(__name__)

sessions_bp = Blueprint('sessions', __name__)


@sessions_bp.route('/', methods=['GET'])
@jwt_required()
def list_sessions():
    """List all research sessions for the authenticated user, ordered by newest first."""
    user_id = int(get_jwt_identity())
    sessions = ResearchSession.query.filter_by(user_id=user_id).order_by(ResearchSession.updated_at.desc()).all()
    return success_response({
        'sessions': [s.to_dict() for s in sessions]
    })


@sessions_bp.route('/', methods=['POST'])
@jwt_required()
def create_session():
    """Create a new blank research session thread."""
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    title = data.get('title', 'New Research Session').strip()

    try:
        session = ResearchSession(user_id=user_id, title=title)
        db.session.add(session)
        db.session.commit()
        logger.info(f"Created research session {session.id} for user {user_id}")
        return success_response(session.to_dict(), 'Session created successfully', 201)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create session: {e}", exc_info=True)
        return error_response(f'Failed to create session: {str(e)}', 500)


@sessions_bp.route('/<int:session_id>', methods=['GET'])
@jwt_required()
def get_session_details(session_id):
    """Retrieve all messages in a specific research session thread."""
    user_id = int(get_jwt_identity())
    session = ResearchSession.query.filter_by(id=session_id, user_id=user_id).first()

    if not session:
        return error_response('Research session not found', 404)

    messages = session.messages.order_by(ResearchMessage.created_at.asc()).all()

    return success_response({
        'session': session.to_dict(),
        'messages': [m.to_dict() for m in messages]
    })


@sessions_bp.route('/<int:session_id>', methods=['DELETE'])
@jwt_required()
def delete_session(session_id):
    """Delete a research session thread and all its history."""
    user_id = int(get_jwt_identity())
    session = ResearchSession.query.filter_by(id=session_id, user_id=user_id).first()

    if not session:
        return error_response('Research session not found', 404)

    try:
        db.session.delete(session)
        db.session.commit()
        logger.info(f"Deleted research session {session_id}")
        return success_response(message='Research session deleted successfully')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete session {session_id}: {e}", exc_info=True)
        return error_response(f'Failed to delete session: {str(e)}', 500)


@sessions_bp.route('/<int:session_id>/research', methods=['POST'])
@jwt_required()
def run_session_research(session_id):
    """
    Run a multi-agent research query within a persistent conversational session.
    Loads prior turns, resolves pronouns, updates and saves conversation turns.
    """
    user_id = int(get_jwt_identity())
    session = ResearchSession.query.filter_by(id=session_id, user_id=user_id).first()

    if not session:
        return error_response('Research session not found', 404)

    data = request.get_json()
    if not data or not data.get('query'):
        return error_response('Research query is required', 400)

    query_text = data['query'].strip()
    if len(query_text) < 5:
        return error_response('Query must be at least 5 characters', 400)

    paper_id = data.get('paper_id')

    # Verify LLM provider configuration
    from ..services.llm_provider import get_llm_provider
    provider = get_llm_provider()
    if not provider.is_available():
        return error_response(
            'LLM provider not configured. Set GROQ_API_KEY in .env',
            503
        )

    # 1. Fetch previous session history
    prior_messages = session.messages.order_by(ResearchMessage.created_at.asc()).all()
    chat_history = [{'role': m.role, 'content': m.content} for m in prior_messages]

    try:
        # 2. Run query with history context
        from ..agents.orchestrator import run_research_query
        result = run_research_query(
            query=query_text,
            paper_id=paper_id,
            chat_history=chat_history,
        )

        if result.get('error'):
            # If orchestrator returns a graceful retrieval error, save the turns but return success with errors
            logger.warning(f"Orchestrator returned error for query: {result.get('error')}")

        # 3. Create user message turn
        user_msg = ResearchMessage(
            session_id=session.id,
            role='user',
            content=query_text
        )
        db.session.add(user_msg)

        # 4. Create assistant message turn
        assistant_content = result.get('report') or result.get('error') or "Unable to synthesize research content."
        assistant_msg = ResearchMessage(
            session_id=session.id,
            role='assistant',
            content=assistant_content,
            agent_data=json.dumps(result)
        )
        db.session.add(assistant_msg)

        # 5. Dynamically rename session if title is default
        if session.title == 'New Research Session':
            # Cut at 45 chars for title
            new_title = query_text[:42] + '...' if len(query_text) > 45 else query_text
            session.title = new_title

        # Update updated timestamp
        session.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info(f"Conversational research step completed on session {session.id}")
        return success_response(assistant_msg.to_dict(), 'Research turn completed successfully')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Session research turn failed: {e}", exc_info=True)
        return error_response(f'Research failed: {str(e)}', 500)
