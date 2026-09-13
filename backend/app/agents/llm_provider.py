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
        
        # If this is a semantic classifier prompt, return a valid JSON matching the schema
        if "Universal Form Field Ontology Mapping Agent" in prompt:
            import json
            label = ""
            # Extract label roughly to return the right mock value
            if '"label": "Name"' in prompt or '"label": "Full Name"' in prompt or '"label": "Applicant Name"' in prompt or '"label": "Name of Candidate"' in prompt:
                return json.dumps({"ontology": "personal.full_name", "field_type": "STRUCTURED", "confidence": 0.95})
            elif '"label": "Date of Birth"' in prompt or '"label": "DOB"' in prompt:
                return json.dumps({"ontology": "personal.date_of_birth", "field_type": "STRUCTURED", "confidence": 0.95})
            elif '"label": "Contact Email"' in prompt or '"label": "Email Address"' in prompt or "Electronic Mail" in prompt:
                return json.dumps({"ontology": "personal.email", "field_type": "STRUCTURED", "confidence": 0.95})
            elif '"label": "Telephone Number"' in prompt or '"label": "Mobile"' in prompt:
                return json.dumps({"ontology": "personal.phone", "field_type": "STRUCTURED", "confidence": 0.95})
            elif '"label": "University"' in prompt:
                return json.dumps({"ontology": "education.institution", "field_type": "STRUCTURED", "confidence": 0.95})
            elif '"label": "Company"' in prompt:
                return json.dumps({"ontology": "experience.company", "field_type": "STRUCTURED", "confidence": 0.95})
            elif '"label": "Field 1"' in prompt:
                return json.dumps({"ontology": "MISSING", "field_type": "MISSING", "confidence": 0.2})
            
            return json.dumps({"ontology": "unknown", "field_type": "MISSING", "confidence": 0.1})

        if "Document Ontology Extraction Agent" in prompt:
            import json
            return json.dumps({
                "document_status": "PROCESSED",
                "facts": [],
                "conflicts": [],
                "unmapped_items": []
            })

        return FinalResponseStatus.MISSING_INFORMATION.value


class MockE2EProvider(LLMProvider):
    """Deterministic mock for E2E tests that successfully generates a recommendation
    if it sees EVIDENCE in the prompt, simulating a real LLM extraction."""
    
    def complete(self, prompt: str) -> str:
        # Check if prompt contains facts or evidence
        import json
        
        has_evidence = "DOCUMENT_EVIDENCE (similarity-ranked):" in prompt or "STRUCTURED_FACTS (verified first):" in prompt
        is_missing = "none" in prompt.split("DOCUMENT_EVIDENCE:")[0] if "DOCUMENT_EVIDENCE:" in prompt else False # Very rough heuristic
        
        # If it seems we passed in structured facts or document chunks, simulate finding it
        if "DOCUMENT_EVIDENCE" in prompt and "similarity=" in prompt:
            return json.dumps({
                "status": FinalResponseStatus.CONFIDENT_RECOMMENDATION.value,
                "value": "E2E Test Value",
                "confidence": 0.95,
                "reason": "Found in document evidence."
            })
        
        if "STRUCTURED_FACTS" in prompt and "value=" in prompt:
            return json.dumps({
                "status": FinalResponseStatus.CONFIDENT_RECOMMENDATION.value,
                "value": "E2E Test Structured Value",
                "confidence": 0.99,
                "reason": "Found in structured facts."
            })
            
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
# Google (Gemini) provider
# ---------------------------------------------------------------------------


class GoogleProvider(LLMProvider):
    """LLM provider backed by Google Gemini REST API with automatic model fallback for 429 rate limits."""

    def __init__(self, model: str, api_key: str, timeout: int = 90) -> None:
        self._primary_model = model or "gemini-3.5-flash-lite"
        self._fallback_models = ["gemini-3.5-flash-lite", "gemini-3.6-flash"]
        self._api_key = api_key
        self._timeout = timeout

    def complete(self, prompt: str) -> str:
        import json
        import urllib.request
        import urllib.error

        models_to_try = [self._primary_model] + [m for m in self._fallback_models if m != self._primary_model]

        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self._api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    candidates = res_data.get("candidates", [])
                    if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
                        parts = candidates[0]["content"]["parts"]
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip()
                    return FinalResponseStatus.ERROR.value
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    logger.warning("google_completion_429 model=%s trying_fallback", model_name)
                    continue
                logger.exception("google_completion_failed model=%s code=%s", model_name, exc.code)
            except Exception as exc:
                logger.exception("google_completion_failed model=%s", model_name)

        return FinalResponseStatus.ERROR.value



# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_llm_provider(settings: "Settings") -> LLMProvider:
    """Return an ``LLMProvider`` driven by ``LLM_PROVIDER`` env var.

    Supported values: ``google``, ``gemini``, ``openai``, ``anthropic``, ``mock``, ``""`` (treated as mock).
    """
    provider = (settings.llm_provider or "mock").lower().strip()
    model = settings.llm_model or ""
    api_key = settings.llm_api_key or ""
    timeout = settings.llm_reasoning_timeout_seconds

    if provider in ("google", "gemini"):
        if not api_key:
            raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=google")
        logger.info("llm_provider=google model=%s", model)
        return GoogleProvider(model=model or "gemini-3.6-flash", api_key=api_key, timeout=max(timeout, 120))

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

    if provider == "mock-e2e":
        logger.info("llm_provider=mock-e2e (Simulating successful extraction for tests)")
        return MockE2EProvider()

    logger.info("llm_provider=mock (no API key required)")
    return MockLLMProvider()

