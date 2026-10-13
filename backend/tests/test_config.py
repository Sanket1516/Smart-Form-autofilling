import pytest
from app.core.config import Settings
from pydantic import ValidationError

SECRET = "x" * 40


def test_settings_load_explicit_values() -> None:
    settings = Settings(
        jwt_secret_key=SECRET, app_name="Test Application", mongodb_database="test_db"
    )
    assert settings.app_name == "Test Application"
    assert settings.mongodb_database == "test_db"


@pytest.mark.parametrize(
    "secret", ["short", "replace_this_with_a_long_random_string_at_least_32_chars"]
)
def test_weak_or_placeholder_jwt_secret_is_rejected(secret: str) -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key=secret)


def test_unknown_llm_provider_is_rejected_not_silently_mocked() -> None:
    with pytest.raises(ValidationError, match="LLM_PROVIDER"):
        Settings(jwt_secret_key=SECRET, llm_provider="gpt-local")


def test_real_provider_requires_api_key() -> None:
    with pytest.raises(ValidationError, match="LLM_API_KEY"):
        Settings(jwt_secret_key=SECRET, llm_provider="google", llm_api_key="")


def test_gemini_alias_maps_to_google() -> None:
    settings = Settings(
        jwt_secret_key=SECRET, llm_provider="gemini", llm_api_key="k", llm_model="m"
    )
    assert settings.llm_provider == "google"


def test_unsupported_jwt_algorithm_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key=SECRET, jwt_algorithm="none")


def test_cloudinary_requires_credentials() -> None:
    with pytest.raises(ValidationError, match="Cloudinary"):
        Settings(jwt_secret_key=SECRET, storage_provider="cloudinary", cloudinary_cloud_name="")


def test_chunk_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key=SECRET, rag_chunk_size=100, rag_chunk_overlap=100)
