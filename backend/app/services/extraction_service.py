"""
Research Agent — Extraction Service

Orchestrates LLM-powered structured knowledge extraction from papers.
Uses the ingested sections/chunks to build context, sends to LLM,
validates the response, and stores the extracted data.

Pipeline:
    Paper (completed) → Build Context → LLM Extraction → Validate → Store
"""

import json
import logging
import threading
from datetime import datetime, timezone

from ..extensions import db
from ..models.paper import Paper, PaperSection
from .llm_provider import get_llm_provider, generate_json
from .extraction_prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    FULL_EXTRACTION_PROMPT,
    SUMMARY_PROMPT,
)

logger = logging.getLogger(__name__)

# Maximum characters to send to LLM (to stay within context window)
MAX_CONTEXT_CHARS = 28000  # ~7000 tokens at 4 chars/token, leaving room for prompt + response


def extract_paper_knowledge(app, paper_id):
    """
    Run extraction in a background thread.

    Args:
        app: Flask application.
        paper_id: ID of the paper to extract from.
    """
    thread = threading.Thread(
        target=_extraction_worker,
        args=(app, paper_id),
        daemon=True,
    )
    thread.start()
    logger.info(f"Started extraction for paper {paper_id}")


def _extraction_worker(app, paper_id):
    """Background worker for extraction pipeline."""
    with app.app_context():
        from ..models.extraction import PaperExtraction

        paper = Paper.query.get(paper_id)
        if not paper:
            logger.error(f"Paper {paper_id} not found for extraction")
            return

        if paper.status != 'completed':
            logger.warning(f"Paper {paper_id} not in completed status, skipping extraction")
            return

        # Check if extraction already exists
        existing = PaperExtraction.query.filter_by(paper_id=paper_id).first()
        if existing:
            existing.status = 'processing'
            existing.error_message = None
            db.session.commit()
            extraction = existing
        else:
            extraction = PaperExtraction(
                paper_id=paper_id,
                status='processing',
            )
            db.session.add(extraction)
            db.session.commit()

        try:
            # ── Step 1: Build context from paper sections ─────────
            logger.info(f"[Extract {paper_id}] Building context...")
            context = _build_paper_context(paper)

            # ── Step 2: Full extraction ───────────────────────────
            logger.info(f"[Extract {paper_id}] Running LLM extraction...")
            extraction_data, response = generate_json(
                prompt=FULL_EXTRACTION_PROMPT.format(paper_content=context),
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=4096,
            )

            # ── Step 3: Generate summary ──────────────────────────
            logger.info(f"[Extract {paper_id}] Generating summary...")
            summary_data, summary_response = generate_json(
                prompt=SUMMARY_PROMPT.format(paper_content=context),
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=2048,
            )

            # ── Step 4: Validate and store ────────────────────────
            logger.info(f"[Extract {paper_id}] Validating and storing...")
            validated = _validate_extraction(extraction_data)

            # Store results
            extraction.extracted_data = json.dumps(validated, ensure_ascii=False)
            extraction.summary_data = json.dumps(summary_data, ensure_ascii=False)
            extraction.llm_model = response.get('model', 'unknown')
            extraction.prompt_tokens = (
                response.get('usage', {}).get('prompt_tokens', 0) +
                summary_response.get('usage', {}).get('prompt_tokens', 0)
            )
            extraction.completion_tokens = (
                response.get('usage', {}).get('completion_tokens', 0) +
                summary_response.get('usage', {}).get('completion_tokens', 0)
            )
            extraction.total_tokens = (
                response.get('usage', {}).get('total_tokens', 0) +
                summary_response.get('usage', {}).get('total_tokens', 0)
            )
            extraction.latency_ms = (
                response.get('latency_ms', 0) +
                summary_response.get('latency_ms', 0)
            )
            extraction.confidence_score = validated.get('confidence_score', 0.0)
            extraction.status = 'completed'
            extraction.extracted_at = datetime.now(timezone.utc)
            db.session.commit()

            logger.info(
                f"[Extract {paper_id}] Complete: "
                f"confidence={extraction.confidence_score:.2f}, "
                f"tokens={extraction.total_tokens}, "
                f"latency={extraction.latency_ms:.0f}ms"
            )

        except Exception as e:
            logger.error(f"[Extract {paper_id}] Failed: {e}", exc_info=True)
            extraction.status = 'failed'
            extraction.error_message = str(e)[:500]
            db.session.commit()


def _build_paper_context(paper):
    """
    Build a text context from a paper's sections for LLM input.
    Prioritizes abstract, introduction, methodology, and results.
    Truncates to stay within context limits.
    """
    sections = (
        PaperSection.query
        .filter_by(paper_id=paper.id)
        .order_by(PaperSection.order)
        .all()
    )

    if not sections:
        return f"Title: {paper.title or paper.file_name}\n\nNo sections available."

    # Priority sections (most important first)
    priority_order = [
        'abstract', 'introduction', 'methodology', 'method', 'methods',
        'proposed', 'approach', 'model', 'architecture',
        'experiments', 'results', 'evaluation',
        'discussion', 'conclusion', 'conclusions',
        'related work', 'background',
        'limitations', 'future work',
    ]

    # Sort sections by priority
    def section_priority(section):
        name_lower = section.section_name.lower()
        for i, keyword in enumerate(priority_order):
            if keyword in name_lower:
                return i
        return len(priority_order)  # unmatched sections go last

    sorted_sections = sorted(sections, key=section_priority)

    # Build context string
    parts = []
    parts.append(f"TITLE: {paper.title or paper.file_name}")

    if paper.authors:
        try:
            authors = json.loads(paper.authors)
            parts.append(f"AUTHORS: {', '.join(authors)}")
        except (json.JSONDecodeError, TypeError):
            pass

    if paper.abstract:
        parts.append(f"\nABSTRACT:\n{paper.abstract}")

    total_chars = sum(len(p) for p in parts)

    for section in sorted_sections:
        section_text = f"\n--- {section.section_name.upper()} ---\n{section.content}"

        if total_chars + len(section_text) > MAX_CONTEXT_CHARS:
            # Truncate this section to fit
            remaining = MAX_CONTEXT_CHARS - total_chars - 50
            if remaining > 200:
                parts.append(section_text[:remaining] + "\n[TRUNCATED]")
            break

        parts.append(section_text)
        total_chars += len(section_text)

    return "\n".join(parts)


def _validate_extraction(data):
    """
    Validate and normalize the extracted data.
    Ensures all expected fields exist with correct types.
    """
    validated = {}

    # String fields
    for field in ['title', 'paper_type', 'research_domain', 'summary']:
        validated[field] = str(data.get(field, '')) if data.get(field) else None

    # Array of strings
    for field in ['key_findings', 'limitations', 'future_work']:
        val = data.get(field, [])
        validated[field] = [str(v) for v in val] if isinstance(val, list) else []

    # Authors
    authors = data.get('authors', [])
    validated['authors'] = [str(a) for a in authors] if isinstance(authors, list) else []

    # Complex arrays
    for field in ['datasets', 'architectures', 'methods', 'metrics']:
        val = data.get(field, [])
        validated[field] = val if isinstance(val, list) else []

    # Training details
    td = data.get('training_details', {})
    validated['training_details'] = td if isinstance(td, dict) else {}

    # Numeric fields
    validated['references_count'] = int(data.get('references_count', 0)) if data.get('references_count') else 0
    validated['confidence_score'] = min(1.0, max(0.0, float(data.get('confidence_score', 0.5))))

    return validated


def get_extraction_for_paper(paper_id):
    """Get the extraction data for a paper, if it exists."""
    from ..models.extraction import PaperExtraction

    extraction = PaperExtraction.query.filter_by(paper_id=paper_id).first()
    if not extraction:
        return None

    return extraction.to_dict()
