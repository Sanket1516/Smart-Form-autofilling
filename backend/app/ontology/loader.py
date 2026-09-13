"""Universal Field Ontology loader and concept synonym resolver."""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_ONTOLOGY_PATH = Path(__file__).parent / "field_ontology.yaml"


class FieldOntology:
    """Loads and queries the versioned Universal Field Ontology."""

    def __init__(self, ontology_path: Path | str | None = None) -> None:
        path = Path(ontology_path) if ontology_path else DEFAULT_ONTOLOGY_PATH
        self.path = path
        self.version: str = "1.0.0"
        self.concepts: dict[str, dict[str, Any]] = {}
        self._synonym_map: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            logger.error("ontology_file_not_found path=%s", self.path)
            raise FileNotFoundError(f"Ontology configuration file not found at {self.path}")

        with open(self.path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.version = data.get("version", "1.0.0")
        self.concepts = data.get("concepts", {})

        self._synonym_map.clear()
        for concept_key, concept_data in self.concepts.items():
            canonical = concept_data.get("canonical_name", concept_key)
            self._synonym_map[canonical.lower()] = canonical

            for synonym in concept_data.get("aliases", []):
                norm_syn = synonym.strip().lower()
                if norm_syn:
                    self._synonym_map[norm_syn] = canonical

        logger.info("ontology_loaded version=%s concepts=%d", self.version, len(self.concepts))

    def get_concept(self, concept_name: str) -> dict[str, Any] | None:
        return self.concepts.get(concept_name)

    def match_synonym(self, text: str) -> str | None:
        if not text:
            return None
        cleaned = text.strip().lower()
        return self._synonym_map.get(cleaned)

    def find_matches(self, text: str) -> list[tuple[str, float]]:
        """Returns candidate (concept, confidence) pairs for text."""
        if not text or not text.strip():
            return []

        cleaned = text.strip().lower()

        # 1. Exact match in synonym table
        exact_concept = self._synonym_map.get(cleaned)
        if exact_concept:
            return [(exact_concept, 0.98)]

        results: list[tuple[str, float]] = []
        # 2. Check substring or token containment
        for syn, concept in self._synonym_map.items():
            if syn in cleaned or cleaned in syn:
                # Calculate simple overlap ratio
                ratio = min(len(syn), len(cleaned)) / max(len(syn), len(cleaned))
                conf = round(0.70 + 0.25 * ratio, 2)
                results.append((concept, conf))

        # Sort by confidence descending, deduplicate concepts
        dedup: dict[str, float] = {}
        for concept, conf in sorted(results, key=lambda x: x[1], reverse=True):
            if concept not in dedup:
                dedup[concept] = conf

        return [(concept, conf) for concept, conf in dedup.items()]
