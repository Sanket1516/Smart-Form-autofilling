"""Resume-and-form demo: concepts for a graduate application, open-question handling, no fabrication."""

import json
import re
import shutil
from pathlib import Path

import pytest
import yaml
from app.agents.field_classifier import FieldClassifier
from app.agents.graph import _DESCRIPTIVE_SUFFIXES
from app.agents.llm_provider import TASK_FIELD_VALUES, MockLLMProvider
from app.ontology.loader import FieldOntology
from app.schemas.form_sessions import FieldObject

from tests.conftest import Harness
from tests.factories import txt_bytes

ONTOLOGY_DIR = Path(__file__).resolve().parents[1] / "app" / "ontology"
FORMS_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "demo" / "forms"
ontology = FieldOntology()
classifier = FieldClassifier(ontology, MockLLMProvider(), threshold=0.7)
candidate_concepts = yaml.safe_load((ONTOLOGY_DIR / "candidate_ontology.yaml").read_text("utf-8"))[
    "concepts"
]

RESUME_FORM = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "public"
    / "demo"
    / "resume"
    / "graduate-software-engineer-application.html"
)

# form field id -> the concept the classifier must find without an LLM call
EXPECTED = {
    "full_name": "personal.full_name",
    "email": "personal.email",
    "phone": "personal.phone",
    "current_location": "personal.current_location",
    "highest_qualification": "education.degree",
    "university": "education.institution",
    "graduation_year": "education.end_year",
    "cgpa": "education.cgpa",
    "languages": "skills.programming_languages",
    "frontend": "skills.frontend",
    "backend": "skills.backend",
    "databases": "skills.databases",
    "ai_ml": "skills.ai_ml",
    "tools": "skills.tools",
    "work_experience": "experience.description",
    "responsibilities": "experience.description",
    "project_description": "project.description",
    "project_technologies": "project.technologies",
    "project_contribution": "contribution.summary",
    "technical_challenge": "challenge.summary",
    "achievements": "achievements.summary",
    "cloud_experience": "cloud.summary",
    "strengths": "strengths.summary",
    "weakness": "weaknesses.summary",
    "why_hire": "suitability.summary",
    "why_role": "motivation.summary",
    "problem_approach": "problem_solving.summary",
    "career_goals": "career.objective",
    "teamwork": "teamwork.summary",
    "improve_areas": "improvement.summary",
    "job_role": "preferences.job_role",
    "work_mode": "preferences.work_mode",
    "availability": "preferences.availability",
    "additional_info": "additional.summary",
}


def demo_form_fields() -> dict[str, FieldObject]:
    """The form's controls as the extension reports them: label, type and the name/id attributes."""
    html = RESUME_FORM.read_text("utf-8")
    fields = {}
    for field_id, label, tag, attrs in re.findall(
        r'<label class="lbl" for="([a-z_]+)">([^<]+)</label><(input|select|textarea)([^>]*)>', html
    ):
        declared = re.search(r'type="([a-z]+)"', attrs)
        input_type = tag if tag != "input" else (declared.group(1) if declared else "text")
        fields[field_id] = FieldObject(
            field_id=field_id,
            label=label,
            question=label,
            tag=tag,
            input_type=input_type,
            name=field_id,
            id=field_id,
        )
    return fields


def _field(label: str, input_type: str, field_id: str = "f1") -> FieldObject:
    return FieldObject(field_id=field_id, label=label, question=label, input_type=input_type)


@pytest.mark.skipif(not RESUME_FORM.exists(), reason="demo forms are not in this checkout")
def test_the_demo_form_has_every_expected_field() -> None:
    fields = demo_form_fields()
    assert len(fields) >= 34  # 33 classified below + "Additional Information", which the LLM reads
    assert set(EXPECTED) <= set(fields)


@pytest.mark.skipif(not RESUME_FORM.exists(), reason="demo forms are not in this checkout")
@pytest.mark.parametrize(("field_id", "concept"), sorted(EXPECTED.items()))
def test_demo_form_fields_are_classified_without_the_llm(field_id: str, concept: str) -> None:
    result = classifier.classify_deterministic(demo_form_fields()[field_id])
    assert result.concept == concept and classifier.is_resolved(result)


def test_open_questions_are_prose_and_never_extracted_as_facts() -> None:
    answer_only = {key for key, entry in candidate_concepts.items() if entry.get("answer_only")}
    assert answer_only, "the demo needs open-question concepts"
    for key in answer_only:
        assert key.endswith(
            _DESCRIPTIVE_SUFFIXES
        ), f"{key} would be treated as a verbatim-value field"
        assert ontology.is_answer_only(key)
    extraction = {key for key, _ in ontology.catalog("extraction")}
    classification = {key for key, _ in ontology.catalog("classification")}
    assert not answer_only & extraction
    assert answer_only <= classification
    # factual concepts stay extractable so structured fields fill without text generation
    assert {"skills.tools", "personal.current_location", "preferences.job_role"} <= extraction


def test_similar_questions_map_to_the_same_meaning() -> None:
    for label in (
        "What are your strongest professional attributes?",
        "What are your key strengths?",
    ):
        assert (
            classifier.classify_deterministic(_field(label, "textarea")).concept
            == "strengths.summary"
        )
    for label in (
        "What makes you a good candidate?",
        "Which qualities distinguish you from other applicants?",
    ):
        assert (
            classifier.classify_deterministic(_field(label, "textarea")).concept
            == "suitability.summary"
        )


def test_strengths_and_weaknesses_stay_apart() -> None:
    strengths = classifier.classify_deterministic(
        _field("What are your greatest strengths?", "textarea")
    )
    weakness = classifier.classify_deterministic(
        _field("What is your biggest weakness, and how are you improving it?", "textarea")
    )
    assert strengths.concept != weakness.concept


def test_cloud_experience_is_not_answered_from_a_tool_list() -> None:
    """'cloud' and 'docker' are aliases of the skills list; an experience question must not map there."""
    result = classifier.classify_deterministic(
        _field("Describe your experience with cloud computing.", "textarea")
    )
    assert result.concept == "cloud.summary"
    assert result.concept != "skills.cloud_devops"


def test_new_aliases_do_not_collide_with_existing_concepts() -> None:
    existing = {
        alias.lower(): key
        for key, entry in ontology.concepts.items()
        if key not in candidate_concepts
        for alias in entry.get("aliases", [])
    }
    for key, entry in candidate_concepts.items():
        assert entry["canonical_name"] == key
        for alias in entry["aliases"]:
            assert (
                alias.lower() not in existing
            ), f"{alias!r} is already an alias of {existing[alias.lower()]}"


@pytest.mark.skipif(not FORMS_DIR.exists(), reason="demo forms are not in this checkout")
def test_existing_demo_forms_are_classified_exactly_as_before(tmp_path: Path) -> None:
    """The new concepts must not change what any label of the 15 judge-demo forms maps to."""
    baseline_dir = tmp_path / "ontology"
    shutil.copytree(ONTOLOGY_DIR, baseline_dir, ignore=shutil.ignore_patterns("__pycache__"))
    main = baseline_dir / "field_ontology.yaml"
    data = yaml.safe_load(main.read_text("utf-8"))
    data["includes"] = [name for name in data["includes"] if name != "candidate_ontology.yaml"]
    main.write_text(yaml.safe_dump(data), "utf-8")
    baseline = FieldOntology(main)

    labels: set[str] = set()
    for form in FORMS_DIR.glob("form-*.html"):
        html = form.read_text("utf-8")
        labels.update(
            re.sub(r"<[^>]+>", "", m).strip()
            for m in re.findall(r"<(?:label|legend)[^>]*>(.*?)</(?:label|legend)>", html, re.S)
        )
        labels.update(re.findall(r'aria-label="([^"]+)"', html))
    labels = {label for label in labels if label}
    assert len(labels) > 50

    def shape(onto: FieldOntology, text: str) -> list[tuple[str, float]]:
        return [(m.concept, m.score) for m in onto.match_text(text)]

    changed = {
        label: (shape(baseline, label), shape(ontology, label))
        for label in labels
        if shape(baseline, label) != shape(ontology, label)
    }
    assert not changed, changed


# ---------------------------------------------------------------- pipeline (real MongoDB, mock LLM)

RESUME_TEXT = [
    "DEMO DATA - fictional profile",
    "Kavya Suresh Deshpande",
    "Strengths",
    "Analytical problem-solving. Quick learning and adaptability. Team collaboration.",
    "Weaknesses",
    "I sometimes spend extra time refining technical solutions because I want them to be reliable.",
    "Work Experience",
    "Software Development Intern at DemoTech Solutions. Developed REST API endpoints and wrote automated API tests.",
    "Tools: Git, GitHub, Docker, Postman",
]


def _analyze(harness: Harness, headers: dict, fields: list[dict]) -> dict[str, dict]:
    session = harness.client.post(
        "/api/v1/forms/sessions",
        headers=headers,
        json={
            "website_origin": "http://localhost:5173",
            "page_url": "http://localhost:5173/demo/resume/form.html",
            "form_id": "grad",
        },
    ).json()["data"]["session_id"]
    response = harness.client.post(
        f"/api/v1/forms/sessions/{session}/analyze", headers=headers, json={"fields": fields}
    )
    assert response.status_code == 202, response.text
    recs = harness.client.get(f"/api/v1/forms/sessions/{session}/recommendations", headers=headers)
    return {r["field_id"]: r for r in recs.json()["data"]["recommendations"]}


@pytest.mark.mongo
def test_open_questions_are_grounded_and_unsupported_claims_are_dropped(harness: Harness) -> None:
    def answer(prompt: str) -> str:
        if not all(f"FIELD {name}" in prompt for name in ("strengths", "cloud", "teamwork")):
            return json.dumps({"answers": []})  # the retry pass re-asks only the still-empty fields
        chunk = {
            name: re.search(rf"FIELD {name}.*?\[(F\d+C\d+)\]", prompt, re.S).group(1)
            for name in ("strengths", "cloud", "teamwork")
        }
        return json.dumps(
            {
                "answers": [
                    {
                        "field_id": "strengths",
                        "chunk_id": chunk["strengths"],
                        "confidence": 0.9,
                        "value": "My strengths include analytical problem-solving and adaptability.",
                        "quote": "Analytical problem-solving",
                    },
                    # a claim the resume does not support: the quote is not in the retrieved text
                    {
                        "field_id": "cloud",
                        "chunk_id": chunk["cloud"],
                        "confidence": 0.95,
                        "value": "I deployed services on AWS.",
                        "quote": "deployed services on AWS",
                    },
                    {
                        "field_id": "teamwork",
                        "chunk_id": chunk["teamwork"],
                        "confidence": 0.9,
                        "value": None,
                        "quote": "",
                    },
                ]
            }
        )

    harness.llm.handlers[TASK_FIELD_VALUES] = answer
    harness.client.app.state.retrieval_service.min_similarity = 0.0  # lexical test embeddings
    headers = harness.register()
    document_id = harness.upload(headers, "DEMO_RESUME_test.txt", txt_bytes(RESUME_TEXT)).json()[
        "data"
    ]["document_id"]
    harness.wait_processed(headers, document_id)

    recs = _analyze(
        harness,
        headers,
        [
            {
                "field_id": "strengths",
                "label": "What are your greatest strengths?",
                "input_type": "textarea",
            },
            {
                "field_id": "cloud",
                "label": "Describe your experience with cloud computing.",
                "input_type": "textarea",
            },
            {
                "field_id": "teamwork",
                "label": "How do you work in a team?",
                "input_type": "textarea",
            },
        ],
    )

    assert recs["strengths"]["concept"] == "strengths.summary"
    assert (
        recs["strengths"]["retrieval_type"] == "rag" and recs["strengths"]["requires_confirmation"]
    )
    assert recs["strengths"]["source"]["document_name"] == "DEMO_RESUME_test.txt"
    assert "Analytical problem-solving" in recs["strengths"]["source"]["snippet"]
    for field_id in ("cloud", "teamwork"):
        assert recs[field_id]["recommended_value"] is None
        assert recs[field_id]["status"] == "missing_information"


def test_a_null_quote_for_an_unanswered_field_does_not_discard_the_batch() -> None:
    from app.agents.graph import _AnswersOutput
    from app.agents.json_output import parse_model

    raw = (
        '{"answers": [{"field_id": "a", "value": null, "chunk_id": null, "quote": null, "confidence": null},'
        ' {"field_id": "b", "value": "x", "chunk_id": "F1C1", "quote": "x", "confidence": 0.9}]}'
    )
    answers = parse_model(raw, _AnswersOutput).answers
    assert [a.quote for a in answers] == ["", "x"]
    assert answers[0].confidence == 0.0


def test_quote_matching_ignores_typographic_punctuation_but_not_invented_text() -> None:
    from app.extraction.normalize import appears_in

    chunk = "I led the team - and reviewed every pull request. It's what I enjoy."
    assert appears_in("I led the team \u2014 and reviewed every pull request\u2026", chunk)
    assert appears_in("\u201cIt\u2019s what I enjoy.\u201d", chunk)
    assert not appears_in("I led the team and mentored three interns", chunk)
