"""
Research Agent — Paper Models

Database models for research papers, sections, and chunks.
These form the core data layer for the ingestion pipeline.
"""

from datetime import datetime, timezone
from ..extensions import db


class Paper(db.Model):
    """A research paper uploaded to the system."""

    __tablename__ = 'papers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(500), nullable=True)
    authors = db.Column(db.Text, nullable=True)          # JSON string of author list
    abstract = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(500), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)      # bytes
    page_count = db.Column(db.Integer, nullable=True)
    status = db.Column(
        db.String(20),
        default='uploaded',
        nullable=False
    )  # uploaded, processing, completed, failed
    error_message = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    upload_date = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    processed_date = db.Column(db.DateTime, nullable=True)

    # Relationships
    sections = db.relationship(
        'PaperSection', backref='paper', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    chunks = db.relationship(
        'Chunk', backref='paper', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def to_dict(self, include_sections=False):
        """Serialize paper to dictionary."""
        import json
        data = {
            'id': self.id,
            'title': self.title or self.file_name,
            'authors': json.loads(self.authors) if self.authors else [],
            'abstract': self.abstract,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'page_count': self.page_count,
            'status': self.status,
            'error_message': self.error_message,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'processed_date': self.processed_date.isoformat() if self.processed_date else None,
            'chunk_count': self.chunks.count(),
            'section_count': self.sections.count(),
        }
        if include_sections:
            data['sections'] = [s.to_dict() for s in self.sections.order_by(PaperSection.order)]
        return data

    def __repr__(self):
        return f'<Paper {self.id}: {self.title or self.file_name}>'


class PaperSection(db.Model):
    """A logical section extracted from a research paper."""

    __tablename__ = 'paper_sections'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'), nullable=False)
    section_name = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)
    page_start = db.Column(db.Integer, nullable=True)
    page_end = db.Column(db.Integer, nullable=True)

    # Relationships
    section_chunks = db.relationship(
        'Chunk', backref='section', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def to_dict(self, include_chunks=False):
        """Serialize section to dictionary."""
        data = {
            'id': self.id,
            'section_name': self.section_name,
            'content_length': len(self.content),
            'order': self.order,
            'page_start': self.page_start,
            'page_end': self.page_end,
            'chunk_count': self.section_chunks.count(),
        }
        if include_chunks:
            data['chunks'] = [c.to_dict() for c in self.section_chunks.order_by(Chunk.chunk_index)]
        return data

    def __repr__(self):
        return f'<PaperSection {self.section_name}>'


class Chunk(db.Model):
    """A text chunk from a paper section, ready for embedding."""

    __tablename__ = 'chunks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('paper_sections.id'), nullable=True)
    text = db.Column(db.Text, nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False, default=0)
    page = db.Column(db.Integer, nullable=True)
    token_count = db.Column(db.Integer, nullable=True)
    embedding_model = db.Column(db.String(100), nullable=True)  # set in Phase 3
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self):
        """Serialize chunk to dictionary."""
        return {
            'id': self.id,
            'paper_id': self.paper_id,
            'section_id': self.section_id,
            'section_name': self.section.section_name if self.section else None,
            'text': self.text,
            'chunk_index': self.chunk_index,
            'page': self.page,
            'token_count': self.token_count,
        }

    def __repr__(self):
        return f'<Chunk {self.id} (paper={self.paper_id}, idx={self.chunk_index})>'
