"""Settings come only from environment variables (12-factor).

Any secret can also be read from a file: if NAME_FILE is set, the file's
content is used instead of NAME (Kubernetes / Docker secrets mount files).
"""

import os
from dataclasses import dataclass
from urllib.parse import quote


class ConfigError(Exception):
    pass


def env(name: str, default: str | None = None) -> str | None:
    path = os.environ.get(f"{name}_FILE")
    if path:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_owner: str
    app_version: str
    git_sha: str
    db_url: str
    clickhouse_url: str | None
    storage_backend: str
    bucket: str
    secret_key: str
    log_level: str
    log_format: str
    password_min_length: int

    @property
    def db_engine(self) -> str:
        return self.db_url.split(":", 1)[0].split("+", 1)[0]

    @property
    def secrets(self) -> list[str]:
        """Values that must never appear in logs."""
        values = [self.secret_key, env("DB_PASSWORD") or ""]
        return [v for v in values if len(v) >= 4]


def load_settings() -> Settings:
    secret_key = env("SECRET_KEY") or ""
    if len(secret_key) < 32:
        raise ConfigError(
            "SECRET_KEY (or SECRET_KEY_FILE) must be set and at least 32 characters long. "
            "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
        )

    db_url = env("DB_URL") or ""
    if not db_url:
        raise ConfigError("DB_URL is required, e.g. postgresql+psycopg://app_rw:${DB_PASSWORD}@db:5432/campus")
    if "${DB_PASSWORD}" in db_url:
        password = env("DB_PASSWORD")
        if not password:
            raise ConfigError("DB_URL contains ${DB_PASSWORD} but DB_PASSWORD(_FILE) is not set")
        db_url = db_url.replace("${DB_PASSWORD}", quote(password, safe=""))
    if not db_url.startswith(("postgresql", "mysql", "sqlite")):
        raise ConfigError("DB_URL must be PostgreSQL (postgresql+psycopg://) or MySQL (mysql+pymysql://)")

    backend = (env("STORAGE_BACKEND", "local") or "local").lower()
    if backend not in ("local", "s3", "gcs"):
        raise ConfigError("STORAGE_BACKEND must be local, s3 or gcs")
    bucket = env("BUCKET", "./data/uploads" if backend == "local" else "") or ""
    if not bucket:
        raise ConfigError(f"BUCKET is required for STORAGE_BACKEND={backend}")

    return Settings(
        app_name=env("APP_NAME", "campus-app"),
        app_owner=env("APP_OWNER", "unknown student"),
        app_version=env("APP_VERSION", "dev"),
        git_sha=env("GIT_SHA", ""),
        db_url=db_url,
        clickhouse_url=env("CLICKHOUSE_URL") or None,
        storage_backend=backend,
        bucket=bucket,
        secret_key=secret_key,
        log_level=(env("LOG_LEVEL", "INFO") or "INFO").upper(),
        log_format=(env("LOG_FORMAT", "json") or "json").lower(),
        password_min_length=int(env("PASSWORD_MIN_LENGTH", "12") or 12),
    )
