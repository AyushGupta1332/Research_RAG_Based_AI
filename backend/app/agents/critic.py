"""
Research Agent — Critic Agent

Verifies claims, checks citation grounding, and detects potential
hallucinations in agent outputs.
"""

from . import BaseAgent


class CriticAgent(BaseAgent):

    @property
    def name(self):
        return "critic"

    @property
    def role(self):
        return """You are a Research Critic Agent. You verify the accuracy 
and grounding of research analysis.

Your job:
1. Check if claims are supported by the source passages
2. Identify any statements that may be hallucinated
3. Verify that numbers and metrics match the source
4. Flag unsupported generalizations
5. Assess overall reliability

Be rigorous but fair. Only flag genuine issues."""

    def execute(self, context):
        """
        Critique an analysis for accuracy and grounding.

        Context:
            analysis (dict): The analysis to critique.
            passages (list): Source passages that should ground the analysis.

        Returns:
            Dict with: issues, grounding_score, verdict
        """
        analysis = context.get('analysis', {})
        passages = context.get('passages', [])

        answer = analysis.get('answer', '') if isinstance(analysis, dict) else str(analysis)
        citations = analysis.get('citations', []) if isinstance(analysis, dict) else []

        passage_text = ""
        for i, p in enumerate(passages[:8]):
            passage_text += f"[{i+1}] {p.get('paper_title', 'Unknown')}: {p.get('text', '')[:500]}\n\n"

        prompt = f"""Review this research analysis for accuracy. Check every claim 
against the source passages.

ANALYSIS TO REVIEW:
{answer}

CLAIMED CITATIONS:
{citations}

SOURCE PASSAGES:
{passage_text}

Return your review as JSON:
{{
    "issues": [
        {{
            "type": "hallucination|unsupported|inaccurate|overgeneralization",
            "claim": "the specific problematic claim",
            "explanation": "why this is an issue"
        }}
    ],
    "grounding_score": 0.0 to 1.0 (1.0 = perfectly grounded),
    "verdict": "reliable|mostly_reliable|partially_reliable|unreliable",
    "suggestions": "how to improve the analysis"
}}"""

        return self.call_llm(prompt, json_mode=True, temperature=0.1, max_tokens=2048)
