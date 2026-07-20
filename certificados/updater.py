"""Auto-actualizacion via GitHub Releases (repo privado).

Flujo:
  1. ``check_for_update`` consulta la ultima Release y compara su tag con la
     version local (``certificados.__version__``).
  2. Si hay una mas nueva, ``download_and_apply`` baja el ZIP adjunto, lo extrae
     a una carpeta temporal junto al .exe y lanza un ``.bat`` externo que, tras
     cerrarse la app, reemplaza los archivos y la relanza.

El token de acceso (repo privado) se resuelve, en orden:
  1. variable de entorno ``CERT_UPDATE_TOKEN`` (dev: ponla en .env),
  2. modulo bundleado ``certificados._update_token`` (lo escribe CI en build
     desde un Secret; nunca se versiona).

IMPORTANTE: un token embebido en el .exe es extraible. Usa un fine-grained PAT
limitado a ESTE repo con permiso Contents: Read-only y expiracion; rotalo.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import requests

from . import __version__

# --- Configuracion del repo -------------------------------------------------
OWNER = "AppsAlmex"
REPO = "py_Certificados_Calidad"
_API = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
_EXE_NAME = "CertificadosCalidad.exe"

# Nombre de la carpeta temporal donde se extrae la nueva version (junto al exe).
_STAGE_DIR = "_update_new"
_BAT_NAME = "_apply_update.bat"


@dataclass
class UpdateInfo:
    version: str          # tag normalizado, ej "1.2.0"
    tag: str              # tag crudo de la Release, ej "v1.2.0"
    notes: str            # release notes
    asset_url: str        # URL API del asset .zip (descarga con Accept octet-stream)
    asset_name: str
    asset_size: int


# --- Token ------------------------------------------------------------------
def _get_token() -> Optional[str]:
    tok = os.environ.get("CERT_UPDATE_TOKEN")
    if tok:
        return tok.strip()
    try:  # bundleado en build por CI (gitignored)
        from ._update_token import TOKEN  # type: ignore
        return str(TOKEN).strip()
    except Exception:
        return None


def _headers(token: Optional[str], accept: str) -> dict:
    h = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


# --- Comparacion de versiones (semver simple, sin dependencias) -------------
def _parse(v: str) -> tuple:
    """'v1.2.0' -> (1, 2, 0). Ignora sufijos no numericos por segmento."""
    nums = []
    for part in re.sub(r"^[vV]", "", v.strip()).split(".")[:4]:
        m = re.match(r"\d+", part)
        nums.append(int(m.group()) if m else 0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def is_newer(remote_tag: str, local: str = __version__) -> bool:
    return _parse(remote_tag) > _parse(local)


# --- Consulta ---------------------------------------------------------------
def check_for_update(timeout: int = 15) -> Optional[UpdateInfo]:
    """Devuelve UpdateInfo si hay version mas nueva con un asset .zip; None si no.

    Lanza requests.RequestException / RuntimeError ante problemas de red o auth,
    para que la GUI pueda mostrar el motivo cuando el chequeo fue manual.
    """
    token = _get_token()
    r = requests.get(_API, headers=_headers(token, "application/vnd.github+json"), timeout=timeout)
    if r.status_code == 401:
        raise RuntimeError("Token de actualizacion invalido o expirado (401).")
    if r.status_code == 404:
        raise RuntimeError("No hay Releases publicadas o el repo no es accesible (404).")
    r.raise_for_status()
    data = r.json()

    tag = data.get("tag_name") or ""
    if not tag or not is_newer(tag):
        return None

    asset = next((a for a in data.get("assets", []) if a.get("name", "").lower().endswith(".zip")), None)
    if not asset:
        return None

    return UpdateInfo(
        version=".".join(map(str, _parse(tag))),
        tag=tag,
        notes=data.get("body") or "",
        asset_url=asset["url"],
        asset_name=asset["name"],
        asset_size=int(asset.get("size", 0)),
    )


# --- Descarga y aplicacion --------------------------------------------------
def _app_dir() -> Path:
    """Carpeta de la app: la del .exe si esta compilada; si no, la del repo."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def download_and_apply(
    info: UpdateInfo,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    timeout: int = 60,
) -> None:
    """Descarga el ZIP, lo extrae y lanza el reemplazo externo. NO retorna:
    termina el proceso para que el .bat pueda sobrescribir los archivos.

    Solo tiene sentido cuando la app esta compilada (frozen). En dev lanza
    RuntimeError.
    """
    if not getattr(sys, "frozen", False):
        raise RuntimeError("La autoactualizacion solo aplica al .exe compilado.")

    app_dir = _app_dir()
    stage = app_dir / _STAGE_DIR

    # Descargar a archivo temporal.
    token = _get_token()
    tmp_zip = Path(tempfile.mkdtemp(prefix="certupd_")) / info.asset_name
    with requests.get(
        info.asset_url,
        headers=_headers(token, "application/octet-stream"),
        stream=True,
        timeout=timeout,
    ) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length") or info.asset_size or 0)
        done = 0
        with open(tmp_zip, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if not chunk:
                    continue
                fh.write(chunk)
                done += len(chunk)
                if progress_cb:
                    progress_cb(done, total)

    # Extraer a carpeta de staging limpia.
    if stage.exists():
        import shutil
        shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(tmp_zip) as zf:
        zf.extractall(stage)

    # Si el ZIP trae una sola carpeta raiz, usar su contenido.
    entries = [p for p in stage.iterdir()]
    if len(entries) == 1 and entries[0].is_dir():
        stage = entries[0]

    _launch_apply_bat(app_dir, stage)
    # Cerrar la app para liberar los archivos que el .bat va a sobrescribir.
    os._exit(0)


def _launch_apply_bat(app_dir: Path, stage: Path) -> None:
    """Escribe y lanza el .bat que espera el cierre de la app, copia la nueva
    version sobre la carpeta y relanza el .exe."""
    bat = app_dir / _BAT_NAME
    log = app_dir / "update.log"
    pid = os.getpid()
    exe_path = app_dir / _EXE_NAME
    stage_root = app_dir / _STAGE_DIR
    # NOTA: se usa 'ping' en vez de 'timeout' para dormir: 'timeout' aborta con
    # "Input redirection is not supported" cuando el proceso no tiene consola
    # interactiva (que es el caso al lanzarlo en segundo plano). 'ping' no la necesita.
    script = f"""@echo off
setlocal enableextensions
set "LOG={log}"
echo [%date% %time%] iniciando actualizacion a {exe_path} > "%LOG%"

rem 1) Esperar a que el proceso anterior cierre del todo (libera los archivos).
:waitloop
tasklist /fi "PID eq {pid}" /nh 2>nul | find "{pid}" >nul
if %errorlevel%==0 (
    ping -n 2 127.0.0.1 >nul
    goto waitloop
)

rem 2) Margen extra: Windows tarda un instante en soltar los locks de _internal.
ping -n 3 127.0.0.1 >nul

rem 3) Copiar la nueva version SOBRE la carpeta. /R:30 /W:1 = reintenta hasta ~30s
rem    si algun archivo sigue bloqueado. Se EXCLUYEN datos de usuario:
rem      /XF .env config.ini            -> archivos de usuario
rem      /XD catalogos logs output ms-playwright -> carpetas de usuario/datos
robocopy "{stage}" "{app_dir}" /E /MOVE /R:30 /W:1 /XF .env config.ini /XD catalogos logs output ms-playwright >> "%LOG%" 2>&1
set "RC=%errorlevel%"
echo [%date% %time%] robocopy termino con codigo %RC% (0-7 = ok) >> "%LOG%"

rem 4) Limpiar staging y relanzar la aplicacion ya actualizada.
rmdir /s /q "{stage_root}" >nul 2>&1
echo [%date% %time%] relanzando... >> "%LOG%"
start "" "{exe_path}"
del "%~f0"
"""
    bat.write_text(script, encoding="utf-8")

    # CREATE_NO_WINDOW: el .bat corre oculto pero CON consola valida (robocopy/ping
    # la necesitan). CREATE_NEW_PROCESS_GROUP + proceso separado -> sobrevive a que
    # esta app se cierre con os._exit().
    NO_WINDOW = 0x08000000   # CREATE_NO_WINDOW
    NEW_GROUP = 0x00000200   # CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        ["cmd.exe", "/c", str(bat)],
        cwd=str(app_dir),
        creationflags=NO_WINDOW | NEW_GROUP,
        close_fds=True,
    )
