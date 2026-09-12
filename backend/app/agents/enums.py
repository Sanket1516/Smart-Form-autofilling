"""Shared agent status enums per SRS §17.2."""

from enum import Enum


class FinalResponseStatus(str, Enum):
    """All possible final-response states for the autofill agent workflow.

    Values are kept as strings so they serialize cleanly to/from JSON and
    MongoDB without custom adapters.
    """

    # Evidence found, confidence above threshold — safe to autofill.
    READY_TO_FILL = "READY_TO_FILL"

    # Evidence found but human confirmation is recommended.
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"

    # More than one plausible candidate exists; the user must choose.
    MULTIPLE_CANDIDATES = "MULTIPLE_CANDIDATES"

    # No usable evidence was found in structured facts or documents.
    MISSING_INFORMATION = "MISSING_INFORMATION"

    # The field type or concept is not supported by the ontology.
    UNSUPPORTED_FIELD = "UNSUPPORTED_FIELD"

    # Evidence exists but overall confidence is below the minimum threshold.
    LOW_CONFIDENCE = "LOW_CONFIDENCE"

    # The field context triggered a prompt-injection or security heuristic.
    SECURITY_BLOCKED = "SECURITY_BLOCKED"

    # An internal agent error occurred.
    ERROR = "ERROR"
