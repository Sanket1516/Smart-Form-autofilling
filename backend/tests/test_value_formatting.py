from app.agents.value_formatting import date_hint, format_for_field
from app.schemas.form_sessions import FieldObject


def field(**kwargs) -> FieldObject:
    return FieldObject(field_id="f", **kwargs)


GENDER = [
    {"value": "M", "label": "Male"},
    {"value": "F", "label": "Female"},
    {"value": "O", "label": "Other"},
]


def test_date_is_formatted_for_the_control() -> None:
    assert format_for_field(field(input_type="date"), "date", "1996-02-14").value == "1996-02-14"
    text_field = field(input_type="text", placeholder="DD/MM/YYYY")
    assert date_hint(text_field) == "DD/MM/YYYY"
    assert format_for_field(text_field, "date", "1996-02-14").value == "14/02/1996"
    assert format_for_field(field(input_type="date"), "date", "not a date").value is None


def test_select_matching_is_exact_never_substring() -> None:
    select = field(input_type="select", options=GENDER)
    result = format_for_field(select, "string", "Male")
    assert result.value == "M" and result.selected_option == {"label": "Male", "value": "M"}
    assert format_for_field(select, "string", "female").value == "F"
    assert format_for_field(select, "string", "f").value == "F"  # synonym
    missing = format_for_field(select, "string", "Prefer not to say")
    assert missing.value is None and "None of the options" in (missing.problem or "")


def test_radio_with_duplicate_matches_is_left_for_review() -> None:
    radio = field(
        input_type="radio",
        options=[{"value": "yes", "label": "Yes"}, {"value": "y", "label": "Yes"}],
    )
    assert format_for_field(radio, "string", "yes").value is None


def test_checkbox_only_ticked_for_explicit_yes() -> None:
    box = field(input_type="checkbox")
    assert format_for_field(box, "string", "yes").value == "true"
    assert format_for_field(box, "string", "Avery").value is None


def test_typed_values_are_validated() -> None:
    assert (
        format_for_field(field(input_type="email"), "email", "Avery@Example.COM").value
        == "avery@example.com"
    )
    assert format_for_field(field(input_type="email"), "email", "nope").value is None
    assert (
        format_for_field(field(input_type="tel"), "phone", "+1 555 010 4477").value
        == "+15550104477"
    )
    assert format_for_field(field(max_length=3), "string", "abcdef").value is None


def test_multiple_values_require_a_choice() -> None:
    assert format_for_field(field(), "string", ["a", "b"]).value is None
