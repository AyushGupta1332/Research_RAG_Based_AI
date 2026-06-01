"""
Research Agent — Evaluation Service

Performs automated benchmarking of the hybrid search engine (BM25 + dense + reranking).
Computes Precision@K, Recall@K, MRR, and NDCG using a pre-defined evaluation dataset.
Logs component latencies and parses persistent assistant chat grounding histories.
"""

import os
import json
import time
import math
import logging
from flask import current_app

from . import search_service
from ..models.memory import ResearchMessage

logger = logging.getLogger(__name__)


def run_system_evaluation(app=None):
    """
    Run automated hybrid retrieval benchmarks using the evaluation dataset.
    
    Returns:
        Dict of results containing retriever_accuracy, component_latencies, and grounding_stats.
    """
    if app is None:
        app = current_app._get_current_object()

    # 1. Load evaluation dataset
    dataset_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'utils', 'evaluation_dataset.json'
    )
    
    if not os.path.exists(dataset_path):
        logger.error(f"Evaluation dataset not found at: {dataset_path}")
        return {'error': 'Evaluation dataset not found'}

    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
    except Exception as e:
        logger.error(f"Failed to parse evaluation dataset: {e}")
        return {'error': f'Failed to parse dataset: {str(e)}'}

    eval_results = []
    latencies = {
        'total': [],
        'bm25': [],
        'dense': [],
        'rrf': [],
        'rerank': []
    }

    # 2. Benchmark each query in the dataset
    for item in dataset:
        query = item.get('query')
        expected_paper = item.get('expected_paper_title', '').lower()
        expected_section = item.get('expected_section', '').lower()
        query_type = item.get('query_type', 'general')

        try:
            # Execute hybrid search with top_k = 5
            search_res = search_service.hybrid_search(
                query=query,
                top_k=5,
                use_reranker=True
            )
            
            results = search_res.get('results', [])
            meta = search_res.get('metadata', {})

            # Track component latencies
            latencies['total'].append(meta.get('total_time_ms', 0))
            latencies['bm25'].append(meta.get('bm25_time_ms', 0))
            latencies['dense'].append(meta.get('dense_time_ms', 0))
            latencies['rrf'].append(meta.get('rrf_time_ms', 0))
            latencies['rerank'].append(meta.get('rerank_time_ms', 0))

            # Evaluate matches
            relevant_found = 0
            first_rank = None
            dcg = 0.0

            for i, p in enumerate(results):
                p_title = p.get('paper_title', '').lower()
                p_sec = p.get('section_name', '').lower()

                # Robust substring match for relevance
                is_paper_match = expected_paper in p_title or p_title in expected_paper
                is_sec_match = expected_section in p_sec or p_sec in expected_section

                if is_paper_match and is_sec_match:
                    relevant_found += 1
                    if first_rank is None:
                        first_rank = i + 1  # 1-indexed
                    # Binary relevance DCG contribution
                    dcg += 1.0 / math.log2(i + 2)

            # Accuracy calculations
            precision_5 = relevant_found / 5.0
            recall_5 = 1.0 if relevant_found > 0 else 0.0
            rr = 1.0 / first_rank if first_rank is not None else 0.0
            
            # Ideal DCG is 1.0 since at least one ground truth exists
            ndcg_5 = dcg / 1.0 if dcg <= 1.0 else 1.0

            eval_results.append({
                'query': query,
                'query_type': query_type,
                'results_count': len(results),
                'relevant_found': relevant_found,
                'precision_5': precision_5,
                'recall_5': recall_5,
                'reciprocal_rank': rr,
                'ndcg_5': ndcg_5,
                'latency_ms': meta.get('total_time_ms', 0)
            })

        except Exception as ex:
            logger.error(f"Failed to benchmark query '{query}': {ex}", exc_info=True)
            continue

    if not eval_results:
        return {'error': 'No queries were successfully evaluated'}

    # 3. Aggregate Retriever Accuracy
    avg_precision = sum(r['precision_5'] for r in eval_results) / len(eval_results)
    avg_recall = sum(r['recall_5'] for r in eval_results) / len(eval_results)
    mrr = sum(r['reciprocal_rank'] for r in eval_results) / len(eval_results)
    avg_ndcg = sum(r['ndcg_5'] for r in eval_results) / len(eval_results)

    retriever_accuracy = {
        'precision_5': round(avg_precision * 100, 1),
        'recall_5': round(avg_recall * 100, 1),
        'mrr': round(mrr * 100, 1),
        'ndcg_5': round(avg_ndcg * 100, 1),
        'total_evaluated': len(eval_results),
        'details': eval_results
    }

    # 4. Aggregate Latencies (averages)
    avg_latencies = {
        k: round(sum(v) / len(v), 1) if v else 0.0 for k, v in latencies.items()
    }

    # 5. Extract grounding history statistics from database
    grounding_stats = _get_db_grounding_stats(app)

    return {
        'retriever_accuracy': retriever_accuracy,
        'component_latencies': avg_latencies,
        'grounding_stats': grounding_stats,
        'timestamp': time.time()
    }


def _get_db_grounding_stats(app):
    """Aggregate grounding and verdict stats from ResearchMessage database logs."""
    stats = {
        'avg_grounding_score': 0.0,
        'verdict_counts': {
            'reliable': 0,
            'mostly_reliable': 0,
            'partially_reliable': 0,
            'unreliable': 0
        },
        'total_audited_messages': 0
    }

    try:
        with app.app_context():
            # Get all assistant messages containing agent_data
            messages = ResearchMessage.query.filter(
                ResearchMessage.role == 'assistant',
                ResearchMessage.agent_data.isnot(None)
            ).all()

            grounding_scores = []
            for m in messages:
                data = m.get_agent_data()
                if not data or not data.get('critic'):
                    continue

                critic = data['critic']
                score = critic.get('grounding_score', 0)
                verdict = critic.get('verdict')

                grounding_scores.append(score)
                if verdict in stats['verdict_counts']:
                    stats['verdict_counts'][verdict] += 1
                stats['total_audited_messages'] += 1

            if grounding_scores:
                stats['avg_grounding_score'] = round((sum(grounding_scores) / len(grounding_scores)) * 100, 1)

    except Exception as e:
        logger.error(f"Failed to load database grounding stats: {e}")

    return stats
