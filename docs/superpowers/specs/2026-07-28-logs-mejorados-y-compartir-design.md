# Logs mejorados y "Compartir" — Diseño

Fecha: 2026-07-28
Estado: aprobado (pendiente plan de implementación)

## Objetivo

Dos capacidades sobre el sistema de logs actual:

1. **Compartir logs por correo**: el usuario selecciona una ejecución en la
   pestaña Logs, presiona "Compartir (ZIP)", elige dónde guardar y obtiene un ZIP
   con los logs de esa ejecución más datos de diagnóstico útiles para el
   desarrollador.
2. **Logs más completos**: cada ejecución guarda los datos enviados a las
   peticiones de reportes (params: inspector, sellos, cantidades, etc.), el SOAP
   request (redactado), la respuesta/fault de Oracle y el contexto de entorno, de
   modo que alguien pueda analizar el issue generado.

## Contexto actual

Cada corrida deja hoy dos archivos planos en `log_dir`:

- `resultados_<stamp>.csv` — una fila por solicitud. **Ya incluye** `parametros`
  (JSON de `request.params`), estado, formato, duración, archivo y mensaje.
- `ejecucion_<stamp>.log` — log de texto legible (no lleva params por fila).

Los escribe `certificados/result_logger.py` (`ResultLogger`, una instancia por
run, thread-safe). `certificados/logs.py` los lee y resume (`LogRun`, `list_runs`,
`read_results`, `read_log_text`). La GUI (`gui/app.py`, pestaña Logs) lista las
ejecuciones y muestra el detalle (CSV por fila + log completo).

La ejecución de reportes vive en `certificados/executor.py`
(`OracleReportClient`, `LocalPdfReportGateway`, `build_gateway`). El SOAP se
construye en `_build_soap` (incluye `<v2:userID>`/`<v2:password>`) y la respuesta
llega en `_send` / `_extract_report`.

## Decisiones tomadas

- Capturar SOAP + respuesta para **todas las filas**.
- En filas **OK** la respuesta ES el reporte completo (base64, MBs) y ya está en
  `output/`: por eso en OK solo se guarda metadata (status + tamaño + archivo), no
  el cuerpo. El cuerpo crudo se guarda solo en **ERROR/fault**.
- El SOAP lleva credenciales: se **redactan siempre** (`userID`/`password` → `***`)
  antes de persistir. Requisito de seguridad, no negociable.
- Formato de diagnóstico: un archivo **JSONL por run** (una línea JSON por fila).
- "Compartir" cubre **una sola ejecución** (la seleccionada).
- El ZIP incluye config **saneada** (sin `user`/`password`); `.env` nunca se
  incluye.
- Arquitectura de captura: **sink de diagnóstico inyectado en el gateway**
  (desacopla el ejecutor por interfaz, opt-in, testeable).

## Arquitectura

### Captura de transporte (SOAP/respuesta)

El ejecutor registra el detalle de transporte en un capturador inyectado; el
`ResultLogger` (que ya conoce estado/params/mensaje por fila) consolida y escribe
el JSONL. Así el JSONL se escribe en un solo lugar y no hay dos escritores
compitiendo por el mismo archivo.

- El ejecutor solo aporta transporte (soap redactado, status, cuerpo/metadata).
- El logger aporta estado, params, params legibles y mensaje, y une el transporte
  de esa fila.
- Filas **INVÁLIDO** nunca llegan al gateway (se validan antes) → su línea JSONL
  no tiene transporte, solo params + issues.

## Componentes

### `certificados/diagnostics.py` (nuevo)

- `redact_soap(soap: str) -> str` — reemplaza el contenido de
  `<v2:userID>...</v2:userID>` y `<v2:password>...</v2:password>` por `***`
  (tolerante a espacios/multilínea).
- `TransportCapture` (ABC): `record(fila: int, soap: str, status: int | None,
  response_body: str | None, is_report: bool, size: int | None) -> None`.
- `InMemoryTransportCapture(TransportCapture)` — guarda `{fila: TransportRecord}`
  en un dict protegido por lock; `get(fila)` para el logger.
- `NullTransportCapture(TransportCapture)` — no-op (default cuando no hay
  diagnóstico).
- `expand_params(params: dict, catalog_maps: dict) -> dict` — traduce códigos a
  descripción usando los catálogos: `P_INSPECTOR` → inspector, `P_FORMATO` →
  formato, `P_PLANTA_PROD` → planta_prod. Un valor sin match se deja como está.

`catalog_maps` es `{campo: {valor: descripcion}}` construido a partir de
`load_catalog`.

### `certificados/executor.py` (cambios)

- `OracleReportClient.__init__(self, settings, session=None, transport: TransportCapture | None = None)`.
  Default efectivo `NullTransportCapture`.
- `fetch_bytes(request)`:
  - construye SOAP y registra `redact_soap(soap)` para `request.row_number`;
  - tras `_send`, registra `status`;
  - en OK: `is_report=True`, `size=len(content)`, sin cuerpo;
  - en HTTP != 200 / SOAP fault: registra el cuerpo (fault/`response.text`) antes
    de lanzar la excepción.
  - Los puntos de captura se ajustan para poder registrar la respuesta también
    cuando `_send`/`_extract_report` van a lanzar (no perder el diagnóstico del
    error).
- `LocalPdfReportGateway` propaga `transport` a su `OracleReportClient` interno.
- `build_gateway(settings, transport: TransportCapture | None = None)`.

La captura es **best-effort**: si registrar falla, se emite warning y la
generación del reporte continúa normal.

### `certificados/result_logger.py` (cambios)

- `ResultLogger.__init__(..., transport: TransportCapture | None = None,
  param_expander: Callable[[dict], dict] | None = None)`.
- Abre `diagnostico_<stamp>.jsonl` junto al CSV y el log.
- Al iniciar, escribe `contexto_<stamp>.txt` con: versión de la app
  (`certificados.__version__`), host, ruta del reporte, timeout, motor PDF,
  workers, sistema operativo (`platform`).
- En `log_success` / `log_failure` / `log_invalid`, además de la fila CSV, escribe
  una línea JSONL con:
  ```json
  {
    "fila": 2,
    "estado": "OK|ERROR|INVALIDO",
    "reporte": "...",
    "formato": "pdf",
    "duracion_seg": 1.23,
    "archivo": "Certificado_123.pdf",
    "params": { "P_INSPECTOR": "003", ... },
    "params_legibles": { "P_INSPECTOR": "Hector Correa", ... },
    "soap_request": "<...userID>***</...>",
    "http_status": 200,
    "respuesta": null,
    "respuesta_size": 45211,
    "mensaje": ""
  }
  ```
  En ERROR: `respuesta` lleva el fault/cuerpo, `respuesta_size` nulo. En INVALIDO:
  sin campos de transporte; `mensaje` lleva los issues.
- Escritura del JSONL protegida por el mismo lock que el CSV.

### `certificados/logs.py` (cambios)

- `LogRun` gana propiedades `diagnostics_path` y `context_path`, derivadas del
  stamp (igual que `log_path`).

### `certificados/log_share.py` (nuevo)

- `build_share_zip(run: LogRun, dest_zip: str | Path, config_path: str | Path) -> Path`.
  - Junta, si existen: `ejecucion_<stamp>.log`, `resultados_<stamp>.csv`,
    `diagnostico_<stamp>.jsonl`, `contexto_<stamp>.txt` (nombres dentro del zip sin
    stamp: `ejecucion.log`, `resultados.csv`, `diagnostico.jsonl`, `contexto.txt`).
  - Genera `config_saneado.ini`: lee `config.ini` y elimina `user`/`password` de
    `[service]` si estuvieran. Nunca incluye `.env`.
  - Genera `LEEME.txt`: describe cada archivo y cómo leer el JSONL. Si faltó algún
    archivo del run, lo anota.
  - Devuelve la ruta del zip creado.

### GUI `gui/app.py` (cambios) y `gui/controller.py`

- Pestaña Logs: botón **"Compartir (ZIP)"** junto a "Refrescar". Requiere run
  seleccionado; abre `filedialog.asksaveasfilename` (nombre por defecto
  `diagnostico_<fecha>.zip`); llama `controller.build_share_zip(run, dest)`; avisa
  éxito/errores.
- Detalle: agregar vista de **parámetros legibles** por fila (ya están en el CSV;
  facilita inspección rápida sin abrir el zip).
- `BatchController`:
  - `build_share_zip(run, dest)` — delega en `log_share.build_share_zip` con
    `self.config_path`.
  - En `run_async` y `process_requests_async`: crea `InMemoryTransportCapture`,
    construye `catalog_maps` (desde `read_catalogs`), arma el `param_expander`, e
    inyecta el capturador en `build_gateway(...)` y en `ResultLogger(...)`.

## Flujo de datos

1. Inicio del run: se crea `InMemoryTransportCapture`; `ResultLogger` abre
   csv/log/jsonl y escribe `contexto.txt`; `build_gateway` recibe el capturador.
2. Por fila: el gateway ejecuta el reporte y registra transporte en el capturador
   (soap redactado, status, cuerpo/metadata). El logger registra el resultado
   (CSV) y escribe la línea JSONL uniendo su estado/params/params_legibles con el
   transporte capturado de esa fila.
3. Compartir: el usuario elige un run y destino; `build_share_zip` empaqueta los
   archivos del run + config saneada + LEEME.

## Manejo de errores

- Diagnóstico best-effort: fallos al capturar/escribir jsonl → warning, no rompen
  la ejecución.
- Compartir con archivos faltantes: el zip incluye lo que exista y lo nota en
  LEEME.
- Seguridad: `redact_soap` y la config saneada garantizan que `user`/`password`
  nunca salgan en el zip (cubierto por tests).

## Testing

- `redact_soap` oculta `userID`/`password` (incluye caso multilínea/espacios).
- `expand_params` traduce con catálogos; valor sin match queda como el código.
- `InMemoryTransportCapture` thread-safe (registro concurrente desde varios hilos).
- `ResultLogger` escribe JSONL con estructura correcta por estado: OK sin cuerpo
  (con size), ERROR con fault, INVALIDO sin transporte.
- `build_share_zip` produce un zip con los miembros esperados y **sin**
  credenciales (ni en `config_saneado.ini` ni en `soap_request`).

## Fuera de alcance (YAGNI)

- Compartir múltiples ejecuciones en un solo zip.
- Modo "diagnóstico configurable" (se captura todo siempre, por decisión del
  usuario).
- Guardar el cuerpo crudo completo de respuestas OK.
- Envío automático por correo (el usuario adjunta el zip manualmente).
