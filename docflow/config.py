"""Load Azure settings from the local .env without making network requests."""
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlsplit

from dotenv import dotenv_values
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationError(ValueError):
    """A configuration error safe to display without credential values."""


@dataclass(frozen=True)
class AzureSettings:
    base_url: str
    deployment: str
    api_key: SecretStr
    timeout_seconds: float = 20.0
    max_retries: int = 0
    max_output_tokens: int = 1024
    reasoning_effort: str = "minimal"


def load_azure_settings(path: Path | None = None) -> AzureSettings:
    path = Path(path) if path is not None else ROOT / ".env"
    if not path.is_file():
        raise ConfigurationError("Missing .env; use the configuration supplied by the organizer.")
    # Do not expand dollar signs in credentials or search parent directories.
    try:
        values = dotenv_values(path, encoding="utf-8-sig", interpolate=False)
    except (OSError, UnicodeError):
        raise ConfigurationError("Cannot read the local .env file.") from None

    def setting(name):
        return (values.get(name) or "").strip()

    deployment = setting("AZURE_OPENAI_DEPLOYMENT") or setting("AZURE_OPENAI_MODEL")
    if (setting("AZURE_OPENAI_DEPLOYMENT") and setting("AZURE_OPENAI_MODEL")
            and setting("AZURE_OPENAI_DEPLOYMENT") != setting("AZURE_OPENAI_MODEL")):
        raise ConfigurationError("Conflicting Azure deployment settings.")
    key = setting("AZURE_OPENAI_API_KEY")
    if not deployment or not key:
        raise ConfigurationError("Set AZURE_OPENAI_DEPLOYMENT and AZURE_OPENAI_API_KEY in .env.")
    endpoint = setting("AZURE_OPENAI_ENDPOINT").rstrip("/")
    explicit_base = setting("AZURE_OPENAI_BASE_URL").rstrip("/")
    candidate = explicit_base or endpoint
    try:
        parsed = urlsplit(candidate)
        valid = (parsed.scheme == "https" and not parsed.username and not parsed.password
                 and parsed.port in (None, 443) and not parsed.query and not parsed.fragment
                 and re.fullmatch(r"[a-z0-9-]+\.(?:services\.ai|openai)\.azure\.com", parsed.hostname or "")
                 and parsed.path.rstrip("/") in ("", "/openai/v1"))
    except ValueError:
        valid = False
    if not valid:
        raise ConfigurationError("Set a valid Azure HTTPS resource endpoint or /openai/v1/ URL.")
    base = candidate if parsed.path.rstrip("/") else candidate + "/openai/v1"
    if endpoint and explicit_base and endpoint not in (base, base.removesuffix("/openai/v1")):
        raise ConfigurationError("Azure endpoint and base URL disagree.")
    return AzureSettings(base + "/", deployment, SecretStr(key))
