"""
Research Agent — Search Service (Hybrid Orchestrator)

Orchestrates the full hybrid retrieval pipeline:
    Query → BM25 + Dense → Reciprocal Rank Fusion → Reranker → Final Results

This is the main entry point for all search functionality.
"""

import logging
import threading

from . import embedding_service
from . import vector_store
from . import bm25_service
from . import reranker_service

logger = logging.getLogger(__name__)


def hybrid_search(query, top_k=5, use_reranker=True,
                  bm25_weight=0.4, dense_weight=0.6,
                  bm25_candidates=20, dense_candidates=20,
                  paper_filter=None):
    """
    Perform hybrid search: BM25 + Dense + RRF + Reranking.

    Args:
        query: The user's search query.
        top_k: Number of final results to return.
        use_reranker: Whether to apply cross-encoder reranking.
        bm25_weight: Weight for BM25 in RRF (default 0.4).
        dense_weight: Weight for dense retrieval in RRF (default 0.6).
        bm25_candidates: Number of BM25 candidates to retrieve.
        dense_candidates: Number of dense candidates to retrieve.
        paper_filter: Optional paper_id to filter results.

    Returns:
        Dict with:
            results: List of ranked result dicts.
            metadata: Search metadata (timings, counts, etc.).
    """
    import time
    start_time = time.time()
    metadata = {
        'query': query,
        'top_k': top_k,
        'use_reranker': use_reranker,
        'bm25_weight': bm25_weight,
        'dense_weight': dense_weight,
    }

    # ── Step 1: BM25 Sparse Retrieval ─────────────────────────────
    bm25_start = time.time()
    bm25_results = bm25_service.search(query, top_k=bm25_candidates)
    bm25_time = time.time() - bm25_start
    metadata['bm25_count'] = len(bm25_results)
    metadata['bm25_time_ms'] = round(bm25_time * 1000, 1)
    logger.info(f"BM25: {len(bm25_results)} results in {bm25_time:.3f}s")

    # ── Step 2: Dense Retrieval ───────────────────────────────────
    dense_start = time.time()
    where_filter = {"paper_id": paper_filter} if paper_filter else None

    query_embedding = embedding_service.embed_single(query)
    dense_results = vector_store.query_similar(
        query_embedding,
        top_k=dense_candidates,
        where_filter=where_filter,
    )
    dense_time = time.time() - dense_start
    metadata['dense_count'] = len(dense_results)
    metadata['dense_time_ms'] = round(dense_time * 1000, 1)
    logger.info(f"Dense: {len(dense_results)} results in {dense_time:.3f}s")

    # ── Step 3: Reciprocal Rank Fusion ────────────────────────────
    rrf_start = time.time()
    fused_results = reciprocal_rank_fusion(
        bm25_results=bm25_results,
        dense_results=dense_results,
        bm25_weight=bm25_weight,
        dense_weight=dense_weight,
        top_k=bm25_candidates + dense_candidates,  # reranker will trim
    )
    rrf_time = time.time() - rrf_start
    metadata['rrf_candidates'] = len(fused_results)
    metadata['rrf_time_ms'] = round(rrf_time * 1000, 1)

    # ── Step 4: Cross-Encoder Reranking ───────────────────────────
    if use_reranker and fused_results:
        rerank_start = time.time()
        try:
            final_results = reranker_service.rerank(
                query, fused_results, top_k=top_k
            )
            rerank_time = time.time() - rerank_start
            metadata['rerank_time_ms'] = round(rerank_time * 1000, 1)
            metadata['reranked'] = True
            logger.info(f"Reranker: {len(final_results)} results in {rerank_time:.3f}s")
        except Exception as e:
            logger.warning(f"Reranker failed, using RRF results: {e}")
            final_results = fused_results[:top_k]
            metadata['reranked'] = False
            metadata['rerank_error'] = str(e)
    else:
        final_results = fused_results[:top_k]
        metadata['reranked'] = False

    total_time = time.time() - start_time
    metadata['total_time_ms'] = round(total_time * 1000, 1)
    metadata['result_count'] = len(final_results)

    logger.info(f"Search complete: {len(final_results)} results in {total_time:.3f}s")

    return {
        'results': final_results,
        'metadata': metadata,
    }


def reciprocal_rank_fusion(bm25_results, dense_results,
                           bm25_weight=0.4, dense_weight=0.6,
                           k=60, top_k=40):
    """
    Merge BM25 and dense results using Reciprocal Rank Fusion (RRF).

    RRF score for document d: sum over ranklists R of w_R / (k + rank(d, R))

    Args:
        bm25_results: BM25 search results (list of dicts).
        dense_results: Dense search results (list of dicts).
        bm25_weight: Weight for BM25 scores.
        dense_weight: Weight for dense scores.
        k: RRF constant (default 60).
        top_k: Number of results to return after fusion.

    Returns:
        List of fused results, sorted by RRF score.
    """
    scores = {}  # chunk_id -> {'rrf_score': float, 'data': dict}

    # Process BM25 results
    for rank, result in enumerate(bm25_results):
        chunk_id = result.get('chunk_id', f"chunk_{result.get('id', rank)}")
        rrf_score = bm25_weight / (k + rank + 1)

        if chunk_id not in scores:
            scores[chunk_id] = {
                'rrf_score': 0,
                'data': result,
                'bm25_score': result.get('score', 0),
                'bm25_rank': rank + 1,
            }
        scores[chunk_id]['rrf_score'] += rrf_score

    # Process dense results
    for rank, result in enumerate(dense_results):
        chunk_id = result.get('id', f"chunk_{rank}")
        rrf_score = dense_weight / (k + rank + 1)

        if chunk_id not in scores:
            scores[chunk_id] = {
                'rrf_score': 0,
                'data': {
                    'id': chunk_id,
                    'chunk_id': chunk_id,
                    'text': result.get('text', ''),
                    'paper_id': result.get('metadata', {}).get('paper_id'),
                    'section_name': result.get('metadata', {}).get('section_name'),
                    'page': result.get('metadata', {}).get('page'),
                },
            }
        scores[chunk_id]['rrf_score'] += rrf_score
        scores[chunk_id]['dense_score'] = result.get('score', 0)
        scores[chunk_id]['dense_rank'] = rank + 1

    # Build final results sorted by RRF score
    fused = []
    for chunk_id, entry in scores.items():
        result = dict(entry['data'])
        result['rrf_score'] = entry['rrf_score']
        result['bm25_score'] = entry.get('bm25_score', 0)
        result['dense_score'] = entry.get('dense_score', 0)
        result['bm25_rank'] = entry.get('bm25_rank')
        result['dense_rank'] = entry.get('dense_rank')
        fused.append(result)

    fused.sort(key=lambda x: x['rrf_score'], reverse=True)

    return fused[:top_k]


def embed_paper_chunks(app, paper_id):
    """
    Embed all chunks of a paper and store them in the vector store.
    Should be called after ingestion completes.

    Args:
        app: Flask application (for app context).
        paper_id: ID of the paper to embed.
    """
    with app.app_context():
        from ..models.paper import Chunk

        chunks = Chunk.query.filter_by(paper_id=paper_id).order_by(Chunk.chunk_index).all()

        if not chunks:
            logger.warning(f"No chunks found for paper {paper_id}")
            return 0

        # Prepare data
        texts = [c.text for c in chunks]
        chunk_ids = [f"chunk_{c.id}" for c in chunks]
        metadatas = [
            {
                'paper_id': c.paper_id,
                'section_name': c.section.section_name if c.section else 'unknown',
                'chunk_index': c.chunk_index,
                'page': c.page or 0,
            }
            for c in chunks
        ]

        # Generate embeddings
        logger.info(f"Embedding {len(texts)} chunks for paper {paper_id}...")
        embeddings = embedding_service.embed_texts(texts)

        # Update chunks with embedding model info
        model_name = embedding_service.get_model_name()
        for chunk in chunks:
            chunk.embedding_model = model_name
        from ..extensions import db
        db.session.commit()

        # Store in vector store
        vector_store.add_embeddings(chunk_ids, embeddings, texts, metadatas)

        # Rebuild BM25 index to include new chunks
        bm25_service.build_index(app)

        logger.info(f"Embedded and indexed {len(texts)} chunks for paper {paper_id}")
        return len(texts)


def get_search_stats(app=None):
    """Get overall search system statistics."""
    stats = {
        'embedding': embedding_service.get_model_info(),
        'vector_store': vector_store.get_stats(),
        'bm25': bm25_service.get_index_stats(),
        'reranker': reranker_service.get_reranker_info(),
    }
    return stats
