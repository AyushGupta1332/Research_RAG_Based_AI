"""
Research Agent — PDF Parser Service

Extracts text, metadata, and structural information from research PDFs
using PyMuPDF (fitz). Detects sections by analyzing heading patterns.
"""

import re
import logging
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


# Common section headings found in research papers
PREFIX = r'^(?:(?:[IVXLCDM]+|\d+)(?:\.\d+)*\.?\s+)?'
SECTION_PATTERNS = [
    PREFIX + r'(abstract)$',
    PREFIX + r'(introduction)$',
    PREFIX + r'(related\s+work)$',
    PREFIX + r'(background)$',
    PREFIX + r'(literature\s+review)$',
    PREFIX + r'(methodology|methods?)$',
    PREFIX + r'(proposed\s+(?:method|approach|system|framework|model))$',
    PREFIX + r'(system\s+(?:design|architecture|overview))$',
    PREFIX + r'(experiment(?:s|al)?(?:\s+(?:setup|results|design))?)$',
    PREFIX + r'(results?\s*(?:and\s+)?(?:discussion|analysis)?)$',
    PREFIX + r'(discussion)$',
    PREFIX + r'(evaluation)$',
    PREFIX + r'(analysis)$',
    PREFIX + r'(implementation)$',
    PREFIX + r'(dataset(?:s)?)$',
    PREFIX + r'(conclusion(?:s)?(?:\s+and\s+future\s+work)?)$',
    PREFIX + r'(future\s+work)$',
    PREFIX + r'(limitations?)$',
    PREFIX + r'(acknowledg(?:e)?ments?)$',
    PREFIX + r'(references|bibliography)$',
    PREFIX + r'(appendi(?:x|ces))$',
    # Numbered/Roman section pattern: "I. Something" or "1. Something" or "2.3 Something"
    r'^((?:[IVXLCDM]+|\d+)(?:\.\d+)*\.?\s+[A-Z][A-Za-z\s\-]{2,50})$',
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SECTION_PATTERNS]


class ParsedPage:
    """Represents a parsed page of a PDF."""

    def __init__(self, page_num, text, blocks=None):
        self.page_num = page_num
        self.text = text
        self.blocks = blocks or []


class ParsedSection:
    """Represents a detected section in the paper."""

    def __init__(self, name, content, page_start, page_end=None):
        self.name = name
        self.content = content
        self.page_start = page_start
        self.page_end = page_end or page_start


class ParsedPaper:
    """Complete parse result for a research paper."""

    def __init__(self):
        self.title = None
        self.authors = []
        self.abstract = None
        self.page_count = 0
        self.sections = []     # list of ParsedSection
        self.full_text = ""
        self.pages = []        # list of ParsedPage


def parse_pdf(file_path):
    """
    Parse a research paper PDF and extract structured information.

    Args:
        file_path: Path to the PDF file.

    Returns:
        ParsedPaper object with extracted metadata and sections.
    """
    logger.info(f"Parsing PDF: {file_path}")

    result = ParsedPaper()

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logger.error(f"Failed to open PDF: {e}")
        raise ValueError(f"Cannot open PDF file: {e}")

    result.page_count = len(doc)

    # ── Step 1: Extract text from all pages ──────────────────────
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        result.pages.append(ParsedPage(page_num + 1, text, blocks))

    result.full_text = "\n".join(p.text for p in result.pages)

    # ── Step 2: Extract title (usually largest text on first page)
    result.title = _extract_title(result.pages[0] if result.pages else None)

    # ── Step 3: Extract authors (text below title, before abstract)
    result.authors = _extract_authors(result.pages[0] if result.pages else None, result.title)

    # ── Step 4: Detect sections ──────────────────────────────────
    result.sections = _detect_sections(result.pages)

    # ── Step 5: Extract abstract from sections ───────────────────
    for section in result.sections:
        if section.name.lower().strip() in ('abstract',):
            result.abstract = section.content.strip()
            break

    doc.close()

    logger.info(
        f"Parsed PDF: {result.title or 'Unknown'}, "
        f"{result.page_count} pages, {len(result.sections)} sections"
    )

    return result


def _extract_title(first_page):
    """
    Extract the paper title from the first page.
    Strategy: Find the largest font text block on page 1.
    """
    if not first_page or not first_page.blocks:
        return None

    largest_font_size = 0
    title_text = ""

    for block in first_page.blocks:
        if block.get("type") != 0:  # only text blocks
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                font_size = span.get("size", 0)
                text = span.get("text", "").strip()
                if font_size > largest_font_size and len(text) > 3:
                    largest_font_size = font_size
                    title_text = text

    # Sometimes title spans multiple spans with same large font
    if first_page.blocks:
        title_parts = []
        for block in first_page.blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if abs(span.get("size", 0) - largest_font_size) < 0.5:
                        title_parts.append(span.get("text", "").strip())

        combined = " ".join(title_parts).strip()
        if combined and len(combined) > len(title_text):
            title_text = combined

    return title_text if title_text else None


def _extract_authors(first_page, title):
    """
    Extract authors from the first page.
    Strategy: Text between title and abstract, look for name-like patterns.
    """
    if not first_page:
        return []

    text = first_page.text
    lines = text.split('\n')

    authors = []
    title_found = False
    abstract_found = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip until after title
        if not title_found:
            if title and stripped.lower() in title.lower():
                title_found = True
            continue

        # Stop at abstract
        if re.match(r'^(?:\d+\.?\s+)?abstract', stripped, re.IGNORECASE):
            break

        # Skip lines that look like affiliations, emails, or dates
        if '@' in stripped or re.match(r'^\d{4}', stripped):
            continue
        if len(stripped) < 3:
            continue

        # Lines with commas or "and" between names
        if re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', stripped):
            # Split by comma or "and"
            names = re.split(r',\s*|\s+and\s+', stripped)
            for name in names:
                name = name.strip()
                # Name-like: 2-4 words starting with capitals
                if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+){0,2}$', name):
                    authors.append(name)

        if len(authors) >= 10:  # sanity limit
            break

    return authors


def _detect_sections(pages):
    """
    Detect section boundaries in the paper.
    Strategy: Look for lines matching known section heading patterns.
    """
    sections = []
    current_section_name = "Preamble"
    current_section_content = []
    current_page_start = 1

    for page in pages:
        lines = page.text.split('\n')

        for line in lines:
            stripped = line.strip()
            if not stripped:
                current_section_content.append("")
                continue

            # Check if this line is a section heading
            is_heading = False
            heading_name = stripped

            for pattern in COMPILED_PATTERNS:
                match = pattern.match(stripped)
                if match:
                    # Verify it's short enough to be a heading (not a sentence)
                    if len(stripped) < 80:
                        is_heading = True
                        # Use the matched group if available, else the full match
                        heading_name = match.group(1) if match.lastindex else stripped
                        heading_name = heading_name.strip()
                        break

            if is_heading and current_section_content:
                # Save the previous section
                content = "\n".join(current_section_content).strip()
                if content:
                    sections.append(ParsedSection(
                        name=current_section_name,
                        content=content,
                        page_start=current_page_start,
                        page_end=page.page_num
                    ))

                # Start new section
                current_section_name = heading_name
                current_section_content = []
                current_page_start = page.page_num
            else:
                current_section_content.append(stripped)

    # Don't forget the last section
    if current_section_content:
        content = "\n".join(current_section_content).strip()
        if content:
            sections.append(ParsedSection(
                name=current_section_name,
                content=content,
                page_start=current_page_start,
                page_end=pages[-1].page_num if pages else 1
            ))

    # If no sections detected, create one big section
    if not sections:
        full_text = "\n".join(p.text for p in pages).strip()
        if full_text:
            sections.append(ParsedSection(
                name="Full Text",
                content=full_text,
                page_start=1,
                page_end=len(pages)
            ))

    return sections
