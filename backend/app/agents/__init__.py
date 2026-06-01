"""
Research Agent — Base Agent Framework

Provides the abstract base class for all specialized agents.
Each agent has a single responsibility, receives structured context,
and returns structured output. No LangChain dependency.

Design:
    - BaseAgent ABC with execute() method
    - Structured input/output via dicts
    - Built-in LLM integration via llm_provider
    - Execution tracing and timing
"""

import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all research agents.

    Every agent must implement:
        - name: Human-readable agent name
        - role: System prompt describing the agent's role
        - execute(context): Takes context dict, returns result dict
    """

    def __init__(self):
        self.logger = logging.getLogger(f"agent.{self.name}")

    @property
    @abstractmethod
    def name(self):
        """Human-readable agent name."""
        pass

    @property
    @abstractmethod
    def role(self):
        """System prompt defining the agent's role and behavior."""
        pass

    @abstractmethod
    def execute(self, context):
        """
        Execute the agent's task.

        Args:
            context: Dict containing all inputs the agent needs.

        Returns:
            Dict with the agent's structured output.
        """
        pass

    def run(self, context):
        """
        Run the agent with timing and error handling.
        This is the public method called by the orchestrator.

        Returns:
            Dict with keys: result, agent, latency_ms, success, error
        """
        self.logger.info(f"Starting execution...")
        start = time.time()

        try:
            result = self.execute(context)
            latency = (time.time() - start) * 1000

            self.logger.info(f"Completed in {latency:.0f}ms")

            return {
                'agent': self.name,
                'result': result,
                'latency_ms': round(latency, 1),
                'success': True,
                'error': None,
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.logger.error(f"Failed after {latency:.0f}ms: {e}", exc_info=True)

            return {
                'agent': self.name,
                'result': None,
                'latency_ms': round(latency, 1),
                'success': False,
                'error': str(e),
            }

    def call_llm(self, prompt, system_prompt=None, temperature=0.2,
                 max_tokens=4096, json_mode=False):
        """
        Convenience method to call the LLM provider.

        Returns:
            The parsed content string (or dict if json_mode=True).
        """
        from ..services.llm_provider import get_llm_provider, generate_json

        if json_mode:
            parsed, response = generate_json(
                prompt=prompt,
                system_prompt=system_prompt or self.role,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return parsed
        else:
            provider = get_llm_provider()
            response = provider.generate(
                prompt=prompt,
                system_prompt=system_prompt or self.role,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response['content']
