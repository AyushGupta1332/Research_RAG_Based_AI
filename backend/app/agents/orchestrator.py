"""
Research Agent — Orchestrator

Coordinates multi-agent execution: receives a user query, plans the
execution strategy, dispatches agents, and assembles the final response.

Pipeline:
    User Query → Planner → [Retrieval → Analysis → Summarization → Critic] → Response
"""

import logging
import time

logger = logging.getLogger(__name__)


def run_research_query(query, app=None, paper_id=None, chat_history=None):
    """
    Execute a full multi-agent research pipeline.

    Args:
        query: User's research question.
        app: Flask app (for app context if needed).
        paper_id: Optional paper ID to focus on.
        chat_history: Optional list of previous chat messages (dict of role, content).

    Returns:
        Dict with: report, analysis, passages, plan, trace, total_time_ms
    """
    start = time.time()
    trace = []  # Agent execution log

    from .planner import PlannerAgent
    from .retrieval import RetrievalAgent
    from .analysis import AnalysisAgent
    from .summarization import SummarizationAgent
    from .critic import CriticAgent

    # ── Step 1: Plan ──────────────────────────────────────────────
    logger.info(f"[Orchestrator] Planning for query: {query[:80]}...")

    planner = PlannerAgent()
    plan_result = planner.run({
        'query': query,
        'paper_count': _get_paper_count(app),
        'has_extractions': _has_extractions(app),
        'chat_history': chat_history or [],
    })
    trace.append(plan_result)

    if not plan_result['success']:
        # If planner fails, use default plan
        plan = _default_plan()
        logger.warning("[Orchestrator] Planner failed, using default plan")
        search_query = query
    else:
        plan = plan_result['result']
        search_query = plan.get('rewritten_query', query)

    logger.info(f"[Orchestrator] Standalone Search Query: {search_query}")
    logger.info(f"[Orchestrator] Plan: {plan.get('complexity', '?')} complexity, "
                f"{len(plan.get('tasks', []))} tasks")

    # ── Step 2: Retrieve ──────────────────────────────────────────
    retrieval = RetrievalAgent()
    retrieval_result = retrieval.run({
        'query': search_query,
        'top_k': 8,
        'paper_id': paper_id,
    })
    trace.append(retrieval_result)

    passages = []
    if retrieval_result['success']:
        passages = retrieval_result['result'].get('passages', [])
    
    if not passages:
        return {
            'report': None,
            'analysis': None,
            'passages': [],
            'plan': plan,
            'trace': _clean_trace(trace),
            'total_time_ms': round((time.time() - start) * 1000, 1),
            'error': 'No relevant passages found. Try uploading more papers or rephrasing your query.',
        }

    # ── Step 3: Analyze ───────────────────────────────────────────
    # Get extraction data if available
    extraction_data = _get_extraction_data(app, passages)

    analysis = AnalysisAgent()
    analysis_result = analysis.run({
        'query': query,
        'passages': passages,
        'extraction_data': extraction_data,
        'chat_history': chat_history or [],
    })
    trace.append(analysis_result)

    analysis_data = analysis_result.get('result', {}) if analysis_result['success'] else {}

    # ── Step 4: Summarize ─────────────────────────────────────────
    summarizer = SummarizationAgent()
    summary_result = summarizer.run({
        'query': query,
        'passages': passages,
        'analysis': analysis_data,
    })
    trace.append(summary_result)

    report_data = summary_result.get('result', {}) if summary_result['success'] else {}

    # ── Step 5: Critic (if plan includes it) ──────────────────────
    critic_data = None
    should_critique = any(
        t.get('agent') == 'critic'
        for t in plan.get('tasks', [])
    )

    if should_critique and analysis_data:
        critic = CriticAgent()
        critic_result = critic.run({
            'analysis': analysis_data,
            'passages': passages,
        })
        trace.append(critic_result)
        if critic_result['success']:
            critic_data = critic_result['result']

    total_time = (time.time() - start) * 1000
    logger.info(f"[Orchestrator] Complete in {total_time:.0f}ms — "
                f"{len(trace)} agents executed")

    return {
        'report': report_data.get('report'),
        'report_title': report_data.get('title', 'Research Report'),
        'analysis': analysis_data,
        'critic': critic_data,
        'passages': passages,
        'plan': plan,
        'trace': _clean_trace(trace),
        'total_time_ms': round(total_time, 1),
        'error': None,
    }


def _default_plan():
    """Fallback plan if the planner agent fails."""
    return {
        'tasks': [
            {'agent': 'retrieval', 'description': 'Search knowledge base'},
            {'agent': 'analysis', 'description': 'Analyze retrieved passages'},
            {'agent': 'summarization', 'description': 'Generate report'},
        ],
        'reasoning': 'Default plan (planner unavailable)',
        'complexity': 'moderate',
    }


def _get_paper_count(app):
    """Get the total number of completed papers."""
    try:
        if app:
            with app.app_context():
                from ..models.paper import Paper
                return Paper.query.filter_by(status='completed').count()
        else:
            from ..models.paper import Paper
            return Paper.query.filter_by(status='completed').count()
    except Exception:
        return 0


def _has_extractions(app):
    """Check if any papers have extractions."""
    try:
        if app:
            with app.app_context():
                from ..models.extraction import PaperExtraction
                return PaperExtraction.query.filter_by(status='completed').count() > 0
        else:
            from ..models.extraction import PaperExtraction
            return PaperExtraction.query.filter_by(status='completed').count() > 0
    except Exception:
        return False


def _get_extraction_data(app, passages):
    """Get extraction data for papers referenced in passages."""
    try:
        from ..models.extraction import PaperExtraction

        paper_ids = set(p.get('paper_id') for p in passages if p.get('paper_id'))
        extractions = {}

        for pid in paper_ids:
            ext = PaperExtraction.query.filter_by(
                paper_id=pid, status='completed'
            ).first()
            if ext:
                extractions[pid] = ext.get_extracted_data()

        return extractions if extractions else None
    except Exception:
        return None


def _clean_trace(trace):
    """Clean trace for API response (remove large data)."""
    clean = []
    for entry in trace:
        clean.append({
            'agent': entry.get('agent'),
            'success': entry.get('success'),
            'latency_ms': entry.get('latency_ms'),
            'error': entry.get('error'),
        })
    return clean
