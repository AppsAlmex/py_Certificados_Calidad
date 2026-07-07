"""Resolucion de rutas segun el modo de ejecucion (script vs .exe compilado).

Cuando se corre como .exe (PyInstaller), ``sys.frozen`` es True y:
  * ``app_dir()``      -> carpeta del .exe (aqui viven config/plantillas EDITABLES).
  * ``resource_dir()`` -> recursos empaquetados dentro del bundle (solo lectura).

En modo script normal, ambas devuelven rutas del proyecto y todo sigue igual.
"""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> Path:
    """Carpeta editable por el usuario (junto al .exe, o el cwd en modo script)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def resource_dir() -> Path:
    """Carpeta de recursos empaquetados (dentro del bundle si esta compilado)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_dir()))
    return Path(__file__).resolve().parent.parent
