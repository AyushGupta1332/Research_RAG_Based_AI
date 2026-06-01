"""
Research Agent — Memory Models

Database models for persistent conversation sessions and message history.
This forms the basis of Phase 7 (Memory Architecture).
"""

import json
from datetime import datetime, timezone
from ..extensions import db


class ResearchSession(db.Model):
    """A conversational research session (chat thread)."""

    __tablename__ = 'research_sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False, default='New Research Session')
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    messages = db.relationship(
        'ResearchMessage', backref='session', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    user = db.relationship('User', backref=db.backref('sessions', lazy='dynamic'))

    def to_dict(self):
        """Serialize session to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'message_count': self.messages.count(),
        }

    def __repr__(self):
        return f'<ResearchSession {self.id}: {self.title}>'


class ResearchMessage(db.Model):
    """An individual message (turn) in a research session."""

    __tablename__ = 'research_messages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey('research_sessions.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    agent_data = db.Column(db.Text, nullable=True)   # JSON string of orchestrator metadata
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def get_agent_data(self):
        """Parse and return the agent data dict."""
        if not self.agent_data:
            return None
        try:
            return json.loads(self.agent_data)
        except (json.JSONDecodeError, TypeError):
            return None

    def to_dict(self):
        """Serialize message to dictionary."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role,
            'content': self.content,
            'agent_data': self.get_agent_data(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<ResearchMessage {self.id} (session={self.session_id}, role={self.role})>'
