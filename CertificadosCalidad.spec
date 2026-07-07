# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec para Certificados de Calidad (v1.0.0).

Genera un .exe (onedir, ventana). Empaqueta Playwright y las plantillas HTML.
La config, .env, catalogos, layouts (editable) y Chromium se colocan JUNTO al exe
mediante build.ps1 (no dentro del bundle), para que el usuario pueda editarlos.

Construir:  pyinstaller --noconfirm CertificadosCalidad.spec
"""
import os

from PyInstaller.utils.hooks import collect_all

ONEFILE = os.environ.get("BUILD_ONEFILE") == "1"  # build.ps1 -OneFile lo activa
CONSOLE = os.environ.get("BUILD_CONSOLE") == "1"  # build.ps1 -Debug (muestra errores)

datas = []
binaries = []
hiddenimports = ["lxml._elementpath"]

# Playwright trae un driver (node) y metadatos que hay que empaquetar completos.
for pkg in ("playwright",):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Plantillas empaquetadas (fallback si no se distribuye la carpeta layouts externa).
datas += [("certificados/layouts", "certificados/layouts")]


a = Analysis(
    ["gui_app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "pytest_cov"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if ONEFILE:
    # Un solo .exe autocontenido (mas facil de distribuir; arranca un poco mas lento).
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="CertificadosCalidad",
        console=CONSOLE,
        icon=None,
    )
else:
    # Modo carpeta (onedir): exe + _internal\. Distribuir la CARPETA completa.
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="CertificadosCalidad",
        console=CONSOLE,
        icon=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        name="CertificadosCalidad",
    )
