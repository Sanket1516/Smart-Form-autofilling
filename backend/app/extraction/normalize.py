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


def normalize_identifier(raw: Any) -> str | None:
    """Upper-case, whitespace removed; digits-only ids also lose hyphens. Leading zeros stay."""
    text = re.sub(r"\s+", "", str(raw or "")).strip(".,;:").upper()
    if not text or not re.search(r"[A-Z0-9]", text):
        return None
    if re.fullmatch(r"[\d-]+", text):
        text = text.replace("-", "")
    return text


_AMOUNT_MULTIPLIERS = {
    "lakh": 100000,
    "lakhs": 100000,
    "lac": 100000,
    "lacs": 100000,
    "crore": 10000000,
    "crores": 10000000,
}


def normalize_amount(raw: Any) -> str | None:
    """Indian currency text to a plain number string: 'Rs. 4,50,000/-' -> '450000'.

    Decimal places are kept as printed ('5,000.00' -> '5000.00')."""
    text = str(raw or "").strip().lower()
    text = re.sub(r"(rs\.?|inr|₹|/-|only)", " ", text)
    match = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(lakhs?|lacs?|crores?)?", text)
    if not match:
        return None
    number = match.group(1).replace(",", "")
    if match.group(2):
        value = float(number) * _AMOUNT_MULTIPLIERS[match.group(2)]
        return str(int(value)) if value == int(value) else f"{value:.2f}"
    return number


def amount_value(raw: Any) -> float | None:
    normalized = normalize_amount(raw)
    try:
        return float(normalized) if normalized is not None else None
    except ValueError:
        return None


def normalize_number(raw: Any) -> str | None:
    """Marks and counts: '082' -> '82'. Non-numeric values (AB, grades) are rejected."""
    text = str(raw or "").strip().replace(",", "")
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        return None
    if "." in text:
        whole, fraction = text.split(".", 1)
        return f"{int(whole)}.{fraction}"
    return str(int(text))


def normalize_percentage(raw: Any) -> str | None:
    match = re.fullmatch(r"\s*(\d{1,3}(?:\.\d+)?)\s*%?\s*", str(raw or ""))
    if not match or float(match.group(1)) > 100:
        return None
    return match.group(1)


def normalize_year(raw: Any) -> str | None:
    match = re.search(r"(?<!\d)(19[5-9]\d|20\d{2})(?!\d)", str(raw or ""))
    return match.group(1) if match else None


_GENDERS = {
    "m": "Male",
    "male": "Male",
    "पुरुष": "Male",
    "f": "Female",
    "female": "Female",
    "स्त्री": "Female",
    "महिला": "Female",
    "t": "Transgender",
    "tg": "Transgender",
    "transgender": "Transgender",
    "third gender": "Transgender",
}


def normalize_gender(raw: Any) -> str | None:
    text = " ".join(str(raw or "").casefold().split())
    if text in _GENDERS:
        return _GENDERS[text]
    for part in re.split(r"\s*/\s*", text):
        if part in _GENDERS:
            return _GENDERS[part]
    return None


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
        "identifier": normalize_identifier,
        "amount": normalize_amount,
        "number": normalize_number,
        "percentage": normalize_percentage,
        "year": normalize_year,
        "gender": normalize_gender,
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
    if isinstance(value, dict):
        return "|".join(
            f"{key}={comparison_key('string', value[key])}" for key in sorted(value) if value[key]
        )
    if isinstance(value, list):
        return str(value).lower()
    if data_type == "identifier":
        return re.sub(r"[^0-9A-Z]", "", str(value).upper())
    if data_type in ("amount", "number", "percentage"):
        number = amount_value(value) if data_type == "amount" else _float(value)
        if number is not None:
            return f"{number:.4f}"
    if data_type == "gender":
        return (normalize_gender(value) or str(value)).casefold()
    text = re.sub(r"[^\w@.+]+", " ", str(value).casefold())
    return " ".join(text.split())


def _float(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "").rstrip("%").strip())
    except ValueError:
        return None


def address_tokens(value: Any) -> set[str]:
    return set(re.sub(r"[^0-9a-z]+", " ", str(value or "").casefold()).split())


def same_address(a: Any, b: Any) -> bool:
    """Two addresses describe the same place when one's words are all in the other
    and they share the same 6-digit PIN code ("Pune 411001" vs "Pune, Maharashtra 411001")."""
    pins_a = set(re.findall(r"(?<!\d)[1-9]\d{5}(?!\d)", str(a or "")))
    pins_b = set(re.findall(r"(?<!\d)[1-9]\d{5}(?!\d)", str(b or "")))
    if not pins_a or pins_a != pins_b:
        return False
    tokens_a, tokens_b = address_tokens(a), address_tokens(b)
    return tokens_a <= tokens_b or tokens_b <= tokens_a


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
