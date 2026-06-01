"""
Research Agent — BM25 Sparse Search Service

Implements BM25-based sparse retrieval using rank-bm25.
Maintains an in-memory BM25 index that's rebuilt from the database.

Design:
    - Index rebuilt on demand (after new papers are embedded).
    - Simple tokenization with stop word removal.
    - Thread-safe index rebuilding.
"""

import re
import logging
import threading

logger = logging.getLogger(__name__)

# ─── Module-Level State ───────────────────────────────────────────
_bm25_index = None
_chunk_data = []  # List of dicts: {id, text, paper_id, section_name, ...}
_index_lock = threading.Lock()
_is_built = False

# Basic English stop words
STOP_WORDS = frozenset([
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'shall', 'can', 'it', 'its',
    'this', 'that', 'these', 'those', 'i', 'we', 'you', 'he', 'she',
    'they', 'them', 'my', 'our', 'your', 'his', 'her', 'their',
    'what', 'which', 'who', 'whom', 'when', 'where', 'why', 'how',
    'not', 'no', 'nor', 'if', 'then', 'than', 'so', 'as', 'such',
    'also', 'very', 'just', 'about', 'above', 'after', 'before',
])


def tokenize(text):
    """
    Simple tokenizer: lowercase, split on non-alpha, remove stop words.
    """
    # Lowercase and split on non-alphanumeric
    tokens = re.findall(r'[a-z0-9]+', text.lower())
    # Remove stop words and short tokens
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


def build_index(app=None):
    """
    Build (or rebuild) the BM25 index from all chunks in the database.

    Args:
        app: Flask app for app context (needed if called from background thread).
    """
    global _bm25_index, _chunk_data, _is_built

    def _build():
        global _bm25_index, _chunk_data, _is_built

        with _index_lock:
            from rank_bm25 import BM25Okapi
            from ..models.paper import Chunk, Paper

            # Fetch all chunks from completed papers
            chunks = (
                Chunk.query
                .join(Paper, Chunk.paper_id == Paper.id)
                .filter(Paper.status == 'completed')
                .all()
            )

            if not chunks:
                logger.info("No chunks found — BM25 index is empty")
                _bm25_index = None
                _chunk_data = []
                _is_built = True
                return

            # Build corpus
            _chunk_data = []
            tokenized_corpus = []

            for chunk in chunks:
                tokens = tokenize(chunk.text)
                tokenized_corpus.append(tokens)
                _chunk_data.append({
                    'id': chunk.id,
                    'chunk_id': f"chunk_{chunk.id}",
                    'text': chunk.text,
                    'paper_id': chunk.paper_id,
                    'section_id': chunk.section_id,
                    'section_name': chunk.section.section_name if chunk.section else None,
                    'chunk_index': chunk.chunk_index,
                    'page': chunk.page,
                    'token_count': chunk.token_count,
                })

            _bm25_index = BM25Okapi(tokenized_corpus)
            _is_built = True
            logger.info(f"BM25 index built with {len(_chunk_data)} chunks")

    if app is not None:
        with app.app_context():
            _build()
    else:
        _build()


def search(query_text, top_k=20):
    """
    Search the BM25 index.

    Args:
        query_text: The search query string.
        top_k: Number of results to return.

    Returns:
        List of dicts: {id, chunk_id, text, score, paper_id, section_name, ...}
    """
    if not _is_built or _bm25_index is None:
        logger.warning("BM25 index not built — returning empty results")
        return []

    query_tokens = tokenize(query_text)
    if not query_tokens:
        return []

    scores = _bm25_index.get_scores(query_tokens)

    # Get top-K indices
    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )[:top_k]

    results = []
    for idx in top_indices:
        if scores[idx] > 0:  # Only include matches with positive score
            result = dict(_chunk_data[idx])
            result['score'] = float(scores[idx])
            results.append(result)

    return results


def is_index_built():
    """Check if the BM25 index has been built."""
    return _is_built


def get_index_stats():
    """Get BM25 index statistics."""
    return {
        'is_built': _is_built,
        'total_documents': len(_chunk_data),
        'has_index': _bm25_index is not None,
    }
