"""
Research Agent — Query API Blueprint

Handles search queries against the research knowledge base.
Supports hybrid search (BM25 + dense + reranking).

Endpoints:
    POST /api/query/         — Full hybrid search
    POST /api/query/embed/<id> — Trigger embedding for a paper
    GET  /api/query/stats    — Retrieval system stats
    POST /api/query/reindex  — Rebuild all indices
"""

import logging
import threading
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services import search_service, bm25_service
from ..utils.responses import success_response, error_response

logger = logging.getLogger(__name__)

query_bp = Blueprint('query', __name__)


@query_bp.route('/', methods=['POST'])
@jwt_required()
def query_papers():
    """
    Search the research knowledge base using hybrid retrieval.

    Request body (JSON):
        query (str): Required — the search query.
        top_k (int): Number of results (default 5, max 20).
        use_reranker (bool): Whether to use cross-encoder reranking (default true).
        paper_id (int): Optional — filter results to a specific paper.
        bm25_weight (float): BM25 weight in fusion (default 0.4).
        dense_weight (float): Dense weight in fusion (default 0.6).

    Returns:
        List of search results with scores and metadata.
    """
    data = request.get_json()

    if not data or not data.get('query'):
        return error_response('Query text is required', 400)

    query_text = data['query'].strip()
    if len(query_text) < 3:
        return error_response('Query must be at least 3 characters', 400)

    top_k = min(data.get('top_k', 5), 20)
    use_reranker = data.get('use_reranker', True)
    paper_filter = data.get('paper_id')
    bm25_weight = data.get('bm25_weight', 0.4)
    dense_weight = data.get('dense_weight', 0.6)

    try:
        results = search_service.hybrid_search(
            query=query_text,
            top_k=top_k,
            use_reranker=use_reranker,
            bm25_weight=bm25_weight,
            dense_weight=dense_weight,
            paper_filter=paper_filter,
        )

        # Enrich results with paper titles
        _enrich_results(results['results'])

        return success_response({
            'results': results['results'],
            'metadata': results['metadata'],
        })

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return error_response(f'Search failed: {str(e)}', 500)


@query_bp.route('/embed/<int:paper_id>', methods=['POST'])
@jwt_required()
def embed_paper(paper_id):
    """
    Trigger embedding generation for a specific paper.
    Chunks must already exist (paper must be in 'completed' status).
    """
    from ..models.paper import Paper

    user_id = int(get_jwt_identity())
    paper = Paper.query.filter_by(id=paper_id, user_id=user_id).first()

    if not paper:
        return error_response('Paper not found', 404)

    if paper.status != 'completed':
        return error_response(
            f'Paper is not ready for embedding (status: {paper.status}). '
            f'Paper must be in "completed" status.',
            400
        )

    # Run embedding in background thread
    app = current_app._get_current_object()

    def _embed_bg():
        try:
            count = search_service.embed_paper_chunks(app, paper_id)
            logger.info(f"Background embedding done: paper_id={paper_id}, chunks={count}")
        except Exception as e:
            logger.error(f"Background embedding failed for paper {paper_id}: {e}", exc_info=True)

    thread = threading.Thread(target=_embed_bg, daemon=True)
    thread.start()

    return success_response(
        {'paper_id': paper_id},
        'Embedding started in background'
    )


@query_bp.route('/stats', methods=['GET'])
@jwt_required()
def search_stats():
    """Get retrieval system statistics."""
    try:
        stats = search_service.get_search_stats()
        return success_response({'stats': stats})
    except Exception as e:
        logger.error(f"Failed to get search stats: {e}", exc_info=True)
        return error_response(f'Failed to get stats: {str(e)}', 500)


@query_bp.route('/reindex', methods=['POST'])
@jwt_required()
def reindex():
    """Rebuild all search indices (BM25 + re-embed all papers)."""
    app = current_app._get_current_object()

    def _reindex_bg():
        try:
            bm25_service.build_index(app)
            logger.info("BM25 index rebuilt via /reindex")
        except Exception as e:
            logger.error(f"Reindex failed: {e}", exc_info=True)

    thread = threading.Thread(target=_reindex_bg, daemon=True)
    thread.start()

    return success_response(message='Reindexing started in background')


def _enrich_results(results):
    """Add paper title to each result."""
    from ..models.paper import Paper

    paper_cache = {}
    for r in results:
        pid = r.get('paper_id')
        if pid and pid not in paper_cache:
            paper = Paper.query.get(pid)
            paper_cache[pid] = paper.title if paper else 'Unknown'

        r['paper_title'] = paper_cache.get(pid, 'Unknown')


@query_bp.route('/research', methods=['POST'])
@jwt_required()
def research_query():
    """
    Run a multi-agent research query.

    This is the main AI-powered research endpoint. It:
    1. Plans the query execution strategy
    2. Retrieves relevant passages
    3. Analyzes the content with an LLM
    4. Generates a structured report
    5. Optionally critiques the output for hallucinations

    Request body:
        query (str): Required — the research question.
        paper_id (int): Optional — focus on a specific paper.

    Returns:
        report, analysis, passages, plan, trace, timing
    """
    data = request.get_json()

    if not data or not data.get('query'):
        return error_response('Research query is required', 400)

    query_text = data['query'].strip()
    if len(query_text) < 5:
        return error_response('Query must be at least 5 characters', 400)

    paper_id = data.get('paper_id')

    # Check LLM availability
    from ..services.llm_provider import get_llm_provider
    provider = get_llm_provider()
    if not provider.is_available():
        return error_response(
            'LLM provider not configured. Set GROQ_API_KEY in .env',
            503
        )

    try:
        from ..agents.orchestrator import run_research_query
        result = run_research_query(
            query=query_text,
            paper_id=paper_id,
        )

        return success_response(result)

    except Exception as e:
        logger.error(f"Research query failed: {e}", exc_info=True)
        return error_response(f'Research query failed: {str(e)}', 500)


@query_bp.route('/evaluate', methods=['GET'])
@jwt_required()
def get_evaluation():
    """Get the current system grounding and audit stats from past database interactions."""
    try:
        from ..services.evaluation_service import _get_db_grounding_stats
        app = current_app._get_current_object()
        stats = _get_db_grounding_stats(app)
        return success_response({'grounding_stats': stats})
    except Exception as e:
        logger.error(f"Failed to get evaluation stats: {e}", exc_info=True)
        return error_response(f'Failed to get stats: {str(e)}', 500)


@query_bp.route('/evaluate/run', methods=['POST'])
@jwt_required()
def run_evaluation():
    """Run a live retrieval search benchmarking process against the evaluation dataset."""
    try:
        from ..services.evaluation_service import run_system_evaluation
        app = current_app._get_current_object()
        results = run_system_evaluation(app)
        
        if 'error' in results:
            return error_response(results['error'], 400)
            
        return success_response(results)
    except Exception as e:
        logger.error(f"Failed to run system evaluation: {e}", exc_info=True)
        return error_response(f'Failed to run evaluation: {str(e)}', 500)

