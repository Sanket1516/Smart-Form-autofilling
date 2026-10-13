"""Universal Field Ontology loader and phrase matcher.

Matching works on normalised word tokens. An alias matches only when all of
its tokens appear contiguously in the text, so "father name" never matches the
concept for "name" alone, and "branch" never matches "bank name". When a longer
alias covers a shorter one (e.g. "father name" covers "name"), the shorter match
is discarded.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_ONTOLOGY_PATH = Path(__file__).parent / "field_ontology.yaml"

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "your",
        "you",
        "my",
        "please",
        "enter",
        "provide",
        "here",
        "type",
        "select",
        "choose",
        "is",
        "what",
        "and",
        "or",
        "in",
        "for",
        "to",
        "s",
    }
)
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def normalize_tokens(text: str | None) -> tuple[str, ...]:
    """Lower-case word tokens with camelCase/snake_case split and stopwords removed."""
    if not text:
        return ()
    spaced = _CAMEL.sub(" ", str(text))
    spaced = re.sub(r"['’]s\b", "", spaced)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced).lower()
    return tuple(token for token in spaced.split() if token not in _STOPWORDS)


@dataclass(frozen=True)
class ConceptMatch:
    concept: str
    score: float
    alias: str


class FieldOntology:
    """Loads and queries the versioned Universal Field Ontology."""

    def __init__(self, ontology_path: Path | str | None = None) -> None:
        self.path = Path(ontology_path) if ontology_path else DEFAULT_ONTOLOGY_PATH
        self.version = "0"
        self.concepts: dict[str, dict[str, Any]] = {}
        self._aliases: list[tuple[tuple[str, ...], str, str]] = []
        self._autocomplete: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"Ontology configuration file not found at {self.path}")
        with open(self.path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        self.version = str(data.get("version", "0"))
        self.concepts = data.get("concepts", {})
        self._aliases.clear()
        self._autocomplete.clear()
        for key, entry in self.concepts.items():
            for alias in set(entry.get("aliases", [])):
                tokens = normalize_tokens(alias)
                if tokens:
                    self._aliases.append((tokens, key, alias))
            for token in entry.get("autocomplete", []):
                self._autocomplete[token.lower()] = key
        logger.info(
            "ontology_loaded", extra={"version": self.version, "concepts": len(self.concepts)}
        )

    # ------------------------------------------------------------------ queries

    def get_concept(self, concept: str) -> dict[str, Any] | None:
        return self.concepts.get(concept)

    def is_known(self, concept: str | None) -> bool:
        return bool(concept) and concept in self.concepts

    def is_sensitive(self, concept: str) -> bool:
        return bool(self.concepts.get(concept, {}).get("sensitive", False))

    def is_fillable(self, concept: str) -> bool:
        return bool(self.concepts.get(concept, {}).get("fillable", True))

    def is_single_valued(self, concept: str) -> bool:
        return self.concepts.get(concept, {}).get("cardinality", "single") == "single"

    def data_type(self, concept: str) -> str:
        return str(self.concepts.get(concept, {}).get("data_type", "string"))

    def derived_from(self, concept: str) -> str | None:
        return self.concepts.get(concept, {}).get("derived_from")

    def description(self, concept: str) -> str:
        return str(self.concepts.get(concept, {}).get("description", concept))

    def concept_for_autocomplete(self, autocomplete: str | None) -> str | None:
        if not autocomplete:
            return None
        for token in reversed(autocomplete.lower().split()):
            if token in self._autocomplete:
                return self._autocomplete[token]
        return None

    def match_text(self, text: str | None) -> list[ConceptMatch]:
        """Return concept matches for text, best first."""
        tokens = normalize_tokens(text)
        if not tokens:
            return []
        spans: list[tuple[int, int, str, str, int]] = []
        for alias_tokens, concept, alias in self._aliases:
            length = len(alias_tokens)
            for start in range(len(tokens) - length + 1):
                if tokens[start : start + length] == alias_tokens:
                    spans.append((start, start + length, concept, alias, length))
                    break
        kept = [
            span
            for span in spans
            if not any(
                other[0] <= span[0] and span[1] <= other[1] and other[4] > span[4]
                for other in spans
            )
        ]
        best: dict[str, ConceptMatch] = {}
        for _start, _end, concept, alias, length in kept:
            score = 0.98 if length == len(tokens) else round(0.80 + 0.15 * length / len(tokens), 3)
            if concept not in best or score > best[concept].score:
                best[concept] = ConceptMatch(concept, score, alias)
        return sorted(best.values(), key=lambda match: match.score, reverse=True)

    def find_matches(self, text: str | None) -> list[tuple[str, float]]:
        """Backward-compatible (concept, score) pairs."""
        return [(match.concept, match.score) for match in self.match_text(text)]

    def catalog(self) -> list[tuple[str, str]]:
        """(concept, description) pairs for fillable concepts, for LLM prompts."""
        return [
            (key, str(entry.get("description", key)))
            for key, entry in self.concepts.items()
            if entry.get("fillable", True)
        ]
