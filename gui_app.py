"""Lanzador de la interfaz grafica.

    python gui_app.py        (modo desarrollo)
    CertificadosCalidad.exe  (compilado con PyInstaller)

Toda la logica de negocio vive en el paquete ``certificados`` (nucleo). Esta GUI
solo lo consume; para ejecucion por consola usa ``main.py``.
"""
import os
import sys
from pathlib import Path


def _bootstrap_frozen() -> None:
    """Al correr como .exe: trabajar en la carpeta del exe (config/plantillas/logs
    editables junto a el) y ubicar el Chromium empaquetado para el motor local."""
    if not getattr(sys, "frozen", False):
        return
    base = Path(sys.executable).resolve().parent
    os.chdir(base)
    # Chromium bundleado en <carpeta_exe>/ms-playwright (si se distribuye el motor local).
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(base / "ms-playwright"))


_bootstrap_frozen()


def _selftest() -> int:
    """Verifica que el bundle carga (imports + version) sin abrir ventana.
    Escribe el resultado en selftest.txt y en stdout. Uso: exe --selftest"""
    try:
        import certificados
        import gui.app  # noqa: F401  (importa tkinter, jinja2, etc.)
        msg = f"SELFTEST OK v{certificados.__version__}"
        code = 0
    except Exception as exc:  # pragma: no cover
        import traceback
        msg = "SELFTEST FAIL:\n" + traceback.format_exc()
        code = 2
    try:
        from pathlib import Path
        Path("selftest.txt").write_text(msg, encoding="utf-8")
    except Exception:
        pass
    print(msg)
    return code


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    from gui.app import launch
    launch()
