"""
Research Agent — Summarization Agent

Generates structured research summaries from retrieved content.
Produces markdown reports, comparison tables, and literature summaries.
"""

from . import BaseAgent


class SummarizationAgent(BaseAgent):

    @property
    def name(self):
        return "summarization"

    @property
    def role(self):
        return """You are a Research Summarization Agent. You create clear,
well-structured summaries of research content.

RULES:
1. Summarize ONLY what the provided content says — never add information.
2. Use clear, academic language.
3. Organize content logically with headers and bullet points.
4. Include relevant metrics and numbers when available.
5. Always cite the source paper for each point.
6. Use markdown formatting in the report."""

    def execute(self, context):
        """
        Generate a research summary from retrieved/analyzed content.

        Context:
            query (str): The original question.
            passages (list): Retrieved passages.
            analysis (dict, optional): Analysis from the Analysis Agent.

        Returns:
            Dict with: report (markdown string), title, word_count
        """
        query = context.get('query', '')
        passages = context.get('passages', [])
        analysis = context.get('analysis', {})

        # Build context
        passage_text = ""
        for i, p in enumerate(passages[:8]):
            source = p.get('paper_title', 'Unknown')
            passage_text += f"[{i+1}] From: {source}\n{p.get('text', '')}\n\n"

        analysis_text = ""
        if analysis:
            if analysis.get('answer'):
                analysis_text = f"PREVIOUS ANALYSIS:\n{analysis['answer']}\n"
            if analysis.get('key_points'):
                analysis_text += "\nKEY POINTS:\n"
                for kp in analysis['key_points']:
                    analysis_text += f"- {kp}\n"

        prompt = f"""Generate a comprehensive research report answering this question:

QUESTION: "{query}"

SOURCE PASSAGES:
{passage_text}

{analysis_text}

Write a well-structured markdown report. Include:
1. A concise title
2. An executive summary (2-3 sentences)
3. Detailed findings organized by theme
4. Key metrics/numbers if available
5. A brief conclusion

Return as JSON:
{{
    "title": "report title",
    "report": "full markdown report text",
    "word_count": approximate word count
}}"""

        return self.call_llm(prompt, json_mode=True, temperature=0.3, max_tokens=4096)
