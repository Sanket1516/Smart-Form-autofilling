"""Format and checksum validation for Indian identifiers.

A validator returns the canonical identifier, or ``None`` when the text is not a
valid identifier of that kind. Aadhaar numbers must pass the Verhoeff checksum;
common OCR confusions (O for 0, I/l for 1) are repaired only when the repaired
number then passes the checksum, and the repair is reported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)
_OCR_DIGITS = str.maketrans({"O": "0", "o": "0", "D": "0", "I": "1", "l": "1", "|": "1"})


def verhoeff_valid(digits: str) -> bool:
    if not digits.isdigit():
        return False
    check = 0
    for index, char in enumerate(reversed(digits)):
        check = _VERHOEFF_D[check][_VERHOEFF_P[index % 8][int(char)]]
    return check == 0


@dataclass(frozen=True)
class Validation:
    value: str
    repaired: bool = False


def _compact(raw: str) -> str:
    return re.sub(r"[\s-]+", "", str(raw or "")).upper()


def aadhaar(raw: str) -> Validation | None:
    text = re.sub(r"[\s-]+", "", str(raw or ""))
    candidates = [(text, False)]
    if not text.isdigit():
        candidates.append((text.translate(_OCR_DIGITS), True))
    for value, repaired in candidates:
        if re.fullmatch(r"[2-9]\d{11}", value) and verhoeff_valid(value):
            return Validation(value, repaired)
    return None


def pan(raw: str) -> Validation | None:
    value = _compact(raw)
    return (
        Validation(value) if re.fullmatch(r"[A-Z]{3}[ABCFGHJLPT][A-Z]\d{4}[A-Z]", value) else None
    )


def ifsc(raw: str) -> Validation | None:
    value = _compact(raw)
    if re.fullmatch(r"[A-Z]{4}[0O][A-Z0-9]{6}", value):
        fixed = value[:4] + "0" + value[5:]
        return Validation(fixed, fixed != value)
    return None


def micr(raw: str) -> Validation | None:
    value = _compact(raw)
    return Validation(value) if re.fullmatch(r"\d{9}", value) else None


def epic(raw: str) -> Validation | None:
    value = _compact(raw)
    return Validation(value) if re.fullmatch(r"[A-Z]{3}\d{7}", value) else None


def passport(raw: str) -> Validation | None:
    value = _compact(raw)
    return Validation(value) if re.fullmatch(r"[A-Z]\d{7}", value) else None


def driving_licence(raw: str) -> Validation | None:
    value = _compact(raw).replace("/", "")
    return Validation(value) if re.fullmatch(r"[A-Z]{2}\d{2}(?:19|20)\d{2}\d{7}", value) else None


def pincode(raw: str) -> Validation | None:
    value = re.sub(r"\s+", "", str(raw or ""))
    return Validation(value) if re.fullmatch(r"[1-9]\d{5}", value) else None


VALIDATORS = {
    "aadhaar": aadhaar,
    "pan": pan,
    "ifsc": ifsc,
    "micr": micr,
    "epic": epic,
    "passport": passport,
    "driving_licence": driving_licence,
    "pincode": pincode,
}

# Patterns that locate candidate identifiers inside a line of text.
PATTERNS = {
    "aadhaar": re.compile(r"(?<![\w])[2-9OoIl][\dOoIl]{3}[ -]?[\dOoIl]{4}[ -]?[\dOoIl]{4}(?![\w])"),
    "pan": re.compile(r"\b[A-Z]{3}[ABCFGHJLPT][A-Z]\d{4}[A-Z]\b"),
    "ifsc": re.compile(r"\b[A-Z]{4}[0O][A-Z0-9]{6}\b"),
    "micr": re.compile(r"(?<!\d)\d{9}(?!\d)"),
    "epic": re.compile(r"\b[A-Z]{3}\d{7}\b"),
    "passport": re.compile(r"\b[A-Z]\d{7}\b"),
    "driving_licence": re.compile(r"\b[A-Z]{2}[ -]?\d{2}[ -]?(?:19|20)\d{2}[ -]?\d{7}\b"),
    "pincode": re.compile(r"(?<!\d)[1-9]\d{2}\s?\d{3}(?!\d)"),
}


def validate(kind: str | None, raw: str) -> Validation | None:
    validator = VALIDATORS.get(kind or "")
    return validator(raw) if validator else None


def find(kind: str, text: str) -> list[tuple[str, Validation]]:
    """(raw match, validation) for every valid identifier of ``kind`` in ``text``."""
    found = []
    for match in PATTERNS[kind].finditer(text):
        result = validate(kind, match.group(0))
        if result is not None:
            found.append((match.group(0), result))
    return found


def mask(value: str, visible: int = 4) -> str:
    """Show only the last ``visible`` characters: for display and logs."""
    text = str(value or "")
    if len(text) <= visible:
        return "*" * len(text)
    return "*" * (len(text) - visible) + text[-visible:]


_IDENTIFIER_IN_TEXT = re.compile(
    r"\b[A-Z]{3}[ABCFGHJLPT][A-Z]\d{4}[A-Z]\b|\b[A-Z]{3}\d{7}\b|(?<![\w])\d[\d -]{6,}\d(?![\w])"
)


def mask_identifiers(text: str) -> str:
    """Mask PAN/EPIC-shaped tokens and digit runs of 8+ digits inside free text."""
    return _IDENTIFIER_IN_TEXT.sub(lambda m: mask(re.sub(r"[\s-]", "", m.group(0))), text or "")
