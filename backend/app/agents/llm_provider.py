"""Pluggable LLM Provider interface for the reasoning node (SRS §35.5).

All personal data must be scoped to the current field only. The LLM never
receives the user's full profile — only the isolated evidence relevant to the
current field (SRS §27.7, data minimization).
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings

from app.agents.enums import FinalResponseStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security heuristics (SRS §27.6 — untrusted webpage data must never become
# an instruction to the LLM).
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions?|prompts?)", re.IGNORECASE),
    re.compile(r"reveal\s+(all\s+)?(stored|user|private|personal)\s+(data|facts|information)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+(instructions?|prompts?)", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(previous|prior)\s+(instructions?|prompts?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a)\s+", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"</?(system|instruction|prompt)>", re.IGNORECASE),
]


def detect_injection(text: str) -> bool:
    """Return True if text contains a known prompt-injection pattern."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning("prompt_injection_detected pattern=%s text=%r", pattern.pattern, text[:120])
            return True
    return False


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class LLMProvider(ABC):
    """Abstract pluggable LLM backend for the reasoning node."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Return LLM completion for *prompt*.

        Implementations must not fabricate personal values (SRS §17.3).
        """


# ---------------------------------------------------------------------------
# Mock provider — deterministic, no network calls, suitable for CI.
# ---------------------------------------------------------------------------


class MockLLMProvider(LLMProvider):
    """Deterministic mock for tests and environments without an API key.

    Behaviour:
    - If *forced_answer* is set, return it verbatim (for happy-path tests).
    - Otherwise return ``MISSING_INFORMATION`` to honour the no-fabrication rule.
    """

    def __init__(self, forced_answer: str | None = None) -> None:
        self._forced = forced_answer

    def complete(self, prompt: str) -> str:
        if self._forced is not None:
            return self._forced
        return FinalResponseStatus.MISSING_INFORMATION.value


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------


class OpenAIProvider(LLMProvider):
    """LLM provider backed by the OpenAI Chat Completions API."""

    def __init__(self, model: str, api_key: str, timeout: int = 30) -> None:
        try:
            import openai  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "openai package is required for OpenAIProvider. "
                "Add 'openai' to requirements.txt."
            ) from exc
        self._client = openai.OpenAI(api_key=api_key, timeout=timeout)
        self._model = model

    def complete(self, prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=256,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.exception("openai_completion_failed model=%s", self._model)
            return FinalResponseStatus.ERROR.value


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------


class AnthropicProvider(LLMProvider):
    """LLM provider backed by the Anthropic Messages API."""

    def __init__(self, model: str, api_key: str, timeout: int = 30) -> None:
        try:
            import anthropic  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "anthropic package is required for AnthropicProvider. "
                "Add 'anthropic' to requirements.txt."
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        self._model = model

    def complete(self, prompt: str) -> str:
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            return (message.content[0].text if message.content else "").strip()
        except Exception as exc:
            logger.exception("anthropic_completion_failed model=%s", self._model)
            return FinalResponseStatus.ERROR.value


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_llm_provider(settings: "Settings") -> LLMProvider:
    """Return an ``LLMProvider`` driven by ``LLM_PROVIDER`` env var.

    Supported values: ``openai``, ``anthropic``, ``mock``, ``""`` (treated as mock).
    """
    provider = (settings.llm_provider or "mock").lower().strip()
    model = settings.llm_model or ""
    api_key = settings.llm_api_key or ""
    timeout = settings.llm_reasoning_timeout_seconds

    if provider == "openai":
        if not api_key:
            raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=openai")
        logger.info("llm_provider=openai model=%s", model)
        return OpenAIProvider(model=model or "gpt-4o-mini", api_key=api_key, timeout=timeout)

    if provider == "anthropic":
        if not api_key:
            raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=anthropic")
        logger.info("llm_provider=anthropic model=%s", model)
        return AnthropicProvider(model=model or "claude-3-haiku-20240307", api_key=api_key, timeout=timeout)

    logger.info("llm_provider=mock (no API key required)")
    return MockLLMProvider()
