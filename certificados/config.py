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

from dotenv import load_dotenv, set_key

from .exceptions import ConfigError

# Limite de seguridad de concurrencia. No se configura por ningun
# medio (ni config.ini, ni .env, ni CLI, ni GUI). workers valido = [1, MAX_WORKERS].
MAX_WORKERS = 100
MIN_WORKERS = 1


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
    connect_timeout: int
    max_workers: int
    verify_ssl: bool
    output_dir: Path
    log_dir: Path
    log_level: str

    @property
    def service_url(self) -> str:
        return f"{self.host}{self.service_path}"

    @property
    def request_timeout(self) -> tuple[int, int]:
        """(connect, read) para requests. read cubre reportes muy largos."""
        return (self.connect_timeout, self.timeout)


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
    workers: int | None = None,
) -> Settings:
    """Build ``Settings`` from ``config.ini`` + ``.env``.

    Overrides win in this order: explicit argument > variable de entorno >
    config.ini. Esto permite fijar credenciales, timeout y el reporte a consumir
    desde ``.env`` sin editar el codigo ni recompilar.

    Variables de entorno soportadas:
      * ``CERT_USER`` / ``CERT_PASSWORD`` — credenciales.
      * ``CERT_TIMEOUT``               — read timeout en segundos (reportes largos).
      * ``CERT_CONNECT_TIMEOUT``       — connect timeout en segundos.
      * ``CERT_REPORT``                — clave del reporte a consumir ([reports]).
      * ``CERT_WORKERS``               — hilos concurrentes (1 = secuencial).
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

    # -- connect timeout: CERT_CONNECT_TIMEOUT > config.ini -------------------
    try:
        connect_timeout = int(
            os.getenv("CERT_CONNECT_TIMEOUT")
            or _get(parser, "service", "connect_timeout", fallback="30")
        )
    except (ValueError, TypeError) as exc:
        raise ConfigError(f"connect_timeout invalido: {exc}") from exc
    if connect_timeout <= 0:
        raise ConfigError(f"connect_timeout debe ser mayor a 0, recibido: {connect_timeout}")

    # -- workers: arg > CERT_WORKERS > config.ini -----------------------------
    workers_raw = workers if workers is not None else (
        os.getenv("CERT_WORKERS") or _get(parser, "batch", "max_workers", fallback="1")
    )
    try:
        max_workers = int(workers_raw)
    except (ValueError, TypeError) as exc:
        raise ConfigError(f"workers invalido: '{workers_raw}'") from exc
    # Limite duro de seguridad (no configurable): 1 <= workers <= MAX_WORKERS.
    if max_workers < MIN_WORKERS:
        raise ConfigError(f"workers debe ser >= {MIN_WORKERS}, recibido: {max_workers}")
    if max_workers > MAX_WORKERS:
        raise ConfigError(
            f"workers no puede superar {MAX_WORKERS} (limite de seguridad), recibido: {max_workers}"
        )

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
        connect_timeout=connect_timeout,
        max_workers=max_workers,
        verify_ssl=verify_ssl,
        output_dir=Path(_get(parser, "output", "output_dir", fallback="output")),
        log_dir=Path(_get(parser, "logging", "log_dir", fallback="logs")),
        log_level=_get(parser, "logging", "log_level", fallback="INFO"),
    )


def save_config(
    config_path: str | os.PathLike = "config.ini",
    env_path: str | os.PathLike = ".env",
    *,
    host: str,
    service_path: str,
    timeout: int,
    connect_timeout: int,
    verify_ssl: bool,
    default_report: str,
    reports: dict,
    max_workers: int,
    output_dir: str,
    log_dir: str,
    log_level: str,
    user: str | None = None,
    password: str | None = None,
) -> None:
    """Persistir la configuracion (Settings) a config.ini y credenciales a .env.

    Usada por la GUI para guardar los ajustes internos. La logica de escritura
    vive en el nucleo (no en la GUI) para mantener la separacion de capas.
    Los comentarios previos de config.ini no se preservan al reescribir.
    """
    if not reports:
        raise ConfigError("Debe existir al menos un reporte en el catalogo")
    if default_report not in reports:
        raise ConfigError(
            f"default_report '{default_report}' no esta en el catalogo: {', '.join(reports)}"
        )
    if not (MIN_WORKERS <= max_workers <= MAX_WORKERS):
        raise ConfigError(
            f"max_workers debe estar entre {MIN_WORKERS} y {MAX_WORKERS}, recibido: {max_workers}"
        )

    parser = configparser.ConfigParser()
    parser.optionxform = str
    # Leer lo existente para preservar secciones que la GUI no edita (p.ej. [catalogs]).
    parser.read(config_path, encoding="utf-8")
    parser["service"] = {
        "host": host,
        "service_path": service_path,
        "timeout": str(timeout),
        "connect_timeout": str(connect_timeout),
        "verify_ssl": "true" if verify_ssl else "false",
        "default_report": default_report,
    }
    parser["reports"] = {key: value for key, value in reports.items()}
    parser["batch"] = {"max_workers": str(max_workers)}
    parser["output"] = {"output_dir": str(output_dir)}
    parser["logging"] = {"log_dir": str(log_dir), "log_level": log_level}

    with open(config_path, "w", encoding="utf-8") as fh:
        parser.write(fh)

    # Credenciales solo si se proporcionan (no se muestran/tocan si vienen None).
    env_file = Path(env_path)
    if not env_file.exists():
        env_file.touch()
    if user is not None:
        set_key(str(env_file), "CERT_USER", user)
    if password is not None:
        set_key(str(env_file), "CERT_PASSWORD", password)
