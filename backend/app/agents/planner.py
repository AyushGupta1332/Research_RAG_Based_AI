"""
Research Agent — Planner Agent

Decomposes a user's research query into a structured task plan.
Decides which agents to invoke and in what order.
"""

from . import BaseAgent


class PlannerAgent(BaseAgent):

    @property
    def name(self):
        return "planner"

    @property
    def role(self):
        return """You are a Research Planning Agent. Your job is to analyze a user's 
research query and decompose it into a structured plan of sub-tasks.

You decide which specialized agents to invoke:
- "retrieval": Search the knowledge base for relevant passages
- "analysis": Analyze methodology, compare approaches, extract insights
- "summarization": Generate a structured summary or report
- "critic": Verify claims, check citations, detect potential hallucinations

RULES:
1. Always include "retrieval" as the first task if the query requires paper content.
2. For simple factual questions, retrieval + summarization is enough.
3. For comparative/analytical questions, add "analysis".
4. For claims or bold statements, add "critic".
5. Return a concise, actionable plan.
6. Always respond with valid JSON."""

    def execute(self, context):
        """
        Plan the execution strategy for a research query.

        Context:
            query (str): The user's research question.
            paper_count (int): Number of papers in the knowledge base.
            has_extractions (bool): Whether any papers have been extracted.
            chat_history (list, optional): Prior messages in the chat session.

        Returns:
            Dict with: tasks (list), reasoning (str), complexity (str), rewritten_query (str)
        """
        query = context.get('query', '')
        paper_count = context.get('paper_count', 0)
        has_extractions = context.get('has_extractions', False)
        chat_history = context.get('chat_history', [])

        # Format chat history for context
        history_text = ""
        if chat_history:
            history_text = "CONVERSATION HISTORY:\n"
            for msg in chat_history:
                role = "User" if msg.get('role') == 'user' else "Assistant"
                # Truncate assistant reports if they're too long
                content = msg.get('content', '')
                if role == "Assistant" and len(content) > 500:
                    content = content[:500] + "... [truncated]"
                history_text += f"{role}: {content}\n"
            history_text += "\n"

        prompt = f"""Analyze this research query and create an execution plan.

{history_text}NEW QUERY: "{query}"

CONTEXT:
- Papers in knowledge base: {paper_count}
- Extracted metadata available: {has_extractions}

Your job is to:
1. Decompose the query into tasks.
2. Resolve any relative context, pronouns, or references (like "its accuracy", "the second paper", "what does that mean?") in the NEW QUERY using the CONVERSATION HISTORY. Write a fully self-contained standalone search query under "rewritten_query". If the query is already self-contained or there is no history, "rewritten_query" should be identical to the original NEW QUERY.

Return a JSON plan:
{{
    "tasks": [
        {{
            "agent": "retrieval|analysis|summarization|critic",
            "description": "what this task should do",
            "depends_on": null or index of task it depends on (0-based)
        }}
    ],
    "reasoning": "brief explanation of why this plan was chosen",
    "complexity": "simple|moderate|complex",
    "needs_extraction": true or false,
    "rewritten_query": "fully resolved standalone search query incorporating context from history"
}}"""

        return self.call_llm(prompt, json_mode=True, temperature=0.1, max_tokens=1024)
