"""
Research Agent — Papers API Blueprint

Handles paper upload, listing, detail view, and deletion.
Upload triggers background ingestion processing.
"""

import os
import logging
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..models.paper import Paper, PaperSection, Chunk
from ..extensions import db
from ..services.ingestion_service import save_uploaded_file, process_paper, reprocess_paper
from ..utils.responses import success_response, error_response

logger = logging.getLogger(__name__)

papers_bp = Blueprint('papers', __name__)


@papers_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_paper():
    """
    Upload a research paper PDF.

    Accepts: multipart/form-data with a 'file' field containing a PDF.
    Returns: Paper record with status 'uploaded'.
    Processing starts automatically in the background.
    """
    if 'file' not in request.files:
        return error_response('No file provided', 400)

    file = request.files['file']

    if not file.filename:
        return error_response('No file selected', 400)

    if not file.filename.lower().endswith('.pdf'):
        return error_response('Only PDF files are accepted', 400)

    user_id = int(get_jwt_identity())
    upload_folder = current_app.config.get(
        'UPLOAD_FOLDER',
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
    )

    try:
        # Save file and create DB record
        paper = save_uploaded_file(file, upload_folder, user_id)

        # Start background processing
        process_paper(current_app._get_current_object(), paper.id)

        return success_response(
            {'paper': paper.to_dict()},
            'Paper uploaded and processing started',
            201
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        return error_response(f'Upload failed: {str(e)}', 500)


@papers_bp.route('/', methods=['GET'])
@jwt_required()
def list_papers():
    """
    List all papers for the authenticated user.

    Query params:
        status: Filter by status (uploaded, processing, completed, failed)
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)
    """
    user_id = int(get_jwt_identity())

    query = Paper.query.filter_by(user_id=user_id)

    # Filter by status
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    # Order by newest first
    query = query.order_by(Paper.upload_date.desc())

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return success_response({
        'papers': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })


@papers_bp.route('/<int:paper_id>', methods=['GET'])
@jwt_required()
def get_paper(paper_id):
    """
    Get detailed information about a specific paper.
    Includes sections and their chunk counts.
    """
    user_id = int(get_jwt_identity())
    paper = Paper.query.filter_by(id=paper_id, user_id=user_id).first()

    if not paper:
        return error_response('Paper not found', 404)

    return success_response({
        'paper': paper.to_dict(include_sections=True)
    })


@papers_bp.route('/<int:paper_id>/chunks', methods=['GET'])
@jwt_required()
def get_paper_chunks(paper_id):
    """
    Get all chunks for a specific paper.

    Query params:
        section_id: Filter chunks by section
        page: Page number
        per_page: Items per page (default 50)
    """
    user_id = int(get_jwt_identity())
    paper = Paper.query.filter_by(id=paper_id, user_id=user_id).first()

    if not paper:
        return error_response('Paper not found', 404)

    query = Chunk.query.filter_by(paper_id=paper_id)

    section_id = request.args.get('section_id', type=int)
    if section_id:
        query = query.filter_by(section_id=section_id)

    query = query.order_by(Chunk.chunk_index)

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 200)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return success_response({
        'chunks': [c.to_dict() for c in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })


@papers_bp.route('/<int:paper_id>/reprocess', methods=['POST'])
@jwt_required()
def reprocess_paper_endpoint(paper_id):
    """Re-run ingestion on a paper (clears existing sections/chunks)."""
    user_id = int(get_jwt_identity())
    paper = Paper.query.filter_by(id=paper_id, user_id=user_id).first()

    if not paper:
        return error_response('Paper not found', 404)

    reprocess_paper(current_app._get_current_object(), paper_id)

    return success_response(
        {'paper_id': paper_id},
        'Reprocessing started'
    )


@papers_bp.route('/<int:paper_id>', methods=['DELETE'])
@jwt_required()
def delete_paper(paper_id):
    """Delete a paper and all its sections, chunks, and the PDF file."""
    user_id = int(get_jwt_identity())
    paper = Paper.query.filter_by(id=paper_id, user_id=user_id).first()

    if not paper:
        return error_response('Paper not found', 404)

    # Delete the PDF file
    try:
        if os.path.exists(paper.file_path):
            os.remove(paper.file_path)
    except OSError as e:
        logger.warning(f"Failed to delete file {paper.file_path}: {e}")

    # Delete the DB record (cascades to sections and chunks)
    db.session.delete(paper)
    db.session.commit()

    logger.info(f"Deleted paper {paper_id}")

    return success_response(message='Paper deleted successfully')


@papers_bp.route('/<int:paper_id>/extract', methods=['POST'])
@jwt_required()
def extract_paper(paper_id):
    """
    Trigger LLM-powered knowledge extraction for a paper.
    Paper must be in 'completed' status (ingestion done).
    """
    user_id = int(get_jwt_identity())
    paper = Paper.query.filter_by(id=paper_id, user_id=user_id).first()

    if not paper:
        return error_response('Paper not found', 404)

    if paper.status != 'completed':
        return error_response(
            f'Paper must be in "completed" status (current: {paper.status})',
            400
        )

    # Check LLM availability
    from ..services.llm_provider import get_llm_provider
    provider = get_llm_provider()
    if not provider.is_available():
        return error_response(
            'LLM provider not configured. Set GROQ_API_KEY in .env',
            503
        )

    # Start extraction in background
    from ..services.extraction_service import extract_paper_knowledge
    extract_paper_knowledge(current_app._get_current_object(), paper_id)

    return success_response(
        {'paper_id': paper_id},
        'Extraction started in background'
    )


@papers_bp.route('/<int:paper_id>/extraction', methods=['GET'])
@jwt_required()
def get_extraction(paper_id):
    """Get the extraction results for a paper."""
    user_id = int(get_jwt_identity())
    paper = Paper.query.filter_by(id=paper_id, user_id=user_id).first()

    if not paper:
        return error_response('Paper not found', 404)

    from ..services.extraction_service import get_extraction_for_paper
    extraction = get_extraction_for_paper(paper_id)

    if not extraction:
        return success_response({
            'extraction': None,
            'has_extraction': False,
        })

    return success_response({
        'extraction': extraction,
        'has_extraction': True,
    })


@papers_bp.route('/<int:paper_id>/extract', methods=['DELETE'])
@jwt_required()
def delete_extraction(paper_id):
    """Delete extraction data for a paper (to allow re-extraction)."""
    from ..models.extraction import PaperExtraction

    user_id = int(get_jwt_identity())
    paper = Paper.query.filter_by(id=paper_id, user_id=user_id).first()

    if not paper:
        return error_response('Paper not found', 404)

    extraction = PaperExtraction.query.filter_by(paper_id=paper_id).first()
    if extraction:
        db.session.delete(extraction)
        db.session.commit()
        logger.info(f"Deleted extraction for paper {paper_id}")

    return success_response(message='Extraction deleted')
