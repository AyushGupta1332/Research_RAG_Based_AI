"""
Research Agent — Extraction Model

Database model for storing LLM-extracted structured knowledge from papers.
"""

import json
from datetime import datetime, timezone
from ..extensions import db


class PaperExtraction(db.Model):
    """Stores LLM-extracted structured knowledge for a paper."""

    __tablename__ = 'paper_extractions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'), nullable=False, unique=True)

    # Extraction data (JSON strings)
    extracted_data = db.Column(db.Text, nullable=True)   # Full extraction JSON
    summary_data = db.Column(db.Text, nullable=True)     # Summary JSON

    # Status
    status = db.Column(
        db.String(20),
        default='pending',
        nullable=False
    )  # pending, processing, completed, failed
    error_message = db.Column(db.Text, nullable=True)

    # LLM metadata
    llm_model = db.Column(db.String(100), nullable=True)
    prompt_tokens = db.Column(db.Integer, nullable=True)
    completion_tokens = db.Column(db.Integer, nullable=True)
    total_tokens = db.Column(db.Integer, nullable=True)
    latency_ms = db.Column(db.Float, nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)

    # Timestamps
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    extracted_at = db.Column(db.DateTime, nullable=True)

    # Relationship
    paper = db.relationship('Paper', backref=db.backref('extraction', uselist=False))

    def get_extracted_data(self):
        """Parse and return the extracted data dict."""
        if not self.extracted_data:
            return {}
        try:
            return json.loads(self.extracted_data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_summary_data(self):
        """Parse and return the summary data dict."""
        if not self.summary_data:
            return {}
        try:
            return json.loads(self.summary_data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def to_dict(self):
        """Serialize extraction to dictionary."""
        return {
            'id': self.id,
            'paper_id': self.paper_id,
            'status': self.status,
            'error_message': self.error_message,
            'extracted_data': self.get_extracted_data(),
            'summary_data': self.get_summary_data(),
            'llm_model': self.llm_model,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'latency_ms': self.latency_ms,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
        }

    def __repr__(self):
        return f'<PaperExtraction paper_id={self.paper_id} status={self.status}>'
