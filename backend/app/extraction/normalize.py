"""Value normalization and comparison shared by extraction and form filling.

Normalizers return ``None`` when a value cannot be interpreted safely; callers
must then keep the raw value or drop it, never guess.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}$")

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%d %b %Y",
    "%d %B %Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%d %b, %Y",
    "%d %B, %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%b %d %Y",
    "%B %d %Y",
)


def normalize_date(raw: Any) -> str | None:
    """Return an ISO date. Numeric dates are read day-first (DD/MM/YYYY)."""
    if isinstance(raw, (date, datetime)):
        return raw.strftime("%Y-%m-%d")
    text = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", str(raw or "").strip(), flags=re.I)
    text = " ".join(text.replace(",", ", ").split()).replace(" ,", ",")
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        if 1900 <= parsed.year <= 2100:
            return parsed.isoformat()
    return None


def format_date(iso_value: str, pattern: str | None) -> str:
    """Render an ISO date for a form. ``pattern`` is e.g. 'DD/MM/YYYY'; None keeps ISO."""
    try:
        parsed = datetime.strptime(iso_value, "%Y-%m-%d")
    except ValueError:
        return iso_value
    if not pattern:
        return iso_value
    mapping = (("YYYY", "%Y"), ("YY", "%y"), ("MM", "%m"), ("DD", "%d"))
    fmt = pattern.upper()
    for token, directive in mapping:
        fmt = fmt.replace(token, directive)
    if "%" not in fmt:
        return iso_value
    return parsed.strftime(fmt)


def normalize_phone(raw: Any) -> str | None:
    text = str(raw or "").strip()
    digits = re.sub(r"\D", "", text)
    if not 7 <= len(digits) <= 15:
        return None
    return f"+{digits}" if text.startswith("+") else digits


def normalize_email(raw: Any) -> str | None:
    text = str(raw or "").strip().strip(".,;").lower()
    return text if EMAIL_RE.match(text) else None


def normalize_postal_code(raw: Any) -> str | None:
    text = str(raw or "").strip().upper()
    compact = re.sub(r"\s+", "", text) if re.fullmatch(r"[\d\s]+", text) else text
    if re.fullmatch(r"[A-Z0-9][A-Z0-9 -]{1,9}", compact):
        return compact
    return None


def normalize_name(raw: Any) -> str:
    text = " ".join(str(raw or "").split())
    if text.isupper() and len(text) > 3:
        return text.title()
    return text


def normalize_value(data_type: str, raw: Any) -> tuple[Any, bool]:
    """Return (value, changed). Unparseable typed values are returned unchanged."""
    if raw is None:
        return None, False
    if isinstance(raw, (list, dict)):
        return raw, False
    text = " ".join(str(raw).split())
    normalizers = {
        "date": normalize_date,
        "phone": normalize_phone,
        "email": normalize_email,
        "postal_code": normalize_postal_code,
    }
    normalizer = normalizers.get(data_type)
    if normalizer is None:
        return text, text != str(raw)
    value = normalizer(text)
    if value is None:
        return text, text != str(raw)
    return value, value != str(raw)


def comparison_key(data_type: str, value: Any) -> str:
    """A key under which two values are considered the same fact."""
    if value is None:
        return ""
    if data_type == "phone":
        digits = re.sub(r"\D", "", str(value))
        return digits[-10:]
    if data_type == "date":
        return normalize_date(value) or str(value).strip().lower()
    if isinstance(value, (list, dict)):
        return str(value).lower()
    text = re.sub(r"[^\w@.+]+", " ", str(value).casefold())
    return " ".join(text.split())


def appears_in(value: Any, text: str) -> bool:
    """True when a value is literally present in text (case/whitespace-insensitive)."""
    needle = " ".join(str(value or "").split()).casefold()
    haystack = " ".join((text or "").split()).casefold()
    if not needle:
        return False
    if needle in haystack:
        return True
    digits = re.sub(r"\D", "", needle)
    return (
        len(digits) >= 6
        and digits == needle.replace(" ", "").replace("-", "").lstrip("+")
        and (digits in re.sub(r"\D", "", haystack))
    )
