"""
Research Agent — Vector Store Service

ChromaDB-based vector storage for dense retrieval.
Manages a persistent collection of chunk embeddings with metadata.

Design:
    - Persistent storage: ChromaDB data saved to disk (survives restarts).
    - Upsert semantics: re-embedding a chunk replaces the old embedding.
    - Metadata filtering: supports filtering by paper_id, section, etc.
"""

import os
import logging
import threading

logger = logging.getLogger(__name__)

# ─── Module-Level State ───────────────────────────────────────────
_client = None
_collection = None
_init_lock = threading.Lock()

COLLECTION_NAME = "research_chunks"


def _get_persist_dir():
    """Get the ChromaDB persist directory (relative to backend/)."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    persist_dir = os.path.join(backend_dir, 'instance', 'chromadb')
    os.makedirs(persist_dir, exist_ok=True)
    return persist_dir


def _init_chromadb():
    """Initialize the ChromaDB client and collection. Thread-safe."""
    global _client, _collection

    with _init_lock:
        if _collection is not None:
            return

        try:
            import chromadb

            persist_dir = _get_persist_dir()
            logger.info(f"Initializing ChromaDB (persist_dir={persist_dir})...")

            _client = chromadb.PersistentClient(path=persist_dir)
            _collection = _client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},  # cosine similarity
            )

            count = _collection.count()
            logger.info(f"ChromaDB ready: collection='{COLLECTION_NAME}', vectors={count}")

        except ImportError:
            raise RuntimeError(
                "ChromaDB not installed. Install with: pip install chromadb"
            )


def get_collection():
    """Get the ChromaDB collection (initializes if needed)."""
    if _collection is None:
        _init_chromadb()
    return _collection


def add_embeddings(chunk_ids, embeddings, texts, metadatas):
    """
    Add or update embeddings in the vector store.

    Args:
        chunk_ids: List of unique string IDs (e.g., "chunk_42").
        embeddings: List of embedding vectors (lists of floats).
        texts: List of chunk text strings (stored as documents).
        metadatas: List of metadata dicts (paper_id, section_name, etc.).
    """
    collection = get_collection()

    # ChromaDB requires string IDs
    str_ids = [str(cid) for cid in chunk_ids]

    # Convert numpy arrays to lists if needed
    emb_lists = [
        e.tolist() if hasattr(e, 'tolist') else list(e)
        for e in embeddings
    ]

    # Upsert in batches (ChromaDB handles up to ~40k at once, but batching is safer)
    batch_size = 500
    for i in range(0, len(str_ids), batch_size):
        end = min(i + batch_size, len(str_ids))
        collection.upsert(
            ids=str_ids[i:end],
            embeddings=emb_lists[i:end],
            documents=texts[i:end],
            metadatas=metadatas[i:end],
        )

    logger.info(f"Upserted {len(str_ids)} embeddings into ChromaDB")


def query_similar(query_embedding, top_k=20, where_filter=None):
    """
    Query the vector store for similar chunks.

    Args:
        query_embedding: The query embedding vector.
        top_k: Number of results to return.
        where_filter: Optional ChromaDB where filter (e.g., {"paper_id": 5}).

    Returns:
        List of dicts with keys: id, text, metadata, distance, score.
    """
    collection = get_collection()

    emb_list = (
        query_embedding.tolist()
        if hasattr(query_embedding, 'tolist')
        else list(query_embedding)
    )

    query_params = {
        'query_embeddings': [emb_list],
        'n_results': top_k,
        'include': ['documents', 'metadatas', 'distances'],
    }
    if where_filter:
        query_params['where'] = where_filter

    results = collection.query(**query_params)

    # Parse results into a cleaner format
    parsed = []
    if results and results['ids'] and results['ids'][0]:
        for i, chunk_id in enumerate(results['ids'][0]):
            distance = results['distances'][0][i]
            # ChromaDB cosine distance is 1 - cosine_similarity
            score = 1.0 - distance

            parsed.append({
                'id': chunk_id,
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': distance,
                'score': score,  # cosine similarity (0-1)
            })

    return parsed


def delete_by_paper(paper_id):
    """Delete all embeddings for a given paper_id."""
    collection = get_collection()

    try:
        # Get IDs matching this paper_id
        results = collection.get(
            where={"paper_id": paper_id},
            include=[],
        )
        if results and results['ids']:
            collection.delete(ids=results['ids'])
            logger.info(f"Deleted {len(results['ids'])} vectors for paper_id={paper_id}")
            return len(results['ids'])
    except Exception as e:
        logger.warning(f"Error deleting vectors for paper {paper_id}: {e}")

    return 0


def get_stats():
    """Get vector store statistics."""
    collection = get_collection()
    count = collection.count()
    return {
        'total_vectors': count,
        'collection_name': COLLECTION_NAME,
        'persist_dir': _get_persist_dir(),
    }


def reset_collection():
    """Delete and recreate the collection (for testing)."""
    global _collection, _client

    if _client is not None:
        try:
            _client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    _collection = None
    _init_chromadb()
    logger.info("ChromaDB collection reset")
