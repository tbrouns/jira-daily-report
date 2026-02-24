from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    jira_base_url: str
    jira_email: str
    jira_api_token: str
    openai_api_key: str
    openai_model: str
    openai_temperature: float
    timezone: str
    system_prompt_path: Path


class ConfigError(ValueError):
    pass


def load_config() -> AppConfig:
    load_dotenv()

    jira_base_url = _require_env("JIRA_BASE_URL").rstrip("/")
    jira_email = _require_env("JIRA_EMAIL")
    jira_api_token = _require_env("JIRA_API_TOKEN")
    openai_api_key = _require_env("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1")
    timezone = os.getenv("TIMEZONE", "Europe/Amsterdam")
    system_prompt_path = Path(os.getenv("SYSTEM_PROMPT_PATH", "prompts/system_instructions.md"))

    temperature_raw = os.getenv("OPENAI_TEMPERATURE", "0.2")
    try:
        openai_temperature = float(temperature_raw)
    except ValueError as exc:
        raise ConfigError("OPENAI_TEMPERATURE must be a valid float") from exc

    return AppConfig(
        jira_base_url=jira_base_url,
        jira_email=jira_email,
        jira_api_token=jira_api_token,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        openai_temperature=openai_temperature,
        timezone=timezone,
        system_prompt_path=system_prompt_path,
    )


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value
