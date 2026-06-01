"""
Research Agent — Retrieval Agent

Searches the knowledge base and assembles relevant context.
Wraps the hybrid search pipeline (BM25 + Dense + Reranker).
"""

from . import BaseAgent


class RetrievalAgent(BaseAgent):

    @property
    def name(self):
        return "retrieval"

    @property
    def role(self):
        return "You are a Research Retrieval Agent. You search knowledge bases for relevant information."

    def execute(self, context):
        """
        Search the knowledge base for relevant passages.

        Context:
            query (str): Search query.
            top_k (int): Number of results (default 8).
            paper_id (int, optional): Filter to specific paper.

        Returns:
            Dict with: passages (list), query (str), count (int)
        """
        from ..services.search_service import hybrid_search

        query = context.get('query', '')
        top_k = context.get('top_k', 8)
        paper_filter = context.get('paper_id')

        results = hybrid_search(
            query=query,
            top_k=top_k,
            use_reranker=True,
            paper_filter=paper_filter,
        )

        passages = []
        for r in results.get('results', []):
            passages.append({
                'text': r.get('text', ''),
                'paper_id': r.get('paper_id'),
                'paper_title': r.get('paper_title', 'Unknown'),
                'section': r.get('section_name', ''),
                'page': r.get('page'),
                'relevance': r.get('rerank_score', r.get('rrf_score', 0)),
            })

        return {
            'passages': passages,
            'query': query,
            'count': len(passages),
            'search_metadata': results.get('metadata', {}),
        }
