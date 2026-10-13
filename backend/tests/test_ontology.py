import pytest
from app.ontology.loader import FieldOntology, normalize_tokens

ontology = FieldOntology()


@pytest.mark.parametrize(
    ("text", "concept"),
    [
        ("Applicant's complete name", "personal.full_name"),
        ("Full legal name", "personal.full_name"),
        ("Correspondence PIN code", "address.zipcode"),
        ("Postal code", "address.zipcode"),
        ("Father's Name", "personal.father_name"),
        ("Name of father", "personal.father_name"),
        ("First name", "personal.first_name"),
        ("Date of Birth (DD/MM/YYYY)", "personal.date_of_birth"),
        ("Mobile No.", "personal.phone"),
        ("E-mail", "personal.email"),
        ("emailAddress", "personal.email"),
        ("FATHER_NAME", "personal.father_name"),
        ("BANK_ACCOUNT_NUMBER", "financial.account_number"),
    ],
)
def test_phrase_matching_finds_the_right_concept(text: str, concept: str) -> None:
    assert ontology.match_text(text)[0].concept == concept


def test_longer_alias_beats_contained_shorter_alias() -> None:
    concepts = [m.concept for m in ontology.match_text("Father's Name")]
    assert concepts == ["personal.father_name"]  # "name" alone is subsumed


def test_substrings_do_not_match() -> None:
    # Regression: containment matching mapped these to full_name / bank_name.
    assert all(m.concept != "personal.full_name" for m in ontology.match_text("Username"))
    assert ontology.match_text("Branding") == []


def test_genuinely_ambiguous_label_reports_both_concepts() -> None:
    matches = ontology.match_text("Branch")
    assert {m.concept for m in matches} == {"education.field_of_study", "financial.branch_name"}
    assert matches[0].score == matches[1].score


def test_concept_metadata() -> None:
    assert ontology.is_sensitive("identity.aadhaar_number")
    assert not ontology.is_sensitive("personal.email")
    assert not ontology.is_fillable("legal.consent")
    assert ontology.data_type("personal.date_of_birth") == "date"
    assert ontology.derived_from("personal.first_name") == "personal.full_name"
    assert ontology.concept_for_autocomplete("shipping postal-code") == "address.zipcode"
    assert ontology.concept_for_autocomplete("off") is None


def test_normalize_tokens() -> None:
    assert normalize_tokens("Applicant's complete name") == ("applicant", "complete", "name")
    assert normalize_tokens("dateOfBirth") == ("date", "birth")
