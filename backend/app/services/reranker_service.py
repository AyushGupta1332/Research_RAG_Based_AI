"""
Research Agent — Reranker Service

Cross-encoder reranking using BAAI/bge-reranker-large (or lighter alternative).
Takes a query and candidate passages, returns re-scored results.

Design:
    - Lazy loading: model loaded on first rerank call.
    - GPU-aware: uses CUDA if available.
    - Fallback: tries bge-reranker-base if bge-reranker-large fails to load.
"""

import logging
import threading

logger = logging.getLogger(__name__)

# ─── Module-Level State ───────────────────────────────────────────
_reranker = None
_reranker_lock = threading.Lock()
_reranker_name = None
_device = None

# Models to try (smallest/fastest first)
# MiniLM-L-6 is ~90MB; bge-reranker-large is ~2.2GB
RERANKER_CANDIDATES = [
    'cross-encoder/ms-marco-MiniLM-L-6-v2',
    'BAAI/bge-reranker-base',
    'BAAI/bge-reranker-large',
]


def _load_reranker():
    """Load the cross-encoder reranker model. Thread-safe."""
    global _reranker, _reranker_name, _device

    with _reranker_lock:
        if _reranker is not None:
            return

        try:
            import torch
            from sentence_transformers import CrossEncoder

            _device = 'cuda' if torch.cuda.is_available() else 'cpu'

            for model_name in RERANKER_CANDIDATES:
                try:
                    logger.info(f"Loading reranker: {model_name} on {_device}...")
                    _reranker = CrossEncoder(
                        model_name,
                        device=_device,
                        max_length=512,
                    )
                    _reranker_name = model_name
                    logger.info(f"Reranker loaded: {_reranker_name}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load reranker {model_name}: {e}")
                    continue

            raise RuntimeError("Could not load any reranker model")

        except ImportError as e:
            raise RuntimeError(
                f"Missing dependency for reranking: {e}. "
                f"Install with: pip install sentence-transformers"
            )


def rerank(query, results, top_k=5):
    """
    Re-rank search results using a cross-encoder.

    Args:
        query: The user's search query.
        results: List of result dicts (must have 'text' key).
        top_k: Number of top results to return after reranking.

    Returns:
        List of result dicts, re-sorted by cross-encoder score, with
        'rerank_score' added to each result.
    """
    if not results:
        return []

    if _reranker is None:
        _load_reranker()

    # Create query-passage pairs for the cross-encoder
    pairs = [(query, r['text']) for r in results]

    # Get cross-encoder scores (raw logits)
    scores = _reranker.predict(pairs, show_progress_bar=False)

    # Normalize raw logits to 0-1 using sigmoid
    import math
    def sigmoid(x):
        try:
            return 1.0 / (1.0 + math.exp(-x))
        except OverflowError:
            return 0.0 if x < 0 else 1.0

    # Add rerank scores to results
    scored_results = []
    for i, result in enumerate(results):
        r = dict(result)
        raw = float(scores[i])
        r['rerank_raw_score'] = raw           # raw logit (for debugging)
        r['rerank_score'] = sigmoid(raw)      # normalized 0-1 (for display)
        scored_results.append(r)

    # Sort by rerank score (highest first) and take top_k
    scored_results.sort(key=lambda x: x['rerank_score'], reverse=True)

    return scored_results[:top_k]


def get_reranker_info():
    """Return info about the loaded reranker."""
    return {
        'model_name': _reranker_name,
        'device': _device,
        'loaded': _reranker is not None,
    }
