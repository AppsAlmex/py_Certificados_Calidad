"""External configuration (Tarea 8, Dependency Inversion Principle).

Non-secret settings live in ``config.ini``; credentials live in ``.env`` (never
committed). Everything is loaded into an immutable ``Settings`` object that the
rest of the system depends on as an abstraction.
"""
from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .exceptions import ConfigError


@dataclass(frozen=True)
class Settings:
    host: str
    service_path: str
    report_path: str
    user: str
    password: str
    timeout: int
    verify_ssl: bool
    output_dir: Path
    log_dir: Path
    log_level: str

    @property
    def service_url(self) -> str:
        return f"{self.host}{self.service_path}"


def _get(parser: configparser.ConfigParser, section: str, option: str, fallback=None):
    try:
        return parser.get(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError):
        if fallback is None:
            raise ConfigError(f"Falta configuracion [{section}] {option}")
        return fallback


def load_settings(
    config_path: str | os.PathLike = "config.ini",
    env_path: str | os.PathLike = ".env",
) -> Settings:
    """Build ``Settings`` from ``config.ini`` + ``.env``.

    Environment variables (``CERT_USER``, ``CERT_PASSWORD``) win over the file so
    the same config can run in CI/containers without editing files on disk.
    """
    load_dotenv(env_path)

    parser = configparser.ConfigParser()
    if not parser.read(config_path, encoding="utf-8"):
        raise ConfigError(f"No se encontro el archivo de configuracion: {config_path}")

    user = os.getenv("CERT_USER") or _get(parser, "service", "user", fallback="")
    password = os.getenv("CERT_PASSWORD") or _get(parser, "service", "password", fallback="")
    if not user or not password:
        raise ConfigError(
            "Credenciales ausentes. Define CERT_USER y CERT_PASSWORD en .env"
        )

    try:
        timeout = int(_get(parser, "service", "timeout", fallback="300"))
    except ValueError as exc:
        raise ConfigError(f"timeout invalido: {exc}") from exc

    verify_ssl = str(_get(parser, "service", "verify_ssl", fallback="false")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    return Settings(
        host=_get(parser, "service", "host"),
        service_path=_get(parser, "service", "service_path"),
        report_path=_get(parser, "service", "report_path"),
        user=user,
        password=password,
        timeout=timeout,
        verify_ssl=verify_ssl,
        output_dir=Path(_get(parser, "output", "output_dir", fallback="output")),
        log_dir=Path(_get(parser, "logging", "log_dir", fallback="logs")),
        log_level=_get(parser, "logging", "log_level", fallback="INFO"),
    )
