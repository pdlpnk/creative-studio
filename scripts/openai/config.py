"""Configuration helpers for the OpenAI Vision Adapter.

The adapter deliberately has no dependency on python-dotenv.  It loads a local
project ``.env`` file when present and never prints or persists the API key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[1]
DEFAULT_DOTENV_PATH = PROJECT_ROOT / ".env"
DEFAULT_MODEL = "gpt-5.6"
DEFAULT_TIMEOUT_SECONDS = 45.0


class ConfigurationError(RuntimeError):
    """Raised when required local configuration is missing or invalid."""


def load_dotenv(path: Path = DEFAULT_DOTENV_PATH) -> None:
    """Load simple KEY=VALUE lines without overwriting real environment values."""
    if not path.is_file():
        return

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            raise ConfigurationError(f"Invalid .env line {line_number}: expected KEY=VALUE")

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ConfigurationError(f"Invalid .env line {line_number}: empty key")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class OpenAISettings:
    api_key: str
    model: str
    timeout_seconds: float


def load_settings(dotenv_path: Path = DEFAULT_DOTENV_PATH) -> OpenAISettings:
    """Return validated OpenAI settings after optionally loading ``.env``."""
    load_dotenv(dotenv_path)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError(
            "OPENAI_API_KEY is not configured. Add it to .env or the environment."
        )

    model = os.getenv("OPENAI_VISION_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    timeout_value = os.getenv("OPENAI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        timeout_seconds = float(timeout_value)
    except ValueError as error:
        raise ConfigurationError("OPENAI_TIMEOUT_SECONDS must be a number.") from error
    if timeout_seconds <= 0:
        raise ConfigurationError("OPENAI_TIMEOUT_SECONDS must be greater than zero.")

    return OpenAISettings(
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
    )
