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
    report_key: str
    reports: dict
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


def _resolve_reports(parser: configparser.ConfigParser) -> dict:
    """Build the catalog {clave: rutaAbsoluta} from [reports].

    Falls back to a legacy ``[service] report_path`` as a single ``default``
    entry so older configs keep working.
    """
    reports = dict(parser.items("reports")) if parser.has_section("reports") else {}
    if not reports:
        legacy = _get(parser, "service", "report_path", fallback="")
        if legacy:
            reports = {"default": legacy}
    if not reports:
        raise ConfigError("No hay reportes configurados. Agrega la seccion [reports] en config.ini")
    return reports


def load_settings(
    config_path: str | os.PathLike = "config.ini",
    env_path: str | os.PathLike = ".env",
    report: str | None = None,
    timeout: int | None = None,
) -> Settings:
    """Build ``Settings`` from ``config.ini`` + ``.env``.

    Overrides win in this order: explicit argument > variable de entorno >
    config.ini. Esto permite fijar credenciales, timeout y el reporte a consumir
    desde ``.env`` sin editar el codigo ni recompilar.

    Variables de entorno soportadas:
      * ``CERT_USER`` / ``CERT_PASSWORD`` — credenciales.
      * ``CERT_TIMEOUT``               — timeout en segundos.
      * ``CERT_REPORT``                — clave del reporte a consumir ([reports]).
    """
    load_dotenv(env_path)

    parser = configparser.ConfigParser()
    # Preservar mayus/minus en las claves (nombres de reporte los llevan).
    parser.optionxform = str
    if not parser.read(config_path, encoding="utf-8"):
        raise ConfigError(f"No se encontro el archivo de configuracion: {config_path}")

    user = os.getenv("CERT_USER") or _get(parser, "service", "user", fallback="")
    password = os.getenv("CERT_PASSWORD") or _get(parser, "service", "password", fallback="")
    if not user or not password:
        raise ConfigError(
            "Credenciales ausentes. Define CERT_USER y CERT_PASSWORD en .env"
        )

    # -- timeout: arg > CERT_TIMEOUT > config.ini -----------------------------
    timeout_raw = timeout if timeout is not None else (
        os.getenv("CERT_TIMEOUT") or _get(parser, "service", "timeout", fallback="300")
    )
    try:
        timeout_value = int(timeout_raw)
    except (ValueError, TypeError) as exc:
        raise ConfigError(f"timeout invalido: '{timeout_raw}'") from exc
    if timeout_value <= 0:
        raise ConfigError(f"timeout debe ser mayor a 0, recibido: {timeout_value}")

    # -- reporte: arg > CERT_REPORT > default_report > primero del catalogo ----
    reports = _resolve_reports(parser)
    requested = (
        report
        or os.getenv("CERT_REPORT")
        or _get(parser, "service", "default_report", fallback="")
        or next(iter(reports))
    )
    # Match case-insensitive: el usuario no debe preocuparse por mayus/minus.
    lookup = {key.lower(): key for key in reports}
    if requested.lower() not in lookup:
        raise ConfigError(
            f"Reporte '{requested}' no existe. Disponibles: {', '.join(sorted(reports))}"
        )
    report_key = lookup[requested.lower()]

    verify_ssl = str(_get(parser, "service", "verify_ssl", fallback="false")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    return Settings(
        host=_get(parser, "service", "host"),
        service_path=_get(parser, "service", "service_path"),
        report_path=reports[report_key],
        report_key=report_key,
        reports=reports,
        user=user,
        password=password,
        timeout=timeout_value,
        verify_ssl=verify_ssl,
        output_dir=Path(_get(parser, "output", "output_dir", fallback="output")),
        log_dir=Path(_get(parser, "logging", "log_dir", fallback="logs")),
        log_level=_get(parser, "logging", "log_level", fallback="INFO"),
    )
