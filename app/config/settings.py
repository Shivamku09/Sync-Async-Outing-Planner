from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, model_validator


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class ApplicationSettings(BaseModel):
    name: str
    environment: str = "production"


class DatabaseSettings(BaseModel):
    url: str
    pool_size: int = Field(default=10, ge=1)
    max_overflow: int = Field(default=10, ge=0)


class RabbitMQSettings(BaseModel):
    url: str
    planner_prefetch: int = Field(default=4, ge=1)
    callback_prefetch: int = Field(default=8, ge=1)


class CallbackSettings(BaseModel):
    connect_timeout_seconds: float = Field(default=2.0, gt=0)
    read_timeout_seconds: float = Field(default=5.0, gt=0)
    max_response_bytes: int = Field(default=65_536, ge=1)
    max_attempts: int = Field(default=4, ge=1)
    retry_delays_seconds: list[int] = Field(default_factory=lambda: [5, 30, 120])
    allow_localhost: bool = False
    allowed_hosts: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_retry_schedule(self) -> "CallbackSettings":
        if len(self.retry_delays_seconds) != self.max_attempts - 1:
            raise ValueError("retry_delays_seconds must contain max_attempts - 1 entries")
        if any(delay < 1 for delay in self.retry_delays_seconds):
            raise ValueError("retry delays must be at least one second")
        return self


class OutboxSettings(BaseModel):
    batch_size: int = Field(default=50, ge=1)
    poll_interval_seconds: float = Field(default=0.5, gt=0)


class APISettings(BaseModel):
    default_page_size: int = Field(default=20, ge=1)
    maximum_page_size: int = Field(default=100, ge=1)
    async_backlog_limit: int = Field(default=10_000, ge=1)


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    application: ApplicationSettings
    database: DatabaseSettings
    rabbitmq: RabbitMQSettings
    callback: CallbackSettings
    outbox: OutboxSettings
    api: APISettings


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def _coerce(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    parsed = yaml.safe_load(value)
    if isinstance(parsed, (list, dict)):
        return parsed
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _apply_environment(data: dict[str, Any]) -> None:
    aliases = {
        "DATABASE_URL": ("database", "url"),
        "RABBITMQ_URL": ("rabbitmq", "url"),
    }
    for env_name, path in aliases.items():
        if env_name in os.environ:
            data.setdefault(path[0], {})[path[1]] = os.environ[env_name]

    for key, value in os.environ.items():
        if not key.startswith("APP__"):
            continue
        path = [part.lower() for part in key.removeprefix("APP__").split("__")]
        target = data
        for part in path[:-1]:
            target = target.setdefault(part, {})
        target[path[-1]] = _coerce(value)


def load_settings(config_dir: Path | None = None) -> Settings:
    directory = config_dir or Path(__file__).parent
    data = _read_yaml(directory / "base.yaml")
    environment = os.getenv("APP_ENV", data.get("application", {}).get("environment", "production"))
    environment_file = directory / f"{environment}.yaml"
    data = _deep_merge(data, _read_yaml(environment_file))
    _apply_environment(data)
    return Settings.model_validate(data)
