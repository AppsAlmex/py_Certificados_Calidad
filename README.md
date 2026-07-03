# Certificados de Calidad — Ejecución masiva de reportes

Ejecuta múltiples reportes de Oracle BI Publisher (ReportService v2) a partir de un
archivo CSV. Diseñado con principios **SOLID**: cada responsabilidad vive en su
propio componente y el núcleo depende de abstracciones, no de implementaciones.

---

## 1. Arquitectura

Dos capas separadas: la **presentación** (CLI o GUI) solo consume el **núcleo**
de negocio; el núcleo no sabe nada de la interfaz.

```
  Presentación                         Núcleo de negocio (certificados/)
  ------------                         ---------------------------------
  main.py     (CLI)  ─┐
                      ├─►  CSVReader ─► Validator ─► ReportRequest ─► ReportGateway ─► ResultLogger
  gui_app.py  (GUI)  ─┘                                              (OracleReportClient → SOAP)
  gui/ (controller+app)          todo orquestado por BatchProcessor / ConcurrentBatchProcessor
```

- **Núcleo** (`certificados/`) — lógica de negocio, sin dependencias de UI.
- **CLI** (`main.py`) — ejecución por consola.
- **GUI** (`gui/`) — Tkinter; `controller.py` media contra el núcleo (en un hilo)
  y `app.py` son solo widgets. Borrar `gui/` no afecta al núcleo ni a la CLI.

| Componente | Archivo | Responsabilidad (SRP) |
|------------|---------|-----------------------|
| `Settings` / `load_settings` | `certificados/config.py` | Cargar configuración externa (config.ini + .env). **DIP** |
| `ReportRequest` / `ReportResult` / `BatchSummary` | `certificados/models.py` | Modelo de datos, sin I/O |
| `CSVReader` | `certificados/csv_reader.py` | Leer CSV → lista de `ReportRequest`. **SRP** |
| `RequestValidator` + `ValidationRule`s | `certificados/validators.py` | Validar solicitudes. **SRP + OCP** |
| `ReportGateway` (abstracción) | `certificados/executor.py` | Contrato de ejecución. **ISP + DIP** |
| `OracleReportClient` | `certificados/executor.py` | Implementación SOAP concreta. **LSP** |
| `ResultLogger` | `certificados/result_logger.py` | Trazabilidad (log + CSV de resultados) |
| `BatchProcessor` | `certificados/batch.py` | Orquestar todo, tolerante a fallos |
| Excepciones | `certificados/exceptions.py` | Jerarquía de errores controlados |

### Principios SOLID aplicados

- **S**RP — Un componente = una razón para cambiar (leer, validar, ejecutar, registrar).
- **O**CP — Nuevas validaciones = nueva clase `ValidationRule` (no se toca el validador).
- **L**SP — Cualquier `ReportGateway` sustituye a otro sin romper `BatchProcessor`.
- **I**SP — Los consumidores dependen solo de `ReportGateway.run_report`.
- **D**IP — El núcleo depende de `Settings` y `ReportGateway` (abstracciones), y la
  sesión HTTP se **inyecta**, lo que permite probar sin red.

---

## 2. Flujo de procesamiento

1. `main.py` carga `Settings` desde `config.ini` + `.env`.
2. `CSVReader` lee el archivo y produce una lista de `ReportRequest`.
3. Por cada solicitud, `BatchProcessor`:
   - valida con `RequestValidator`; si es inválida se registra y **se continúa**;
   - ejecuta con `OracleReportClient` (SOAP → base64 → archivo);
   - captura cualquier error individual, lo registra y **continúa** con la siguiente.
4. `ResultLogger` escribe `logs/ejecucion_*.log` y `logs/resultados_*.csv`.
5. Se imprime un `BatchSummary` (total / ok / inválidos / fallidos).

---

## 3. Formato del CSV

Plantilla: `templates/solicitudes_template.csv`. Delimitador `,`, codificación UTF-8.

| Columna | Parámetro | Tipo | Obligatorio |
|---------|-----------|------|-------------|
| `embarque` | P_EMBARQUE | texto | **Sí** |
| `formato` | P_FORMATO | texto | **Sí** |
| `inspector` | P_INSPECTOR | texto | **Sí** |
| `observaciones` | P_OBSERVACIONES | texto | No |
| `planta_prod` | P_PLANTA_PROD | texto | **Sí** |
| `tanque` | P_TANQUE | texto | **Sí** |
| `sello1..4` | P_SELLO1..4 | texto | No |
| `cantidad1..4` | P_CANTIDAD1..4 | entero | No (si viene, numérico) |
| `formato_salida` | attributeFormat | `pdf`\|`xml`\|`xlsx` | No (default `pdf`) |
| `nombre_archivo` | — | texto | No (se deriva del embarque) |

Notas:
- Un **valor** vacío en columna opcional es válido; una **columna** ausente es error.
- Valores con comas (ej. `"MARSHALL, MN"`) van entre comillas dobles.

Ejemplo:

```csv
embarque,formato,inspector,observaciones,planta_prod,tanque,sello1,cantidad1,sello2,cantidad2,sello3,cantidad3,sello4,cantidad4,formato_salida,nombre_archivo
256436,1,003,,"MARSHALL, MN",ADMX0106215_221209,951,2,,,,,,,pdf,
```

---

## 4. Instalación y ejecución

```powershell
# dependencias
pip install -r requirements.txt

# credenciales (una sola vez)
copy .env.example .env      # editar CERT_USER / CERT_PASSWORD

# carga masiva
python main.py --csv templates/solicitudes_template.csv

# un solo reporte (ejemplo de reutilización del núcleo)
python getReport.py

# interfaz gráfica (selector de CSV + Settings + workers)
python gui_app.py
```

### GUI

`python gui_app.py` abre una ventana con tres pestañas:

- **Ejecución (CSV)** (configuración *al momento*): selector de archivo CSV,
  reporte a consumir (del catálogo), número de workers, botón **Ejecutar** y
  botón **Detener**. Muestra el log en vivo y un resumen al terminar. El proceso
  corre en un hilo: la ventana no se congela aunque el reporte tarde.
- **Certificado individual**: formulario con los mismos campos del CSV. "Agregar
  a la cola" mete cada certificado a la lista **Certificados en proceso** (con su
  estado: En cola → Procesando → OK/ERROR/INVALIDO). Tiene **paridad con el batch**:
  en "Opciones de envío" se elige el **reporte** y los **workers**; la única
  diferencia con la ejecución por CSV es el origen de los datos (capturar vs
  archivo). "Procesar cola" los ejecuta (concurrente si workers > 1); "Detener",
  "Quitar seleccionado" y "Limpiar completados" gestionan la lista.
  - **Cantidad 1‑4** → combos de 1 a 10.
  - **Formato, Inspector, Planta** → combos "valor - descripción" alimentados por
    CSVs en `catalogos/` (columnas `valor,descripcion`). Edita esos CSV para
    personalizar las opciones; la ruta se configura en `[catalogs]` de
    `config.ini`. Son editables: si un valor no está en la lista, se puede
    escribir. Se guarda solo el `valor` en el parámetro del reporte.
- **Logs**: lista de ejecuciones previas (más recientes primero) con conteos
  Total/OK/Error/Inválido. Al seleccionar una, el panel inferior muestra el
  **detalle por fila** (estado con color, formato, duración, archivo, mensaje) en
  la sub‑pestaña "Resultados" y el **log de texto completo** en "Log completo".
  Botón "Refrescar"; se actualiza sola al terminar una ejecución.
- **Settings** (configuración *interna*, persistente): host, service path,
  timeouts, verify_ssl, carpetas, nivel de log, credenciales, catálogo de
  reportes y workers por defecto. "Guardar configuración" escribe `config.ini`
  y `.env` (vía el núcleo, no la GUI).

**Detener (cancelación cooperativa):** para nuevas peticiones y no lanza más; la
petición **en curso termina** (un único reporte de 70 min no se aborta a la
fuerza — Python no puede matar el request bloqueante sin riesgo). El resumen
final marca `(cancelado)`.

Los PDF/XLSX se guardan en `output/`; la trazabilidad en `logs/`.

---

## 5. Configuración externa (sin secretos en el código)

- `config.ini`
  - `[service]` — host, endpoint, timeout, verify_ssl, `default_report`.
  - `[reports]` — **catálogo** de reportes `clave = ruta.xdo`. Tienes varios
    reportes iguales con distintos datos: registra cada uno aquí.
  - `[output]` / `[logging]` — carpetas y nivel de log.
- `.env` (git-ignored)
  - `CERT_USER`, `CERT_PASSWORD` — credenciales.
  - `CERT_TIMEOUT` — timeout en segundos.
  - `CERT_REPORT` — **clave** del reporte a consumir (del catálogo `[reports]`).

**Precedencia:** argumento CLI > variable de entorno (`.env`) > `config.ini`.

```powershell
# elegir reporte y timeout desde .env  → solo editas .env
CERT_REPORT=certificado_exportacion
CERT_TIMEOUT=600

# o puntualmente por CLI (gana sobre .env)
python main.py --csv datos.csv --report certificado_exportacion --timeout 600
```

Agregar un reporte nuevo: añade una línea en `[reports]` y apunta `CERT_REPORT`
a esa clave. No se toca código.

---

## 5b. Reportes largos (timeout) y concurrencia

### Timeout — reportes de hasta ~70 min

El `timeout` de `requests` **no es el tiempo total**; son dos cosas:
`(connect, read)`.

- **connect** (`CERT_CONNECT_TIMEOUT` / `connect_timeout`) — abrir la conexión. Corto (30s).
- **read** (`CERT_TIMEOUT` / `timeout`) — inactividad entre bytes. Como Oracle
  responde recién al terminar de generar, **debe cubrir toda la duración**.
  Para 70 min usa `CERT_TIMEOUT=5400` (90 min, con margen).

El sistema arma la tupla automáticamente: `Settings.request_timeout → (connect, read)`.

> ⚠️ Un load balancer / gateway / Oracle pueden cortar la conexión antes,
> sin importar el timeout del cliente. Para reportes extremadamente largos, lo
> robusto es el patrón async del servidor (`scheduleReport` + polling). Con
> timeout alto se llega lejos; solo tenlo presente.

### Concurrencia — varias peticiones en paralelo

Como cada petición pasa la mayor parte del tiempo *esperando* a Oracle (I/O-bound)
y `requests` es síncrono, se usan **hilos** (`ThreadPoolExecutor`), no `asyncio`
(evitamos reescribir el gateway y romper la integridad).

- `CERT_WORKERS` / `--workers N` / `[batch] max_workers`.
- **Límite de seguridad (código duro, no configurable):** `1 ≤ workers ≤ 100`.
  Fuera de rango → `ConfigError`. Constantes `MIN_WORKERS`/`MAX_WORKERS` en
  `certificados/config.py`; se aplica en `load_settings` y `save_config`, así que
  ningún medio (config.ini, .env, CLI, GUI) puede superarlo.
- **`1` = secuencial (comportamiento original, default).**
- `>1` → `ConcurrentBatchProcessor`: valida secuencial (barato) y ejecuta las
  filas válidas en paralelo. Mismo resultado por fila, solo más rápido.
- `ResultLogger` es thread-safe (lock en la escritura del CSV).

```powershell
# 4 reportes a la vez
python main.py --csv datos.csv --workers 4
```

No se modificó `BatchProcessor` ni el gateway (OCP/LSP): la concurrencia es una
clase nueva, opt-in.

## 6. Errores comunes

| Síntoma | Causa | Solución |
|---------|-------|----------|
| `ConfigError: Credenciales ausentes` | falta `.env` | crear `.env` con CERT_USER/PASSWORD |
| `CSVReadError: Faltan columnas` | encabezado incompleto | usar la plantilla |
| `AuthenticationError` | usuario/clave o permisos | verificar credenciales |
| `ReportConnectionError` | red / VPN / timeout | revisar conectividad, subir `timeout` |
| `ReportGenerationError: no XML` | endpoint incorrecto | revisar `host`/`service_path` |
| Fila `INVALIDO` en el log | dato inválido | corregir la fila indicada (row/columna) |

---

## 7. Cómo agregar un nuevo parámetro

1. Añadir la columna → parámetro en `PARAM_COLUMNS` (`csv_reader.py`).
2. Añadirla a la plantilla CSV.
3. (Opcional) añadir una regla en `build_default_validator()` (`validators.py`).

No se modifica ningún otro componente (OCP).

## 8. Cómo agregar un nuevo origen de datos (DB, API, cola)

Crear una clase con método `read() -> list[ReportRequest]` y pasarla a
`BatchProcessor` en lugar de `CSVReader`. El núcleo no cambia (DIP).

---

## 9. Pruebas

```powershell
pytest          # 34 pruebas, cobertura ≥ 80% (actual ~93%)
```

Cubren: lector CSV, validaciones, ejecutor (con sesión HTTP simulada), procesador
masivo (casos positivos y negativos) y registro de resultados.
