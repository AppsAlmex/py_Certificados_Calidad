# Certificados de Calidad — Ejecución masiva de reportes

Ejecuta múltiples reportes de Oracle BI Publisher (ReportService v2) a partir de un
archivo CSV. Diseñado con principios **SOLID**: cada responsabilidad vive en su
propio componente y el núcleo depende de abstracciones, no de implementaciones.

---

## 1. Arquitectura

```
CSV ─► CSVReader ─► Validator ─► ReportRequest ─► ReportGateway ─► ResultLogger
                                                   (OracleReportClient → SOAP)
              todo orquestado por  BatchProcessor
```

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
```

Los PDF/XLSX se guardan en `output/`; la trazabilidad en `logs/`.

---

## 5. Configuración externa (sin secretos en el código)

- `config.ini` — host, endpoint, ruta del reporte, timeout, verify_ssl, carpetas.
- `.env` — `CERT_USER`, `CERT_PASSWORD` (git-ignored). Las variables de entorno
  tienen prioridad sobre el archivo, útil en CI/contenedores.

---

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
