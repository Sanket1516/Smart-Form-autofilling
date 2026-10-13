"""Pluggable LLM providers.

Providers expose a single synchronous ``complete`` call plus an async wrapper.
Failures raise :class:`LLMProviderError`; a provider never returns a sentinel
string and never silently switches to another provider or model. The mock
provider is deterministic, makes no network calls and never invents personal
data: unless a test injects a responder, it answers every task with an empty,
schema-valid result.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

# Task names let the mock provider return a correctly shaped empty answer and
# make logs readable. They are not sent to real providers.
TASK_FIELD_CLASSIFICATION = "field_classification"
TASK_DOCUMENT_EXTRACTION = "document_extraction"
TASK_FIELD_VALUES = "field_value_extraction"
TASK_RAG_ANSWER = "rag_answer"

# Interactive form analysis should return promptly when a provider is slow or
# unreachable. Document extraction and ad-hoc RAG answers keep the configured
# retry policy because they are not on the extension's review path.
_INTERACTIVE_TASKS = {TASK_FIELD_CLASSIFICATION, TASK_FIELD_VALUES}
_INTERACTIVE_TIMEOUT_SECONDS = 20

_MOCK_EMPTY_RESPONSES: dict[str, dict[str, object]] = {
    TASK_FIELD_CLASSIFICATION: {"classifications": []},
    TASK_DOCUMENT_EXTRACTION: {"document_type": "UNKNOWN", "attributes": []},
    TASK_FIELD_VALUES: {"answers": []},
    TASK_RAG_ANSWER: {"answer": "", "used_chunk_ids": [], "confidence": 0.0},
}


class LLMProviderError(RuntimeError):
    """Raised when the configured LLM provider cannot produce a completion."""


class LLMProvider(ABC):
    """Abstract LLM backend."""

    name: str = "abstract"
    model: str = ""
    is_mock: bool = False

    def __init__(self) -> None:
        self.call_count = 0

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_mode: bool = True,
        task: str = "generic",
    ) -> str:
        """Return the completion text for *prompt* or raise ``LLMProviderError``."""
        self.call_count += 1
        started = time.monotonic()
        try:
            return self._complete(prompt, system=system, json_mode=json_mode, task=task)
        finally:
            logger.info(
                "llm_call",
                extra={
                    "provider": self.name,
                    "model": self.model,
                    "task": task,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                },
            )

    async def acomplete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_mode: bool = True,
        task: str = "generic",
    ) -> str:
        return await asyncio.to_thread(
            self.complete, prompt, system=system, json_mode=json_mode, task=task
        )

    @abstractmethod
    def _complete(self, prompt: str, *, system: str | None, json_mode: bool, task: str) -> str: ...


class MockLLMProvider(LLMProvider):
    """Deterministic offline provider for tests and local development.

    ``responder`` (optional) receives ``(task, prompt)`` and returns the raw
    completion text, which lets tests simulate valid, invalid or failing model
    output. Without a responder every task gets an empty, schema-valid answer.
    """

    name = "mock"
    model = "mock"
    is_mock = True

    def __init__(self, responder: Callable[[str, str], str] | None = None) -> None:
        super().__init__()
        self._responder = responder

    def _complete(self, prompt: str, *, system: str | None, json_mode: bool, task: str) -> str:
        if self._responder is not None:
            return self._responder(task, prompt)
        return json.dumps(_MOCK_EMPTY_RESPONSES.get(task, {}))


class _HTTPProvider(LLMProvider):
    """Shared retry logic for HTTP-based providers."""

    def __init__(self, model: str, api_key: str, timeout: int, max_tokens: int, retries: int):
        super().__init__()
        if not model:
            raise ValueError(f"LLM_MODEL is required when LLM_PROVIDER={self.name}")
        self.model = model
        self._api_key = api_key
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._retries = retries

    def _post(
        self, url: str, headers: dict[str, str], payload: dict[str, object], *, task: str
    ) -> dict:
        last_error: Exception | None = None
        interactive = task in _INTERACTIVE_TASKS
        timeout = min(self._timeout, _INTERACTIVE_TIMEOUT_SECONDS) if interactive else self._timeout
        retries = 0 if interactive else self._retries
        for attempt in range(retries + 1):
            try:
                response = httpx.post(url, headers=headers, json=payload, timeout=timeout)
            except httpx.TimeoutException as error:
                last_error = error
            except httpx.HTTPError as error:
                raise LLMProviderError(
                    f"{self.name} request failed: {type(error).__name__}"
                ) from error
            else:
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = LLMProviderError(
                        f"{self.name} returned HTTP {response.status_code}"
                    )
                elif response.status_code >= 400:
                    raise LLMProviderError(
                        f"{self.name} rejected the request (HTTP {response.status_code}); "
                        "check LLM_MODEL and LLM_API_KEY"
                    )
                else:
                    try:
                        return response.json()
                    except ValueError as error:
                        raise LLMProviderError(f"{self.name} returned a non-JSON body") from error
            if attempt < retries:
                time.sleep(min(2**attempt, 8))
        raise LLMProviderError(
            f"{self.name} unavailable after {retries + 1} attempts"
        ) from last_error


class GoogleProvider(_HTTPProvider):
    """Google Gemini through the Generative Language REST API."""

    name = "google"
    _BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def _complete(self, prompt: str, *, system: str | None, json_mode: bool, task: str) -> str:
        generation: dict[str, object] = {"temperature": 0, "maxOutputTokens": self._max_tokens}
        if json_mode:
            generation["responseMimeType"] = "application/json"
        payload: dict[str, object] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": generation,
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        data = self._post(
            f"{self._BASE}/{self.model}:generateContent",
            {"Content-Type": "application/json", "x-goog-api-key": self._api_key},
            payload,
            task=task,
        )
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as error:
            reason = (data.get("candidates") or [{}])[0].get("finishReason", "unknown")
            raise LLMProviderError(f"google returned no text (finishReason={reason})") from error
        if not text.strip():
            raise LLMProviderError("google returned an empty completion")
        return text.strip()


class OpenAIProvider(_HTTPProvider):
    """OpenAI Chat Completions API."""

    name = "openai"
    _URL = "https://api.openai.com/v1/chat/completions"

    def _complete(self, prompt: str, *, system: str | None, json_mode: bool, task: str) -> str:
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": self._max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = self._post(
            self._URL,
            {"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"},
            payload,
            task=task,
        )
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as error:
            raise LLMProviderError("openai returned an unexpected response shape") from error
        if not text.strip():
            raise LLMProviderError("openai returned an empty completion")
        return text.strip()


class AnthropicProvider(_HTTPProvider):
    """Anthropic Messages API."""

    name = "anthropic"
    _URL = "https://api.anthropic.com/v1/messages"

    def _complete(self, prompt: str, *, system: str | None, json_mode: bool, task: str) -> str:
        payload: dict[str, object] = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        data = self._post(
            self._URL,
            {
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
            payload,
            task=task,
        )
        try:
            text = "".join(
                block.get("text", "") for block in data["content"] if block.get("type") == "text"
            )
        except (KeyError, TypeError) as error:
            raise LLMProviderError("anthropic returned an unexpected response shape") from error
        if not text.strip():
            raise LLMProviderError("anthropic returned an empty completion")
        return text.strip()


def get_llm_provider(settings: Settings) -> LLMProvider:
    """Build the provider selected by ``LLM_PROVIDER`` (validated in Settings)."""
    provider = settings.llm_provider
    if provider == "mock":
        logger.warning("llm_provider_mock: AI extraction and classification return empty results")
        return MockLLMProvider()
    providers: dict[str, type[_HTTPProvider]] = {
        "google": GoogleProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }
    instance = providers[provider](
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout_seconds,
        max_tokens=settings.llm_max_output_tokens,
        retries=settings.llm_max_retries,
    )
    logger.info(
        "llm_provider_configured", extra={"provider": provider, "model": settings.llm_model}
    )
    return instance
