"""Helpers for treating webpage and document content as untrusted LLM input.

Every piece of text that originates from a web page or an uploaded document is
wrapped in a tagged block before it reaches an LLM. The tag delimiters are
escaped inside the content so the text cannot close the block and smuggle in
instructions. A small set of heuristics flags obvious injection attempts so the
caller can drop or quarantine the content.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier|system)\s+(instructions?|prompts?|rules?)",
        re.I,
    ),
    re.compile(
        r"\b(reveal|print|show|dump|output)\s+(all\s+|the\s+|any\s+)?"
        r"((stored|user'?s?|private|personal|system|saved|other)\s+){1,2}(data|facts|information|prompt|details|profile)",
        re.I,
    ),
    re.compile(r"\byou\s+are\s+now\s+(a|an|the)\b", re.I),
    re.compile(r"\bnew\s+(system\s+)?instructions?\s*:", re.I),
    re.compile(r"\b(system|developer)\s+prompt\b", re.I),
    re.compile(r"</?\s*(system|instruction|instructions|prompt|untrusted_[a-z_]+)\s*>", re.I),
)

_TAG_CHARS = str.maketrans({"<": "‹", ">": "›"})


def detect_injection(text: str | None) -> bool:
    """Return True when text contains a known prompt-injection pattern."""
    if not text:
        return False
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning("prompt_injection_detected", extra={"pattern": pattern.pattern[:60]})
            return True
    return False


def sanitize_untrusted(text: object, max_chars: int) -> str:
    """Collapse whitespace, cap length and neutralise angle brackets."""
    cleaned = " ".join(str(text or "").split())
    return cleaned[:max_chars].translate(_TAG_CHARS)


def wrap_untrusted(tag: str, content: str) -> str:
    """Wrap pre-sanitised content in an untrusted-data block."""
    safe_tag = re.sub(r"[^A-Z_]", "", tag.upper()) or "UNTRUSTED_DATA"
    return f"<{safe_tag}>\n{content.translate(_TAG_CHARS)}\n</{safe_tag}>"
