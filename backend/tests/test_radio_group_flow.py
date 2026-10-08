"""Focused tests for structured radio recommendations in the session flow."""

from app.agents.prompts import build_bulk_fill_prompt
from app.api.v1.forms import _resolve_radio_option, _selected_radio_option
from app.schemas.form_sessions import ApprovedValueData, FieldObject, FormFieldOption


def _gender_field() -> FieldObject:
    return FieldObject(
        field_id="radio_form_gender",
        label="Gender",
        question="Gender",
        input_type="radio",
        options=[
            FormFieldOption(option_id="male", label="Male", value="male"),
            FormFieldOption(option_id="female", label="Female", value="female"),
            FormFieldOption(option_id="other", label="Other", value="other"),
            FormFieldOption(option_id="disabled", label="Disabled", value="disabled", disabled=True),
        ],
    )


def test_radio_answer_resolves_to_one_exact_enabled_label_value_pair():
    field = _gender_field()
    assert _resolve_radio_option(field, {
        "value": "female",
        "selected_option": {"label": "Female", "value": "female"},
    }) == {"label": "Female", "value": "female"}
    assert _resolve_radio_option(field, {"value": "Other"}) == {
        "label": "Other", "value": "other",
    }
    assert _resolve_radio_option(field, {
        "value": "female",
        "selected_option": {"label": "Female", "value": "male"},
    }) is None
    assert _resolve_radio_option(field, {"value": "disabled"}) is None


def test_radio_bulk_prompt_contains_full_options_and_structured_response_contract():
    prompt = build_bulk_fill_prompt(facts=[], fields=[_gender_field().model_dump()])
    assert "Options: [{'label': 'Male', 'value': 'male'}" in prompt
    assert "'label': 'Female', 'value': 'female'" in prompt
    assert '"selected_option": {"label":"exact option label","value":"exact option value"}' in prompt
    assert "question='Gender'" not in prompt  # Question is presented as the field label.
    assert "Label: 'Gender'" in prompt


def test_approved_radio_value_is_returned_as_structured_option():
    options = [
        {"label": "Male", "value": "male"},
        {"label": "Female", "value": "female"},
    ]
    selected_option = _selected_radio_option(options, "female")
    assert selected_option == {"label": "Female", "value": "female"}
    assert _selected_radio_option(options, "unknown") is None
    response_value = ApprovedValueData(
        field_id="radio_form_gender",
        concept="gender",
        value="female",
        confidence=1.0,
        requires_confirmation=False,
        input_type="radio",
        selected_option=selected_option,
    )
    assert response_value.model_dump()["selected_option"] == {
        "label": "Female", "value": "female",
    }
