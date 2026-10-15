"""Adapt a known value to a specific form control, or explain why it does not fit."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.extraction.normalize import (
    format_date,
    normalize_date,
    normalize_email,
    normalize_phone,
    normalize_postal_code,
)
from app.schemas.form_sessions import FieldObject

_DATE_PATTERN = re.compile(r"\b(DD|MM|YYYY|YY)([/.\- ])(DD|MM|YYYY|YY)\2(DD|MM|YYYY|YY)\b", re.I)
_SYNONYMS = {
    "m": "male",
    "man": "male",
    "f": "female",
    "woman": "female",
    "y": "yes",
    "true": "yes",
    "1": "yes",
    "n": "no",
    "false": "no",
    "0": "no",
    "pass": "passed",
    "qualified": "passed",
    "appeared": "appearing",
    "transgender": "transgender",
    "third gender": "transgender",
}
_RANGE_NUMBER = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(lakhs?|lacs?|l\b|crores?)?", re.I)
_UNITS = {"lakh": 100000, "lac": 100000, "l": 100000, "crore": 10000000}
_TRUTHY = {"yes", "true", "1", "on", "checked"}


@dataclass
class Formatted:
    value: str | None
    selected_option: dict[str, str] | None = None
    problem: str | None = None


def _norm(text: Any) -> str:
    cleaned = " ".join(re.sub(r"[^\w]+", " ", str(text or "").casefold()).split())
    return _SYNONYMS.get(cleaned, cleaned)


def date_hint(field_obj: FieldObject) -> str | None:
    for text in (field_obj.placeholder, field_obj.label, field_obj.question, field_obj.pattern):
        match = _DATE_PATTERN.search(text or "")
        if match:
            return match.group(0).upper()
    return None


def format_for_field(field_obj: FieldObject, data_type: str, value: Any) -> Formatted:
    """Convert a stored value into what this control expects."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return Formatted(None, problem="No value")
    if isinstance(value, (list, dict)):
        return Formatted(None, problem="Several values are stored; choose one")
    text = " ".join(str(value).split())

    if field_obj.input_type in ("select", "select-one", "radio") or (
        field_obj.options and field_obj.input_type != "checkbox"
    ):
        if data_type == "amount":
            ranged = _match_amount_range(field_obj, text)
            if ranged is not None:
                return ranged
        return _match_option(field_obj, text)
    if field_obj.input_type == "checkbox":
        if _norm(text) in _TRUTHY:
            return Formatted("true")
        return Formatted(None, problem="Checkboxes are only ticked for explicit yes/no answers")

    if data_type == "date" or field_obj.input_type == "date":
        iso = normalize_date(text)
        if iso is None:
            return Formatted(None, problem=f"'{text}' is not a recognisable date")
        if field_obj.input_type == "date":
            return Formatted(iso)
        return Formatted(format_date(iso, date_hint(field_obj)))
    if data_type == "email" or field_obj.input_type == "email":
        email = normalize_email(text)
        return (
            Formatted(email)
            if email
            else Formatted(None, problem="Stored value is not a valid email")
        )
    if data_type == "phone" or field_obj.input_type == "tel":
        phone = normalize_phone(text)
        return (
            Formatted(phone)
            if phone
            else Formatted(None, problem="Stored value is not a valid phone number")
        )
    if data_type == "postal_code":
        code = normalize_postal_code(text)
        return (
            Formatted(code)
            if code
            else Formatted(None, problem="Stored value is not a valid postal code")
        )
    if field_obj.max_length and len(text) > field_obj.max_length:
        return Formatted(
            None, problem=f"Value is longer than the field allows ({field_obj.max_length})"
        )
    return Formatted(text)


def _option_range(label: str) -> tuple[float, float] | None:
    """(low, high] described by an option such as 'Above 2.5 Lakh and up to 6 Lakh'."""
    found = [(m.group(1), (m.group(2) or "").lower()) for m in _RANGE_NUMBER.finditer(label)]
    if not found:
        return None
    last_unit = next((unit for _n, unit in reversed(found) if unit), "")
    numbers = []
    for raw, unit in found:
        unit = (unit or last_unit).rstrip("s")
        numbers.append(float(raw.replace(",", "")) * _UNITS.get(unit, 1))
    lowered = label.lower()
    if len(numbers) >= 2:
        return numbers[0], numbers[1]
    if re.search(r"\b(up\s*to|upto|below|less than|not exceeding|under)\b", lowered):
        return float("-inf"), numbers[0]
    if re.search(r"\b(above|more than|exceeding|over|and above)\b", lowered):
        return numbers[0], float("inf")
    return None


def _match_amount_range(field_obj: FieldObject, text: str) -> Formatted | None:
    try:
        amount = float(text.replace(",", ""))
    except ValueError:
        return None
    ranged = [(o, _option_range(o.label or o.value)) for o in field_obj.options if not o.disabled]
    ranged = [(o, r) for o, r in ranged if r is not None]
    if not ranged:
        return None
    matching = [
        o
        for o, (low, high) in ranged
        if low < amount <= high or (low == float("-inf") and amount <= high)
    ]
    if len(matching) == 1:
        option = matching[0]
        return Formatted(
            option.value or option.label, {"label": option.label, "value": option.value}
        )
    return Formatted(None, problem=f"No single income range option fits {text}")


def _match_option(field_obj: FieldObject, text: str) -> Formatted:
    options = [o for o in field_obj.options if not o.disabled and (o.label or o.value)]
    target = _norm(text)
    exact = [o for o in options if target and target in (_norm(o.label), _norm(o.value))]
    if len(exact) == 1:
        option = exact[0]
        return Formatted(
            option.value or option.label, {"label": option.label, "value": option.value}
        )
    if len(exact) > 1:
        return Formatted(None, problem="More than one option matches; choose one")
    words = [
        o for o in options if target and re.search(rf"\b{re.escape(target)}\b", _norm(o.label))
    ]
    if len(words) == 1:
        option = words[0]
        return Formatted(
            option.value or option.label, {"label": option.label, "value": option.value}
        )
    return Formatted(None, problem=f"None of the options matches '{text}'")
