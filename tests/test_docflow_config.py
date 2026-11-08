"""Offline checks for private Azure configuration handling."""
import pytest
from docflow.config import ConfigurationError, load_azure_settings


def config_file(tmp_path, extra="", endpoint="https://synthetic.services.ai.azure.com"):
    path = tmp_path / ".env"
    path.write_text(f"AZURE_OPENAI_ENDPOINT={endpoint}\nAZURE_OPENAI_DEPLOYMENT=gpt-5-mini\n"
                    "AZURE_OPENAI_API_KEY='private-${KEEP_LITERAL}'\n" + extra, encoding="utf-8")
    return path


def test_dotenv_loads_shared_endpoint_and_keeps_key_private(tmp_path):
    settings = load_azure_settings(config_file(tmp_path))
    assert settings.base_url == "https://synthetic.services.ai.azure.com/openai/v1/"
    assert settings.deployment == "gpt-5-mini"
    assert settings.api_key.get_secret_value() == "private-${KEEP_LITERAL}"
    assert "private-" not in repr(settings)


def test_existing_base_url_and_model_aliases(tmp_path):
    path = tmp_path / ".env"
    path.write_text("AZURE_OPENAI_BASE_URL=https://synthetic.services.ai.azure.com/openai/v1\n"
                    "AZURE_OPENAI_MODEL=gpt-5-mini\nAZURE_OPENAI_API_KEY=fake\n")
    assert load_azure_settings(path).deployment == "gpt-5-mini"


def test_missing_file_does_not_use_ambient_key(tmp_path, monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "ambient-secret")
    with pytest.raises(ConfigurationError, match="Missing .env"):
        load_azure_settings(tmp_path / "absent")


@pytest.mark.parametrize("endpoint", [
    "http://synthetic.services.ai.azure.com", "https://synthetic.services.ai.azure.com.evil.test",
    "https://secret@synthetic.services.ai.azure.com", "https://synthetic.services.ai.azure.com?key=secret",
    "https://synthetic.services.ai.azure.com:invalid",
])
def test_bad_endpoint_errors_do_not_echo_credentials(tmp_path, endpoint):
    with pytest.raises(ConfigurationError) as error:
        load_azure_settings(config_file(tmp_path, endpoint=endpoint))
    assert "secret" not in str(error.value)
    assert "private-" not in str(error.value)


@pytest.mark.parametrize("extra", [
    "AZURE_OPENAI_MODEL=other\n",
    "AZURE_OPENAI_BASE_URL=https://other.openai.azure.com/openai/v1\n",
])
def test_conflicting_settings_fail_closed(tmp_path, extra):
    with pytest.raises(ConfigurationError):
        load_azure_settings(config_file(tmp_path, extra))
