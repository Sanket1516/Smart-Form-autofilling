"""Strict parsing of JSON returned by an LLM."""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)


class LLMOutputError(ValueError):
    """Raised when model output is not valid JSON or does not match the schema."""


def parse_json_object(raw: str) -> dict:
    """Parse a JSON object, tolerating a surrounding Markdown code fence only."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise LLMOutputError("model output is not valid JSON") from error
    if not isinstance(data, dict):
        raise LLMOutputError("model output must be a JSON object")
    return data


def parse_model(raw: str, model: type[ModelT]) -> ModelT:
    """Parse and validate model output against a Pydantic schema."""
    data = parse_json_object(raw)
    try:
        return model.model_validate(data)
    except ValidationError as error:
        raise LLMOutputError(
            f"model output failed schema validation ({error.error_count()} errors)"
        ) from error
