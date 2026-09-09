from app.core.config import Settings


def test_settings_load_explicit_values() -> None:
    settings = Settings(app_name="Test Application", mongodb_database="test_db")
    assert settings.app_name == "Test Application"
    assert settings.mongodb_database == "test_db"

