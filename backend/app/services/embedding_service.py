"""
Research Agent — Embedding Service

Generates dense embeddings using BAAI/bge-m3 (or fallback to bge-small-en-v1.5).
Uses GPU (CUDA) if available, otherwise falls back to CPU.

Design:
    - Lazy model loading: model is loaded on first embed call, not at import time.
    - Batch embedding: chunks are embedded in configurable batches for GPU efficiency.
    - Thread-safe: uses a threading lock for model loading.
"""

import logging
import threading
import numpy as np

logger = logging.getLogger(__name__)

# ─── Module-Level State ───────────────────────────────────────────
_model = None
_model_lock = threading.Lock()
_model_name = None
_device = None
_embedding_dim = None


# ─── Model Configuration ─────────────────────────────────────────

# Ordered list of models to try (fastest-to-download first)
# bge-small is ~33MB and loads in seconds; bge-m3 is ~2GB
MODEL_CANDIDATES = [
    {
        'name': 'BAAI/bge-small-en-v1.5',
        'dim': 384,
        'description': 'Fast, lightweight (~33MB download)',
    },
    {
        'name': 'BAAI/bge-m3',
        'dim': 1024,
        'description': 'Best quality, multilingual (~2GB download)',
    },
]

DEFAULT_BATCH_SIZE = 32


def _load_model():
    """
    Load the embedding model. Tries bge-m3 first, falls back to bge-small.
    Called lazily on first use — thread-safe via lock.
    """
    global _model, _model_name, _device, _embedding_dim

    with _model_lock:
        if _model is not None:
            return  # Already loaded by another thread

        try:
            import torch
            from sentence_transformers import SentenceTransformer

            # Detect device
            if torch.cuda.is_available():
                _device = 'cuda'
                try:
                    props = torch.cuda.get_device_properties(0)
                    vram_gb = getattr(props, 'total_memory', getattr(props, 'total_mem', 0)) / (1024 ** 3)
                    logger.info(f"CUDA available: {torch.cuda.get_device_name(0)} ({vram_gb:.1f} GB VRAM)")
                except Exception as e:
                    logger.warning(f"Failed to query CUDA properties: {e}. Using device name fallback.")
                    vram_gb = 0
                    logger.info("CUDA available: Yes (Properties lookup skipped)")
            else:
                _device = 'cpu'
                logger.info("No CUDA GPU detected — using CPU for embeddings")

            # Try loading models in order
            for candidate in MODEL_CANDIDATES:
                try:
                    logger.info(f"Loading embedding model: {candidate['name']}...")
                    _model = SentenceTransformer(
                        candidate['name'],
                        device=_device,
                        trust_remote_code=True,
                    )
                    _model_name = candidate['name']
                    _embedding_dim = candidate['dim']
                    logger.info(
                        f"Loaded {_model_name} on {_device} "
                        f"(dim={_embedding_dim})"
                    )
                    return
                except Exception as e:
                    logger.warning(f"Failed to load {candidate['name']}: {e}")
                    continue

            raise RuntimeError("Could not load any embedding model")

        except ImportError as e:
            raise RuntimeError(
                f"Missing dependency for embeddings: {e}. "
                f"Install with: pip install sentence-transformers torch"
            )


def get_model_info():
    """Return information about the currently loaded (or to-be-loaded) model."""
    if _model is not None:
        return {
            'model_name': _model_name,
            'device': _device,
            'embedding_dim': _embedding_dim,
            'loaded': True,
        }
    return {
        'model_name': None,
        'device': None,
        'embedding_dim': None,
        'loaded': False,
        'candidates': [c['name'] for c in MODEL_CANDIDATES],
    }


def embed_texts(texts, batch_size=DEFAULT_BATCH_SIZE, show_progress=False):
    """
    Generate embeddings for a list of text strings.

    Args:
        texts: List of strings to embed.
        batch_size: Number of texts to process at once (default 32).
        show_progress: Whether to show a progress bar.

    Returns:
        numpy.ndarray of shape (len(texts), embedding_dim).
    """
    if not texts:
        return np.array([])

    # Ensure model is loaded
    if _model is None:
        _load_model()

    logger.info(f"Embedding {len(texts)} texts (batch_size={batch_size})...")

    embeddings = _model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        normalize_embeddings=True,  # L2 normalize for cosine similarity
    )

    logger.info(f"Generated {len(embeddings)} embeddings (shape={embeddings.shape})")
    return embeddings


def embed_single(text):
    """Embed a single text string. Returns a 1D numpy array."""
    if _model is None:
        _load_model()

    embedding = _model.encode(
        text,
        normalize_embeddings=True,
    )
    return embedding


def get_embedding_dim():
    """Return the embedding dimension of the loaded model."""
    if _model is None:
        _load_model()
    return _embedding_dim


def get_model_name():
    """Return the name of the loaded model."""
    if _model is None:
        _load_model()
    return _model_name
