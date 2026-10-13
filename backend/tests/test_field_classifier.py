import asyncio
import json

import pytest
from app.agents.field_classifier import FieldClassifier
from app.agents.llm_provider import TASK_FIELD_CLASSIFICATION, LLMProviderError, MockLLMProvider
from app.ontology.loader import FieldOntology
from app.schemas.form_sessions import FieldObject

ontology = FieldOntology()


def field(**kwargs) -> FieldObject:
    return FieldObject(field_id=kwargs.pop("field_id", "f1"), **kwargs)


def classifier(responder=None) -> FieldClassifier:
    return FieldClassifier(ontology, MockLLMProvider(responder), threshold=0.75)


@pytest.mark.parametrize(
    ("kwargs", "concept", "method"),
    [
        ({"label": "Applicant's complete name"}, "personal.full_name", "label"),
        ({"label": "Correspondence PIN code"}, "address.zipcode", "label"),
        ({"label": "Your answer", "autocomplete": "email"}, "personal.email", "autocomplete"),
        ({"label": "", "placeholder": "Mobile number"}, "personal.phone", "placeholder"),
        ({"label": "Contact", "input_type": "email"}, "personal.email", "input_type"),
        ({"label": "", "name": "date_of_birth"}, "personal.date_of_birth", "name"),
    ],
)
def test_deterministic_rules_classify_obvious_fields(kwargs, concept, method) -> None:
    result = classifier().classify_deterministic(field(**kwargs))
    assert result.concept == concept
    assert result.method == method


def test_ambiguous_label_is_not_resolved_deterministically() -> None:
    result = classifier().classify_deterministic(field(label="Branch"))
    assert result.ambiguous and not classifier().is_resolved(result)


def test_name_attribute_breaks_a_tie() -> None:
    result = classifier().classify_deterministic(field(label="Branch", name="bank_branch_name"))
    assert result.concept == "financial.branch_name"


def test_name_in_another_persons_section_is_never_the_users_name() -> None:
    result = classifier().classify_deterministic(field(label="Name", section="Father's details"))
    assert result.concept is None and result.other_person


def test_llm_is_called_once_for_all_unresolved_fields_and_output_is_validated() -> None:
    prompts: list[str] = []

    def respond(task: str, prompt: str) -> str:
        assert task == TASK_FIELD_CLASSIFICATION
        prompts.append(prompt)
        return json.dumps(
            {
                "classifications": [
                    {"field_id": "a", "concept": "education.field_of_study", "confidence": 0.9},
                    {"field_id": "b", "concept": "not.a.concept", "confidence": 0.99},
                    {"field_id": "c", "concept": "personal.full_name", "confidence": 0.9},
                ]
            }
        )

    c = classifier(respond)
    fields = [
        field(field_id="a", label="Branch"),
        field(field_id="b", label="Favourite colour"),
        field(field_id="c", label="Name", section="Guardian details"),
    ]
    prior = {f.field_id: c.classify_deterministic(f) for f in fields}
    results = asyncio.run(c.classify_with_llm(fields, prior))
    assert len(prompts) == 1
    assert results["a"].concept == "education.field_of_study" and results["a"].method == "llm"
    assert results["b"].concept is None  # unknown concepts are rejected
    assert results["c"].concept is None  # the user's own name is never used for another person
    assert "UNTRUSTED_FORM_FIELDS" in prompts[0]


@pytest.mark.parametrize("bad", ["not json", json.dumps({"classifications": "nope"})])
def test_invalid_llm_output_marks_fields_as_errors(bad: str) -> None:
    c = classifier(lambda task, prompt: bad)
    fields = [field(field_id="a", label="Favourite colour")]
    results = asyncio.run(c.classify_with_llm(fields, {}))
    assert results["a"].concept is None
    assert "invalid output" in (results["a"].error or "")


def test_provider_failure_marks_fields_as_errors() -> None:
    def boom(task: str, prompt: str) -> str:
        raise LLMProviderError("down")

    results = asyncio.run(classifier(boom).classify_with_llm([field(label="Favourite colour")], {}))
    assert results["f1"].error == "AI classification is unavailable"
