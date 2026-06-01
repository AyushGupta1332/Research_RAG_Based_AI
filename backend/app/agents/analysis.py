"""
Research Agent — Analysis Agent

Analyzes retrieved passages and extracted data to answer research questions.
Focuses on methodology comparison, insight extraction, and benchmarking.
"""

from . import BaseAgent


class AnalysisAgent(BaseAgent):

    @property
    def name(self):
        return "analysis"

    @property
    def role(self):
        return """You are a Research Analysis Agent. You analyze academic papers 
and research content to provide deep, structured insights.

Your capabilities:
- Compare methodologies across papers
- Identify strengths and weaknesses of approaches
- Analyze experimental results and metrics
- Extract relationships between concepts
- Identify research gaps

RULES:
1. Base ALL analysis on the provided passages — never fabricate information.
2. Cite specific papers/sections when making claims.
3. Be precise about numbers and metrics.
4. Distinguish between what the paper claims vs what you infer.
5. Always respond with valid JSON."""

    def execute(self, context):
        """
        Analyze retrieved passages to answer a research question.

        Context:
            query (str): The research question.
            passages (list): Retrieved passages from the knowledge base.
            extraction_data (dict, optional): Extracted paper metadata.

        Returns:
            Dict with: analysis, key_points, citations
        """
        query = context.get('query', '')
        passages = context.get('passages', [])
        extraction_data = context.get('extraction_data', {})
        chat_history = context.get('chat_history', [])

        # Build context from passages
        passage_text = self._format_passages(passages)
        extraction_text = self._format_extraction(extraction_data)

        # Format chat history for context
        history_text = ""
        if chat_history:
            history_text = "CONVERSATION HISTORY:\n"
            for msg in chat_history:
                role = "User" if msg.get('role') == 'user' else "Assistant"
                content = msg.get('content', '')
                if role == "Assistant" and len(content) > 500:
                    content = content[:500] + "... [truncated]"
                history_text += f"{role}: {content}\n"
            history_text += "\n"

        prompt = f"""Analyze the following research content to answer this question.

{history_text}QUESTION: "{query}"

RETRIEVED PASSAGES:
{passage_text}

{f"EXTRACTED METADATA:{chr(10)}{extraction_text}" if extraction_text else ""}

Provide a thorough analysis as JSON:
{{
    "answer": "direct, comprehensive answer to the question (2-4 paragraphs)",
    "key_points": [
        "key insight or finding 1",
        "key insight or finding 2"
    ],
    "citations": [
        {{
            "claim": "specific claim made in the answer",
            "source": "paper title or section name",
            "page": page number or null
        }}
    ],
    "confidence": 0.0 to 1.0,
    "limitations": "any caveats or limitations of this analysis"
}}"""

        return self.call_llm(prompt, json_mode=True, temperature=0.2, max_tokens=4096)

    def _format_passages(self, passages):
        if not passages:
            return "No passages available."

        parts = []
        for i, p in enumerate(passages[:10]):  # Limit to 10 passages
            source = f"[{p.get('paper_title', 'Unknown')}]"
            section = f" — {p['section']}" if p.get('section') else ""
            page = f" (Page {p['page']})" if p.get('page') else ""
            parts.append(f"[{i+1}] {source}{section}{page}\n{p.get('text', '')}\n")
        return "\n".join(parts)

    def _format_extraction(self, data):
        if not data:
            return ""
        import json
        return json.dumps(data, indent=2, default=str)[:3000]
