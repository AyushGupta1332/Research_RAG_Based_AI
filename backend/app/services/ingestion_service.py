"""
Research Agent — Ingestion Service

Orchestrates the full paper ingestion pipeline:
    Upload → Parse → Section Detect → Chunk → Store

Runs the heavy processing in a background thread so the
upload API can return immediately.
"""

import os
import json
import logging
import threading
from datetime import datetime, timezone

from ..extensions import db
from ..models.paper import Paper, PaperSection, Chunk
from .pdf_parser import parse_pdf
from .chunking_service import chunk_paper

logger = logging.getLogger(__name__)


def save_uploaded_file(file, upload_folder, user_id):
    """
    Save an uploaded PDF file to disk and create a Paper record.

    Args:
        file: Werkzeug FileStorage object from the request.
        upload_folder: Directory to save the file.
        user_id: ID of the authenticated user.

    Returns:
        Paper object (with status='uploaded').
    """
    # Ensure upload directory exists
    user_folder = os.path.join(upload_folder, str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    # Generate a safe filename
    original_name = file.filename
    safe_name = _safe_filename(original_name)
    file_path = os.path.join(user_folder, safe_name)

    # Handle duplicates
    counter = 1
    base, ext = os.path.splitext(safe_name)
    while os.path.exists(file_path):
        safe_name = f"{base}_{counter}{ext}"
        file_path = os.path.join(user_folder, safe_name)
        counter += 1

    # Save file
    file.save(file_path)
    file_size = os.path.getsize(file_path)

    # Create database record
    paper = Paper(
        file_path=file_path,
        file_name=original_name,
        file_size=file_size,
        user_id=user_id,
        status='uploaded',
    )
    db.session.add(paper)
    db.session.commit()

    logger.info(f"Saved uploaded paper: {original_name} (id={paper.id}, {file_size} bytes)")

    return paper


def process_paper(app, paper_id):
    """
    Process a paper in a background thread.
    This is the main ingestion pipeline entry point.

    Args:
        app: Flask application (needed for app context in thread).
        paper_id: ID of the Paper to process.
    """
    thread = threading.Thread(
        target=_process_paper_worker,
        args=(app, paper_id),
        daemon=True,
    )
    thread.start()
    logger.info(f"Started background processing for paper {paper_id}")


def _process_paper_worker(app, paper_id):
    """
    Background worker that runs the full ingestion pipeline.
    Runs inside its own Flask app context.
    """
    with app.app_context():
        paper = Paper.query.get(paper_id)
        if not paper:
            logger.error(f"Paper {paper_id} not found for processing")
            return

        try:
            # Update status
            paper.status = 'processing'
            db.session.commit()

            # ── Step 1: Parse PDF ────────────────────────────────
            logger.info(f"[Paper {paper_id}] Step 1: Parsing PDF...")
            parsed = parse_pdf(paper.file_path)

            # Update paper metadata
            paper.title = parsed.title
            paper.authors = json.dumps(parsed.authors) if parsed.authors else None
            paper.abstract = parsed.abstract
            paper.page_count = parsed.page_count
            db.session.commit()

            # ── Step 2: Store sections ───────────────────────────
            logger.info(f"[Paper {paper_id}] Step 2: Storing {len(parsed.sections)} sections...")
            section_map = {}  # section_name -> PaperSection id
            for idx, section in enumerate(parsed.sections):
                db_section = PaperSection(
                    paper_id=paper.id,
                    section_name=section.name,
                    content=section.content,
                    order=idx,
                    page_start=section.page_start,
                    page_end=section.page_end,
                )
                db.session.add(db_section)
                db.session.flush()  # get the ID
                section_map[section.name] = db_section.id

            db.session.commit()

            # ── Step 3: Chunk sections ───────────────────────────
            logger.info(f"[Paper {paper_id}] Step 3: Chunking...")
            all_chunks = chunk_paper(parsed.sections)

            # ── Step 4: Store chunks ─────────────────────────────
            logger.info(f"[Paper {paper_id}] Step 4: Storing {len(all_chunks)} chunks...")
            for chunk_data in all_chunks:
                db_chunk = Chunk(
                    paper_id=paper.id,
                    section_id=section_map.get(chunk_data['section_name']),
                    text=chunk_data['text'],
                    chunk_index=chunk_data['global_index'],
                    page=chunk_data.get('page'),
                    token_count=chunk_data.get('token_count'),
                )
                db.session.add(db_chunk)

            # ── Done ─────────────────────────────────────────────
            paper.status = 'completed'
            paper.processed_date = datetime.now(timezone.utc)
            db.session.commit()

            logger.info(
                f"[Paper {paper_id}] Processing complete: "
                f"title='{paper.title}', "
                f"sections={len(parsed.sections)}, "
                f"chunks={len(all_chunks)}"
            )

            # ── Step 5: Auto-embed for retrieval (Phase 3) ──────
            try:
                from .search_service import embed_paper_chunks
                embed_count = embed_paper_chunks(app, paper_id)
                logger.info(f"[Paper {paper_id}] Auto-embedded {embed_count} chunks")
            except Exception as embed_err:
                logger.warning(
                    f"[Paper {paper_id}] Auto-embedding failed (non-fatal): {embed_err}"
                )

        except Exception as e:
            logger.error(f"[Paper {paper_id}] Processing failed: {e}", exc_info=True)
            paper.status = 'failed'
            paper.error_message = str(e)[:500]
            db.session.commit()


def reprocess_paper(app, paper_id):
    """
    Re-run the ingestion pipeline on a paper.
    Clears existing sections and chunks first.
    """
    with app.app_context():
        paper = Paper.query.get(paper_id)
        if not paper:
            return False

        # Delete existing sections and chunks (cascade handles chunks via sections)
        PaperSection.query.filter_by(paper_id=paper_id).delete()
        Chunk.query.filter_by(paper_id=paper_id).delete()
        paper.status = 'uploaded'
        paper.error_message = None
        db.session.commit()

    process_paper(app, paper_id)
    return True


def _safe_filename(filename):
    """Sanitize a filename to be safe for storage."""
    import unicodedata
    import re

    # Normalize unicode
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')

    # Replace unsafe characters
    filename = re.sub(r'[^\w\s\-.]', '', filename)
    filename = re.sub(r'\s+', '_', filename)

    if not filename:
        filename = 'unnamed_paper.pdf'

    return filename
