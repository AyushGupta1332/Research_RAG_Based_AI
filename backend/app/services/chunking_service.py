"""
Research Agent — Chunking Service

Implements section-aware semantic chunking with overlap.
Chunks respect section boundaries and use sentence-level splits.
"""

import re
import logging
import tiktoken

logger = logging.getLogger(__name__)

# Default tokenizer (cl100k_base is used by most modern models)
_tokenizer = None


def _get_tokenizer():
    """Lazy-load the tokenizer."""
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = tiktoken.get_encoding("cl100k_base")
    return _tokenizer


def count_tokens(text):
    """Count tokens in a text string."""
    return len(_get_tokenizer().encode(text))


def split_into_sentences(text):
    """
    Split text into sentences using regex.
    Handles common abbreviations and decimal numbers.
    """
    # Protect common abbreviations
    text = re.sub(r'(Dr|Mr|Mrs|Ms|Prof|et al|vs|Fig|Eq|Ref|Vol|No|pp)\.',
                  r'\1<DOT>', text)
    # Protect decimal numbers
    text = re.sub(r'(\d)\.(\d)', r'\1<DOT>\2', text)

    # Split on sentence-ending punctuation followed by space and capital
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

    # Restore dots
    sentences = [s.replace('<DOT>', '.') for s in sentences]

    # Filter empty sentences
    return [s.strip() for s in sentences if s.strip()]


def chunk_section(section_content, section_name, page_start,
                  target_tokens=600, max_tokens=768, overlap_ratio=0.12):
    """
    Chunk a single section into semantically coherent pieces.

    Args:
        section_content: The text content of the section.
        section_name: Name of the section (for metadata).
        page_start: Starting page number of this section.
        target_tokens: Target chunk size in tokens (default 600).
        max_tokens: Hard maximum tokens per chunk (default 768).
        overlap_ratio: Fraction of previous chunk to overlap (default 0.12).

    Returns:
        List of dicts: [{text, token_count, page, section_name, chunk_index}]
    """
    if not section_content or not section_content.strip():
        return []

    sentences = split_into_sentences(section_content)
    if not sentences:
        return []

    chunks = []
    current_sentences = []
    current_tokens = 0
    overlap_sentences = []  # sentences from end of previous chunk for overlap

    for sentence in sentences:
        sent_tokens = count_tokens(sentence)

        # If a single sentence exceeds max, split it further by clauses
        if sent_tokens > max_tokens:
            # Force-split long sentences at clause boundaries
            sub_parts = re.split(r'[;,]\s+', sentence)
            for part in sub_parts:
                part_tokens = count_tokens(part)
                if current_tokens + part_tokens > max_tokens and current_sentences:
                    # Flush current chunk
                    chunk_text = " ".join(current_sentences)
                    chunks.append({
                        'text': chunk_text,
                        'token_count': count_tokens(chunk_text),
                        'page': page_start,
                        'section_name': section_name,
                        'chunk_index': len(chunks),
                    })
                    # Calculate overlap
                    overlap_sentences = _get_overlap_sentences(
                        current_sentences, overlap_ratio, max_tokens
                    )
                    current_sentences = list(overlap_sentences)
                    current_tokens = sum(count_tokens(s) for s in current_sentences)

                current_sentences.append(part)
                current_tokens += part_tokens
            continue

        # Check if adding this sentence would exceed target
        if current_tokens + sent_tokens > target_tokens and current_sentences:
            # Flush current chunk
            chunk_text = " ".join(current_sentences)
            chunks.append({
                'text': chunk_text,
                'token_count': count_tokens(chunk_text),
                'page': page_start,
                'section_name': section_name,
                'chunk_index': len(chunks),
            })

            # Calculate overlap sentences from end of current chunk
            overlap_sentences = _get_overlap_sentences(
                current_sentences, overlap_ratio, max_tokens
            )
            current_sentences = list(overlap_sentences)
            current_tokens = sum(count_tokens(s) for s in current_sentences)

        current_sentences.append(sentence)
        current_tokens += sent_tokens

    # Don't forget the last chunk
    if current_sentences:
        chunk_text = " ".join(current_sentences)
        chunks.append({
            'text': chunk_text,
            'token_count': count_tokens(chunk_text),
            'page': page_start,
            'section_name': section_name,
            'chunk_index': len(chunks),
        })

    return chunks


def _get_overlap_sentences(sentences, overlap_ratio, max_tokens):
    """
    Get sentences from the end of a chunk for overlap.
    Takes approximately overlap_ratio of the chunk's tokens.
    """
    if not sentences or overlap_ratio <= 0:
        return []

    total_tokens = sum(count_tokens(s) for s in sentences)
    target_overlap_tokens = int(total_tokens * overlap_ratio)

    overlap = []
    overlap_tokens = 0

    for sentence in reversed(sentences):
        sent_tokens = count_tokens(sentence)
        if overlap_tokens + sent_tokens > target_overlap_tokens and overlap:
            break
        overlap.insert(0, sentence)
        overlap_tokens += sent_tokens

    return overlap


def chunk_paper(parsed_sections, target_tokens=600, max_tokens=768, overlap_ratio=0.12):
    """
    Chunk an entire parsed paper, respecting section boundaries.

    Args:
        parsed_sections: List of ParsedSection objects from pdf_parser.
        target_tokens: Target chunk size in tokens.
        max_tokens: Hard max tokens per chunk.
        overlap_ratio: Overlap fraction between consecutive chunks.

    Returns:
        List of chunk dicts with metadata.
    """
    all_chunks = []
    global_index = 0

    for section in parsed_sections:
        section_chunks = chunk_section(
            section_content=section.content,
            section_name=section.name,
            page_start=section.page_start,
            target_tokens=target_tokens,
            max_tokens=max_tokens,
            overlap_ratio=overlap_ratio,
        )

        for chunk in section_chunks:
            chunk['global_index'] = global_index
            global_index += 1

        all_chunks.extend(section_chunks)

    logger.info(f"Chunked paper into {len(all_chunks)} chunks across {len(parsed_sections)} sections")
    return all_chunks
