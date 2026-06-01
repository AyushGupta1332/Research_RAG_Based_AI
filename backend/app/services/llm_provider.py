"""
Research Agent — LLM Provider Abstraction Layer

Provides a unified interface for LLM inference.
Currently implements Groq provider with Llama 3.3 70B.
Designed to be swappable — add OpenAI, Ollama, etc. later.

Design:
    - Abstract base class with generate() method.
    - Groq provider with JSON mode, retry logic, and token tracking.
    - Factory function to get the configured provider.
"""

import os
import json
import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt, system_prompt=None, temperature=0.1,
                 max_tokens=4096, json_mode=False):
        """
        Generate a completion from the LLM.

        Args:
            prompt: User prompt text.
            system_prompt: Optional system/instruction prompt.
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum tokens in the response.
            json_mode: If True, request JSON-formatted output.

        Returns:
            Dict with keys:
                content (str): The generated text.
                usage (dict): Token usage stats.
                model (str): Model used.
                latency_ms (float): Request latency in ms.
        """
        pass

    @abstractmethod
    def is_available(self):
        """Check if the provider is configured and available."""
        pass

    @abstractmethod
    def get_info(self):
        """Return provider info dict."""
        pass


class GroqProvider(LLMProvider):
    """
    Groq API provider using Llama 3.3 70B Versatile.

    Requires GROQ_API_KEY environment variable.
    """

    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    def __init__(self, model=None, api_key=None):
        self.model = model or self.DEFAULT_MODEL
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        self._client = None
        self._total_tokens_used = 0

    def _get_client(self):
        """Lazy-initialize the Groq client."""
        if self._client is None:
            if not self.api_key:
                raise RuntimeError(
                    "GROQ_API_KEY is not set. "
                    "Add it to backend/.env: GROQ_API_KEY=your_key_here"
                )
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
                logger.info(f"Groq client initialized (model={self.model})")
            except ImportError:
                raise RuntimeError(
                    "Groq SDK not installed. Install with: pip install groq"
                )
        return self._client

    def generate(self, prompt, system_prompt=None, temperature=0.1,
                 max_tokens=4096, json_mode=False):
        """Generate a completion using Groq API."""
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        # Retry loop
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = time.time()
                response = client.chat.completions.create(**kwargs)
                latency_ms = (time.time() - start_time) * 1000

                content = response.choices[0].message.content
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                self._total_tokens_used += usage["total_tokens"]

                logger.info(
                    f"Groq response: model={self.model}, "
                    f"tokens={usage['total_tokens']}, "
                    f"latency={latency_ms:.0f}ms"
                )

                return {
                    "content": content,
                    "usage": usage,
                    "model": self.model,
                    "latency_ms": round(latency_ms, 1),
                }

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Groq API error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))

        raise RuntimeError(f"Groq API failed after {self.MAX_RETRIES} attempts: {last_error}")

    def is_available(self):
        """Check if Groq API key is set."""
        return bool(self.api_key)

    def get_info(self):
        """Return provider information."""
        return {
            "provider": "groq",
            "model": self.model,
            "available": self.is_available(),
            "total_tokens_used": self._total_tokens_used,
        }


# ─── Provider Factory ─────────────────────────────────────────────

_provider_instance = None


def get_llm_provider():
    """
    Get the configured LLM provider (singleton).
    Currently returns GroqProvider, but can be extended
    to support multiple providers via config.
    """
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = GroqProvider()
    return _provider_instance


def generate_json(prompt, system_prompt=None, temperature=0.1, max_tokens=4096):
    """
    Convenience function: generate and parse JSON from LLM.

    Returns:
        Tuple of (parsed_dict, raw_response_dict)

    Raises:
        ValueError if JSON parsing fails.
    """
    provider = get_llm_provider()
    response = provider.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=True,
    )

    try:
        parsed = json.loads(response["content"])
        return parsed, response
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        logger.debug(f"Raw content: {response['content'][:500]}")
        raise ValueError(f"LLM returned invalid JSON: {e}")
