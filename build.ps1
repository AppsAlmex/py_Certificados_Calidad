# Compila Certificados de Calidad a .exe y deja los archivos editables + Chromium
# junto al ejecutable.
#
#   .\build.ps1                    # carpeta (onedir): distribuye la CARPETA completa
#   .\build.ps1 -OneFile           # un solo .exe autocontenido
#   .\build.ps1 -Chromium          # ademas empaqueta Chromium (motor local)
#   .\build.ps1 -OneFile -Chromium
#
param([switch]$Chromium, [switch]$OneFile, [switch]$Debug)

$ErrorActionPreference = "Stop"
$py = ".\.venv\Scripts\python.exe"

# Cerrar cualquier instancia abierta que bloquee dist\, y limpiar salidas previas.
Get-Process CertificadosCalidad -ErrorAction SilentlyContinue | Stop-Process -Force
if (Test-Path ".\dist")  { Remove-Item ".\dist"  -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path ".\build") { Remove-Item ".\build" -Recurse -Force -ErrorAction SilentlyContinue }

Write-Host "== Instalando PyInstaller ==" -ForegroundColor Cyan
& $py -m pip install pyinstaller -q

Write-Host "== Compilando ($(if($OneFile){'onefile'}else{'onedir'})$(if($Debug){' + consola/debug'})) ==" -ForegroundColor Cyan
if ($OneFile) { $env:BUILD_ONEFILE = "1" } else { $env:BUILD_ONEFILE = "0" }
if ($Debug)   { $env:BUILD_CONSOLE = "1" } else { $env:BUILD_CONSOLE = "0" }
& $py -m PyInstaller --noconfirm --clean CertificadosCalidad.spec

# Carpeta donde queda el exe (y donde van los archivos editables al lado).
$dist = if ($OneFile) { ".\dist" } else { ".\dist\CertificadosCalidad" }

Write-Host "== Copiando archivos editables junto al exe ($dist) ==" -ForegroundColor Cyan
Copy-Item "config.ini" $dist -Force
if (Test-Path ".env")             { Copy-Item ".env" $dist -Force }
elseif (Test-Path ".env.example") { Copy-Item ".env.example" "$dist\.env" -Force }
Copy-Item "catalogos" $dist -Recurse -Force
Copy-Item "certificados\layouts" "$dist\layouts" -Recurse -Force
New-Item -ItemType Directory -Force "$dist\output" | Out-Null
New-Item -ItemType Directory -Force "$dist\logs"   | Out-Null

if ($Chromium) {
  Write-Host "== Empaquetando Chromium (motor local) ==" -ForegroundColor Cyan
  $src = Join-Path $env:LOCALAPPDATA "ms-playwright"
  if (Test-Path $src) {
    New-Item -ItemType Directory -Force "$dist\ms-playwright" | Out-Null
    Copy-Item "$src\*" "$dist\ms-playwright" -Recurse -Force
  } else {
    Write-Warning "No se encontro $src. Corre: $py -m playwright install chromium"
  }
}

Write-Host "== Verificando salida completa ==" -ForegroundColor Cyan
$checks = @{
  "exe"        = "$dist\CertificadosCalidad.exe"
  "config.ini" = "$dist\config.ini"
  ".env"       = "$dist\.env"
  "catalogos"  = "$dist\catalogos"
  "layouts"    = "$dist\layouts\formato1.html"
}
if (-not $OneFile) { $checks["_internal"] = "$dist\_internal\python313.dll" }
if ($Chromium)     { $checks["chromium"]  = "$dist\ms-playwright" }
$ok = $true
foreach ($k in $checks.Keys) {
  $exists = Test-Path $checks[$k]
  if (-not $exists) { $ok = $false }
  Write-Host ("  {0,-12} {1}" -f $k, $(if($exists){"OK"}else{"FALTA"}))
}

Write-Host "== Listo -> $dist\CertificadosCalidad.exe ==" -ForegroundColor Green
if ($ok) {
  Write-Host "Salida completa. Zipea la carpeta: $dist" -ForegroundColor Green
} else {
  Write-Warning "Faltan archivos en la salida (ver arriba)."
}
if (-not $OneFile) {
  Write-Host "IMPORTANTE: distribuye la CARPETA completa (exe + _internal\)." -ForegroundColor Yellow
}
