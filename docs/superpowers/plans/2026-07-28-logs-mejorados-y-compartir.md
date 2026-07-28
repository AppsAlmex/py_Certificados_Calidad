# Logs mejorados y "Compartir" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capturar diagnóstico completo por ejecución (SOAP redactado, respuesta/fault, contexto, params legibles) en un JSONL, y agregar un botón "Compartir (ZIP)" que empaqueta los logs de un run + config saneada para enviar por correo.

**Architecture:** Un capturador de transporte (`TransportCapture`) se inyecta en el gateway Oracle; el ejecutor registra SOAP/respuesta por fila. El `ResultLogger` consolida ese transporte con estado/params y escribe un `diagnostico_<stamp>.jsonl`. Un módulo `log_share` arma el ZIP a pedido de la GUI. Todo opt-in y best-effort: si el diagnóstico falla, la generación del reporte no se rompe.

**Tech Stack:** Python 3.13, stdlib (`zipfile`, `json`, `csv`, `configparser`, `re`, `threading`, `platform`), `requests`, `lxml`, Tkinter, pytest.

## Global Constraints

- Credenciales NUNCA salen en artefactos compartidos: `redact_soap` oculta `userID`/`password`; `config_saneado.ini` no lleva `user`/`password`; `.env` nunca se incluye.
- Diagnóstico best-effort: fallos de captura/escritura emiten warning, no interrumpen el reporte.
- Codificación de archivos de texto: UTF-8.
- En filas OK NO se guarda el cuerpo de respuesta (es el reporte, MBs): solo `http_status` + `respuesta_size`.
- Seguir patrones existentes: capas GUI→controller→core; una responsabilidad por archivo; tests con pytest y fixtures de `tests/conftest.py`.
- Comando de tests: `.venv/Scripts/python.exe -m pytest`. El repo exige cobertura global ≥80% (correr la suite completa al validar, no un solo archivo).

---

## File Structure

- Create: `certificados/diagnostics.py` — redacción, captura de transporte, expansión de params.
- Create: `certificados/log_share.py` — armado del ZIP para compartir.
- Create: `tests/test_diagnostics.py`, `tests/test_log_share.py`.
- Modify: `certificados/executor.py` — inyección de `TransportCapture` y captura por fila.
- Modify: `certificados/result_logger.py` — escritura del JSONL + `contexto.txt`.
- Modify: `certificados/logs.py` — `LogRun.diagnostics_path` / `context_path`.
- Modify: `certificados/__init__.py` — exportar símbolos nuevos.
- Modify: `gui/controller.py` — wiring del capturador/expander y `build_share_zip`.
- Modify: `gui/app.py` — botón "Compartir (ZIP)" + vista de params legibles.
- Modify: `tests/test_executor.py`, `tests/test_result_logger.py`, `tests/test_gui_controller.py` — cubrir lo nuevo y ajustar el monkeypatch de `build_gateway`.

---

### Task 1: Núcleo de diagnóstico (`certificados/diagnostics.py`)

**Files:**
- Create: `certificados/diagnostics.py`
- Test: `tests/test_diagnostics.py`
- Modify: `certificados/__init__.py`

**Interfaces:**
- Produces:
  - `redact_soap(soap: str) -> str`
  - `class TransportRecord` con campos `soap: str`, `status: int|None`, `response_body: str|None`, `is_report: bool`, `size: int|None`
  - `class TransportCapture(ABC)` con `record(fila:int, soap:str, status=None, response_body=None, is_report=False, size=None) -> None` y `get(fila:int) -> TransportRecord|None`
  - `class NullTransportCapture(TransportCapture)`
  - `class InMemoryTransportCapture(TransportCapture)`
  - `expand_params(params: dict, catalog_maps: dict) -> dict`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_diagnostics.py`:

```python
import threading

from certificados.diagnostics import (
    InMemoryTransportCapture,
    NullTransportCapture,
    expand_params,
    redact_soap,
)

SOAP = (
    "<v2:runReport><v2:userID>admin</v2:userID>"
    "<v2:password>s3cr3t</v2:password></v2:runReport>"
)


def test_redact_soap_oculta_credenciales():
    out = redact_soap(SOAP)
    assert "admin" not in out
    assert "s3cr3t" not in out
    assert "<v2:userID>***</v2:userID>" in out
    assert "<v2:password>***</v2:password>" in out


def test_redact_soap_multilinea_y_sin_prefijo():
    soap = "<userID>\n  admin\n</userID><password>p</password>"
    out = redact_soap(soap)
    assert "admin" not in out
    assert "<userID>***</userID>" in out
    assert "<password>***</password>" in out


def test_null_capture_no_guarda_nada():
    cap = NullTransportCapture()
    cap.record(2, soap="x", status=200)
    assert cap.get(2) is None


def test_inmemory_capture_guarda_y_recupera():
    cap = InMemoryTransportCapture()
    cap.record(2, soap="redacted", status=200, is_report=True, size=10)
    rec = cap.get(2)
    assert rec.status == 200
    assert rec.is_report is True
    assert rec.size == 10
    assert cap.get(99) is None


def test_inmemory_capture_thread_safe():
    cap = InMemoryTransportCapture()

    def worker(n):
        cap.record(n, soap=f"s{n}", status=200)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(cap.get(i).soap == f"s{i}" for i in range(50))


def test_expand_params_traduce_con_catalogos():
    maps = {
        "inspector": {"003": "Hector Correa"},
        "formato": {"1": "Estandar"},
    }
    out = expand_params({"P_INSPECTOR": "003", "P_FORMATO": "1"}, maps)
    assert out["P_INSPECTOR"] == "003 - Hector Correa"
    assert out["P_FORMATO"] == "1 - Estandar"


def test_expand_params_sin_match_deja_codigo():
    out = expand_params({"P_INSPECTOR": "999", "P_SELLO1": "951"}, {"inspector": {}})
    assert out["P_INSPECTOR"] == "999"
    assert out["P_SELLO1"] == "951"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_diagnostics.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'certificados.diagnostics'`.

- [ ] **Step 3: Write the implementation**

Create `certificados/diagnostics.py`:

```python
"""Diagnóstico de ejecuciones: redacción de credenciales, captura de transporte
(SOAP/respuesta por fila) y expansión legible de parámetros.

Separado del ejecutor y del logger para poder testear cada pieza aislada. La
captura se inyecta en el gateway (Dependency Inversion); el logger la consume.
"""
from __future__ import annotations

import re
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional

# Etiquetas del SOAP que llevan secretos (con o sin prefijo de namespace).
_CRED_TAGS = ("userID", "password")


def redact_soap(soap: str) -> str:
    """Devuelve el SOAP con el contenido de userID/password reemplazado por ***."""
    out = soap
    for tag in _CRED_TAGS:
        out = re.sub(
            rf"(<(?:\w+:)?{tag}>)(.*?)(</(?:\w+:)?{tag}>)",
            r"\1***\3",
            out,
            flags=re.DOTALL,
        )
    return out


@dataclass
class TransportRecord:
    """Detalle de transporte capturado para una fila."""

    soap: str = ""
    status: Optional[int] = None
    response_body: Optional[str] = None
    is_report: bool = False
    size: Optional[int] = None


class TransportCapture(ABC):
    """Abstracción que el ejecutor llena y el logger consume."""

    @abstractmethod
    def record(self, fila: int, soap: str, status: Optional[int] = None,
               response_body: Optional[str] = None, is_report: bool = False,
               size: Optional[int] = None) -> None:
        ...

    @abstractmethod
    def get(self, fila: int) -> Optional[TransportRecord]:
        ...


class NullTransportCapture(TransportCapture):
    """No-op: se usa cuando no hay diagnóstico activo."""

    def record(self, fila: int, soap: str, status=None, response_body=None,
               is_report=False, size=None) -> None:
        return None

    def get(self, fila: int) -> Optional[TransportRecord]:
        return None


class InMemoryTransportCapture(TransportCapture):
    """Guarda el transporte por fila en memoria (thread-safe para el pool)."""

    def __init__(self) -> None:
        self._data: Dict[int, TransportRecord] = {}
        self._lock = threading.Lock()

    def record(self, fila: int, soap: str, status=None, response_body=None,
               is_report=False, size=None) -> None:
        with self._lock:
            self._data[int(fila)] = TransportRecord(
                soap=soap, status=status, response_body=response_body,
                is_report=is_report, size=size,
            )

    def get(self, fila: int) -> Optional[TransportRecord]:
        with self._lock:
            return self._data.get(int(fila))


# Parámetro Oracle -> campo de catálogo (para traducir código a descripción).
_PARAM_TO_CATALOG = {
    "P_INSPECTOR": "inspector",
    "P_FORMATO": "formato",
    "P_PLANTA_PROD": "planta_prod",
}


def expand_params(params: dict, catalog_maps: dict) -> dict:
    """Traduce códigos a 'codigo - descripcion' usando los catálogos.

    ``catalog_maps`` es ``{campo: {valor: descripcion}}``. Un valor sin match (o un
    parámetro sin catálogo) se deja tal cual.
    """
    out: Dict[str, str] = {}
    for key, value in params.items():
        field = _PARAM_TO_CATALOG.get(key)
        desc = ""
        if field and value:
            desc = (catalog_maps.get(field) or {}).get(value, "")
        out[key] = f"{value} - {desc}" if desc else value
    return out
```

- [ ] **Step 4: Export the new symbols**

In `certificados/__init__.py`, after the `from .executor import ...` line (currently line 37), add:

```python
from .diagnostics import (
    InMemoryTransportCapture,
    NullTransportCapture,
    TransportCapture,
    TransportRecord,
    expand_params,
    redact_soap,
)
```

And add these names to the `__all__` list:

```python
    "TransportCapture",
    "TransportRecord",
    "NullTransportCapture",
    "InMemoryTransportCapture",
    "expand_params",
    "redact_soap",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_diagnostics.py -q`
Expected: PASS (7 passed).

- [ ] **Step 6: Commit**

```bash
git add certificados/diagnostics.py certificados/__init__.py tests/test_diagnostics.py
git commit -m "feat: nucleo de diagnostico (redact_soap, TransportCapture, expand_params)"
```

---

### Task 2: Captura de transporte en el ejecutor (`certificados/executor.py`)

**Files:**
- Modify: `certificados/executor.py`
- Test: `tests/test_executor.py`

**Interfaces:**
- Consumes: `TransportCapture`, `NullTransportCapture`, `redact_soap` (Task 1).
- Produces:
  - `OracleReportClient(settings, session=None, transport: TransportCapture|None = None)`
  - `LocalPdfReportGateway(settings, oracle_client=None, renderer=None, transport: TransportCapture|None = None)`
  - `build_gateway(settings, transport: TransportCapture|None = None) -> ReportGateway`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_executor.py` (usa `FakeSession`, `FakeResponse`, `soap_response` ya presentes):

```python
from certificados.diagnostics import InMemoryTransportCapture


def test_transport_capturado_en_ok(settings, valid_request):
    session = FakeSession(FakeResponse(content=soap_response(b"%PDF fake")))
    cap = InMemoryTransportCapture()
    OracleReportClient(settings, session=session, transport=cap).run_report(valid_request)
    rec = cap.get(valid_request.row_number)
    assert rec is not None
    assert rec.status == 200
    assert rec.is_report is True
    assert rec.size == len(b"%PDF fake")
    assert rec.response_body is None
    # SOAP redactado: la password real no aparece.
    assert "pass" not in rec.soap
    assert "<v2:password>***</v2:password>" in rec.soap


def test_transport_capturado_en_error_http(settings, valid_request):
    session = FakeSession(FakeResponse(status_code=500, text="boom interno"))
    cap = InMemoryTransportCapture()
    with pytest.raises(ReportGenerationError):
        OracleReportClient(settings, session=session, transport=cap).run_report(valid_request)
    rec = cap.get(valid_request.row_number)
    assert rec is not None
    assert rec.is_report is False
    assert "500" in (rec.response_body or "")
    assert "<v2:password>***</v2:password>" in rec.soap
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_executor.py -k transport -q`
Expected: FAIL (`OracleReportClient` no acepta `transport`).

- [ ] **Step 3: Implement capture in the client**

In `certificados/executor.py`:

Add import near the top (after the existing `from .models import ...`):

```python
from .diagnostics import NullTransportCapture, TransportCapture, redact_soap
```

Change `OracleReportClient.__init__` to accept and store the capture:

```python
    def __init__(self, settings: Settings, session: requests.Session | None = None,
                 transport: TransportCapture | None = None):
        self._settings = settings
        # Session injected for testability (Dependency Inversion).
        self._session = session or requests.Session()
        # Capturador de diagnóstico (SOAP/respuesta por fila). Null = sin captura.
        self._transport = transport or NullTransportCapture()
        if not settings.verify_ssl:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

Replace `fetch_bytes` with a version que captura en cada salida:

```python
    def fetch_bytes(self, request: ReportRequest) -> bytes:
        """Descarga y decodifica el reporte SIN guardarlo, registrando el
        transporte (SOAP redactado + resultado) por fila para diagnóstico."""
        fila = request.row_number
        soap = self._build_soap(request)
        redacted = redact_soap(soap)
        try:
            response = self._send(soap)
        except CertificadoError as exc:
            # HTTP != 200 / red: el cuerpo/motivo viaja en el mensaje de la excepción.
            self._safe_record(fila, redacted, status=None, body=str(exc),
                               is_report=False, size=None)
            raise
        try:
            content = self._extract_report(response)
        except CertificadoError as exc:
            self._safe_record(fila, redacted, status=response.status_code, body=str(exc),
                              is_report=False, size=None)
            raise
        self._safe_record(fila, redacted, status=response.status_code, body=None,
                          is_report=True, size=len(content))
        return content

    def _safe_record(self, fila, soap, status, body, is_report, size) -> None:
        """Registra transporte sin romper la ejecución si el capturador falla."""
        try:
            self._transport.record(fila, soap=soap, status=status, response_body=body,
                                    is_report=is_report, size=size)
        except Exception:  # best-effort: el diagnóstico nunca tumba el reporte
            pass
```

Add the `CertificadoError` import to the existing `from .exceptions import (...)` block (add the name to the tuple):

```python
from .exceptions import (
    AuthenticationError,
    CertificadoError,
    FileSaveError,
    ReportConnectionError,
    ReportGenerationError,
)
```

Propagate `transport` through `LocalPdfReportGateway.__init__`:

```python
    def __init__(self, settings: Settings, oracle_client: "OracleReportClient | None" = None,
                 renderer=None, transport: TransportCapture | None = None):
        self._settings = settings
        self._oracle = oracle_client or OracleReportClient(settings, transport=transport)
        self._renderer = renderer
```

Update `build_gateway`:

```python
def build_gateway(settings: Settings, transport: TransportCapture | None = None) -> ReportGateway:
    """Elige el gateway segun el motor de PDF configurado (oracle | local)."""
    if getattr(settings, "pdf_engine", "oracle").lower() == "local":
        return LocalPdfReportGateway(settings, transport=transport)
    return OracleReportClient(settings, transport=transport)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_executor.py -q`
Expected: PASS (todos, incluidos los dos nuevos).

- [ ] **Step 5: Commit**

```bash
git add certificados/executor.py tests/test_executor.py
git commit -m "feat: capturar SOAP redactado y respuesta por fila en el ejecutor"
```

---

### Task 3: JSONL + contexto en `ResultLogger` (`certificados/result_logger.py`)

**Files:**
- Modify: `certificados/result_logger.py`
- Test: `tests/test_result_logger.py`

**Interfaces:**
- Consumes: `TransportCapture` (Task 1).
- Produces:
  - `ResultLogger(log_dir, level="INFO", extra_handlers=None, context=None, transport: TransportCapture|None = None, param_expander: Callable[[dict], dict]|None = None)`
  - Escribe `diagnostico_<stamp>.jsonl` (una línea por fila) y `contexto_<stamp>.txt`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_result_logger.py`:

```python
import json

from certificados.diagnostics import InMemoryTransportCapture
from certificados.models import ReportRequest, ReportResult
from certificados.result_logger import ResultLogger


def _req(fila=2):
    return ReportRequest(row_number=fila, params={"P_INSPECTOR": "003"}, output_format="pdf")


def test_jsonl_ok_lleva_transporte_y_params_legibles(tmp_path):
    cap = InMemoryTransportCapture()
    cap.record(2, soap="<v2:password>***</v2:password>", status=200, is_report=True, size=123)
    expander = lambda params: {"P_INSPECTOR": "003 - Hector Correa"}
    with ResultLogger(tmp_path, transport=cap, param_expander=expander,
                      context={"reporte": "R"}) as logger:
        req = _req()
        result = ReportResult(request=req, file_path=tmp_path / "c.pdf", size_bytes=123)
        logger.log_success(result, 1.5)
        jsonl_path = logger.diagnostics_path
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    assert entry["estado"] == "OK"
    assert entry["http_status"] == 200
    assert entry["respuesta"] is None
    assert entry["respuesta_size"] == 123
    assert entry["params_legibles"]["P_INSPECTOR"] == "003 - Hector Correa"
    assert entry["soap_request"] == "<v2:password>***</v2:password>"


def test_jsonl_error_lleva_cuerpo(tmp_path):
    cap = InMemoryTransportCapture()
    cap.record(2, soap="s", status=None, response_body="Respuesta HTTP 500: boom",
               is_report=False, size=None)
    with ResultLogger(tmp_path, transport=cap) as logger:
        logger.log_failure(_req(), RuntimeError("boom"), 0.4)
        jsonl_path = logger.diagnostics_path
    entry = json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["estado"] == "ERROR"
    assert "500" in entry["respuesta"]
    assert entry["respuesta_size"] is None


def test_jsonl_invalido_sin_transporte(tmp_path):
    with ResultLogger(tmp_path) as logger:  # sin capturador
        logger.log_invalid(_req(), ["campo X requerido"], 0.0)
        jsonl_path = logger.diagnostics_path
    entry = json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["estado"] == "INVALIDO"
    assert entry["soap_request"] is None
    assert "campo X requerido" in entry["mensaje"]


def test_contexto_txt_se_escribe(tmp_path):
    with ResultLogger(tmp_path, context={"reporte": "R", "workers": 4}) as logger:
        ctx_path = logger.context_path
    text = ctx_path.read_text(encoding="utf-8")
    assert "reporte: R" in text
    assert "workers: 4" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_result_logger.py -k "jsonl or contexto" -q`
Expected: FAIL (`ResultLogger` no acepta `transport`/`param_expander`, no tiene `diagnostics_path`).

- [ ] **Step 3: Implement JSONL + contexto**

In `certificados/result_logger.py`:

Add to imports at top:

```python
from typing import Callable, Iterable
```
(añade `Callable` a la línea `from typing import Iterable`).

Extend `__init__` signature and body. Change the signature line and, right after opening the CSV writer, open the JSONL file and write the context file. Concretely:

Replace the signature:

```python
    def __init__(self, log_dir: str | Path, level: str = "INFO", extra_handlers=None,
                 context=None, transport=None, param_expander: Callable[[dict], dict] | None = None):
```

After the existing block that creates `self.results_path` / `self._writer` (right after `self._writer.writerow(_CSV_HEADER)`), add:

```python
        # Diagnóstico: capturador de transporte + expansor de params legibles.
        from .diagnostics import NullTransportCapture
        self._transport = transport or NullTransportCapture()
        self._param_expander = param_expander
        self.diagnostics_path = self.log_dir / f"diagnostico_{stamp}.jsonl"
        self._jsonl_file = self.diagnostics_path.open("w", encoding="utf-8")
        self.context_path = self.log_dir / f"contexto_{stamp}.txt"
```

At the end of `__init__`, after the `if self._context:` logging block, write the context file:

```python
        # Contexto de la corrida en texto plano (para el zip de diagnóstico).
        try:
            lines = [f"{k}: {v}" for k, v in self._context.items()]
            self.context_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError:
            pass
```

Add a `_jsonl` helper and call it from each log event. Add this method (después de `_row`):

```python
    def _jsonl(self, request: ReportRequest, estado: str, duration: float,
               archivo: str, mensaje: str) -> None:
        """Escribe una línea JSON consolidando estado/params con el transporte."""
        try:
            rec = self._transport.get(request.row_number)
            params = dict(request.params)
            legibles = self._param_expander(params) if self._param_expander else {}
            entry = {
                "fila": request.row_number,
                "estado": estado,
                "reporte": self._context.get("reporte", ""),
                "formato": request.output_format,
                "duracion_seg": round(duration, 2),
                "archivo": archivo,
                "params": params,
                "params_legibles": legibles,
                "soap_request": rec.soap if rec else None,
                "http_status": rec.status if rec else None,
                "respuesta": rec.response_body if rec else None,
                "respuesta_size": rec.size if rec else None,
                "mensaje": mensaje,
            }
            with self._lock:
                self._jsonl_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
                self._jsonl_file.flush()
        except Exception:  # best-effort: el diagnóstico nunca tumba el logging
            pass
```

Call `_jsonl` from the three event methods. In `log_success` add at the end:

```python
        self._jsonl(req, "OK", duration, str(result.file_path.name), "")
```

In `log_failure` add at the end:

```python
        self._jsonl(request, "ERROR", duration, "", str(error))
```

In `log_invalid`, after building `message`, add at the end:

```python
        self._jsonl(request, "INVALIDO", duration, "", message)
```

Close the JSONL file in `close()`. In `close`, before removing handlers, add:

```python
        if hasattr(self, "_jsonl_file") and not self._jsonl_file.closed:
            self._jsonl_file.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_result_logger.py -q`
Expected: PASS (nuevos + existentes).

- [ ] **Step 5: Commit**

```bash
git add certificados/result_logger.py tests/test_result_logger.py
git commit -m "feat: ResultLogger escribe diagnostico JSONL y contexto por ejecucion"
```

---

### Task 4: Rutas de diagnóstico en `LogRun` (`certificados/logs.py`)

**Files:**
- Modify: `certificados/logs.py`
- Test: `tests/test_logs.py`

**Interfaces:**
- Produces: `LogRun.diagnostics_path -> Path`, `LogRun.context_path -> Path`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_logs.py`:

```python
from pathlib import Path

from certificados.logs import LogRun


def test_logrun_deriva_rutas_diagnostico():
    run = LogRun(results_path=Path("logs/resultados_20260101_101010.csv"), fecha="x")
    assert run.log_path.name == "ejecucion_20260101_101010.log"
    assert run.diagnostics_path.name == "diagnostico_20260101_101010.jsonl"
    assert run.context_path.name == "contexto_20260101_101010.txt"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_logs.py -k diagnostico -q`
Expected: FAIL (`LogRun` no tiene `diagnostics_path`).

- [ ] **Step 3: Implement the properties**

In `certificados/logs.py`, after the existing `log_path` property of `LogRun`, add:

```python
    @property
    def diagnostics_path(self) -> Path:
        stamp = self.results_path.stem[len(RESULT_PREFIX):]
        return self.results_path.parent / f"diagnostico_{stamp}.jsonl"

    @property
    def context_path(self) -> Path:
        stamp = self.results_path.stem[len(RESULT_PREFIX):]
        return self.results_path.parent / f"contexto_{stamp}.txt"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_logs.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add certificados/logs.py tests/test_logs.py
git commit -m "feat: LogRun expone rutas de diagnostico y contexto"
```

---

### Task 5: Armado del ZIP para compartir (`certificados/log_share.py`)

**Files:**
- Create: `certificados/log_share.py`
- Test: `tests/test_log_share.py`
- Modify: `certificados/__init__.py`

**Interfaces:**
- Consumes: `LogRun` (Task 4).
- Produces: `build_share_zip(run: LogRun, dest_zip: str|Path, config_path: str|Path) -> Path`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_log_share.py`:

```python
import zipfile
from pathlib import Path

from certificados.log_share import build_share_zip
from certificados.logs import LogRun


def _make_run(tmp_path) -> LogRun:
    stamp = "20260101_101010"
    (tmp_path / f"resultados_{stamp}.csv").write_text("timestamp,estado\n", encoding="utf-8")
    (tmp_path / f"ejecucion_{stamp}.log").write_text("log\n", encoding="utf-8")
    (tmp_path / f"diagnostico_{stamp}.jsonl").write_text('{"fila":2}\n', encoding="utf-8")
    (tmp_path / f"contexto_{stamp}.txt").write_text("reporte: R\n", encoding="utf-8")
    return LogRun(results_path=tmp_path / f"resultados_{stamp}.csv", fecha="x")


def _make_config(tmp_path) -> Path:
    cfg = tmp_path / "config.ini"
    cfg.write_text(
        "[service]\nhost = h\nuser = admin\npassword = s3cr3t\n\n"
        "[reports]\nR = /Custom/R.xdo\n",
        encoding="utf-8",
    )
    return cfg


def test_zip_contiene_miembros_esperados(tmp_path):
    run = _make_run(tmp_path)
    cfg = _make_config(tmp_path)
    dest = tmp_path / "salida" / "diag.zip"
    build_share_zip(run, dest, cfg)
    assert dest.exists()
    with zipfile.ZipFile(dest) as zf:
        names = set(zf.namelist())
    assert {"ejecucion.log", "resultados.csv", "diagnostico.jsonl",
            "contexto.txt", "config_saneado.ini", "LEEME.txt"} <= names


def test_zip_config_saneada_sin_credenciales(tmp_path):
    run = _make_run(tmp_path)
    cfg = _make_config(tmp_path)
    dest = tmp_path / "diag.zip"
    build_share_zip(run, dest, cfg)
    with zipfile.ZipFile(dest) as zf:
        saneada = zf.read("config_saneado.ini").decode("utf-8")
    assert "admin" not in saneada
    assert "s3cr3t" not in saneada
    assert "host = h" in saneada


def test_zip_nota_archivos_faltantes(tmp_path):
    run = _make_run(tmp_path)
    run.diagnostics_path.unlink()  # borra el jsonl
    cfg = _make_config(tmp_path)
    dest = tmp_path / "diag.zip"
    build_share_zip(run, dest, cfg)
    with zipfile.ZipFile(dest) as zf:
        names = set(zf.namelist())
        leeme = zf.read("LEEME.txt").decode("utf-8")
    assert "diagnostico.jsonl" not in names
    assert "diagnostico.jsonl" in leeme  # anotado como faltante
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_log_share.py -q`
Expected: FAIL (`No module named 'certificados.log_share'`).

- [ ] **Step 3: Implement the module**

Create `certificados/log_share.py`:

```python
"""Empaqueta los artefactos de una ejecución en un ZIP para compartir por correo.

Incluye los logs del run, el diagnóstico JSONL, el contexto y una copia de la
config SIN credenciales. El .env nunca se incluye.
"""
from __future__ import annotations

import configparser
import io
import zipfile
from pathlib import Path

from .logs import LogRun

_README = """Diagnostico de ejecucion - Certificados de Calidad
=====================================================

Archivos incluidos:
- resultados.csv      Una fila por solicitud (estado, formato, duracion, params, mensaje).
- ejecucion.log       Log de texto legible de la corrida.
- diagnostico.jsonl   Una linea JSON por fila con el detalle para analizar issues:
                        fila, estado, params, params_legibles, soap_request (SIN
                        credenciales), http_status, respuesta (fault/cuerpo solo en
                        error), respuesta_size, mensaje.
- contexto.txt        Version de la app, host, reporte, timeout, motor, workers, SO.
- config_saneado.ini  Copia de config.ini SIN usuario ni contrasena.

Como leer el JSONL: cada linea es un objeto JSON independiente. En Python:
    import json
    with open("diagnostico.jsonl", encoding="utf-8") as fh:
        filas = [json.loads(l) for l in fh]
"""


def _sanitize_config(config_path: str | Path) -> str:
    """Devuelve el texto de config.ini sin las claves user/password de [service]."""
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(config_path, encoding="utf-8")
    if parser.has_section("service"):
        for key in ("user", "password"):
            if parser.has_option("service", key):
                parser.remove_option("service", key)
    buf = io.StringIO()
    parser.write(buf)
    return buf.getvalue()


def build_share_zip(run: LogRun, dest_zip: str | Path, config_path: str | Path) -> Path:
    """Crea el ZIP con los artefactos del run + config saneada + LEEME.

    Los archivos ausentes del run se omiten y se anotan en el LEEME.
    """
    dest = Path(dest_zip)
    dest.parent.mkdir(parents=True, exist_ok=True)
    members = {
        "ejecucion.log": run.log_path,
        "resultados.csv": run.results_path,
        "diagnostico.jsonl": run.diagnostics_path,
        "contexto.txt": run.context_path,
    }
    faltantes: list[str] = []
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, path in members.items():
            if Path(path).exists():
                zf.write(path, arcname=arcname)
            else:
                faltantes.append(arcname)
        try:
            zf.writestr("config_saneado.ini", _sanitize_config(config_path))
        except OSError:
            faltantes.append("config_saneado.ini")
        readme = _README
        if faltantes:
            readme += "\nArchivos no encontrados en este run: " + ", ".join(faltantes) + "\n"
        zf.writestr("LEEME.txt", readme)
    return dest
```

- [ ] **Step 4: Export the function**

In `certificados/__init__.py`, add after the logs import:

```python
from .log_share import build_share_zip
```

And add `"build_share_zip"` to `__all__`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_log_share.py -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add certificados/log_share.py certificados/__init__.py tests/test_log_share.py
git commit -m "feat: build_share_zip empaqueta logs + diagnostico + config saneada"
```

---

### Task 6: Wiring en el controlador (`gui/controller.py`)

**Files:**
- Modify: `gui/controller.py`
- Test: `tests/test_gui_controller.py`

**Interfaces:**
- Consumes: `InMemoryTransportCapture`, `expand_params` (Task 1); `build_gateway(settings, transport=...)` (Task 2); `ResultLogger(..., transport=..., param_expander=...)` (Task 3); `build_share_zip` (Task 5).
- Produces: `BatchController.build_share_zip(run, dest) -> Path`; capturador/expander inyectados en `run_async` y `process_requests_async`.

- [ ] **Step 1: Adjust the existing monkeypatch and add a test**

En `tests/test_gui_controller.py`, las dos líneas que hacen:

```python
    monkeypatch.setattr(ctrl_mod, "build_gateway", lambda settings: FakeClient(settings))
```

cámbialas por (acepta el nuevo kwarg `transport`):

```python
    monkeypatch.setattr(ctrl_mod, "build_gateway", lambda settings, transport=None: FakeClient(settings))
```

Add a new test for `build_share_zip` delegation:

```python
def test_build_share_zip_delegates(monkeypatch, tmp_path):
    from gui.controller import BatchController
    import gui.controller as ctrl_mod

    called = {}

    def fake_build(run, dest, config_path):
        called["args"] = (run, dest, config_path)
        return tmp_path / "z.zip"

    monkeypatch.setattr(ctrl_mod, "build_share_zip", fake_build)
    ctrl = BatchController(str(tmp_path / "config.ini"), str(tmp_path / ".env"))
    out = ctrl.build_share_zip("RUN", tmp_path / "z.zip")
    assert out == tmp_path / "z.zip"
    assert called["args"][0] == "RUN"
```

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui_controller.py -k share -q`
Expected: FAIL (`BatchController` no tiene `build_share_zip`; `build_share_zip` no importado en el módulo).

- [ ] **Step 3: Implement controller wiring**

In `gui/controller.py`:

Add imports to the `from certificados import (...)` block:

```python
    InMemoryTransportCapture,
    build_share_zip,
    expand_params,
```

Add a helper to build catalog maps and the share method (después de `read_catalogs`):

```python
    def _catalog_maps(self) -> dict:
        """{campo: {valor: descripcion}} para expandir params en el diagnóstico."""
        cats = self.read_catalogs()
        return {
            field: {e.valor: e.descripcion for e in entries}
            for field, entries in cats.items()
        }

    def build_share_zip(self, run, dest):
        """Empaqueta el run seleccionado en un ZIP para compartir."""
        return build_share_zip(run, dest, self.config_path)
```

Enrich `_run_context` (module-level function) to add data para `contexto.txt`:

```python
def _run_context(settings, origen: str) -> dict:
    """Contexto de la corrida que se guarda en los logs (para saber que se uso)."""
    import platform

    from certificados import __version__
    return {
        "reporte": settings.report_key,
        "ruta_reporte": settings.report_path,
        "host": settings.host,
        "motor_pdf": getattr(settings, "pdf_engine", "oracle"),
        "workers": settings.max_workers,
        "timeout": settings.timeout,
        "version_app": __version__,
        "sistema": platform.platform(),
        "origen": origen,
    }
```

In `run_async`, inside `task()`, después de `settings = load_settings(...)` y antes de crear el gateway, agrega el capturador y el expander, y pásalos:

```python
                capture = InMemoryTransportCapture()
                maps = self._catalog_maps()
                expander = lambda params: expand_params(params, maps)
                gateway = build_gateway(settings, transport=capture)
```

y cambia la construcción del `ResultLogger` para incluir el diagnóstico:

```python
                with ResultLogger(settings.log_dir, settings.log_level,
                                  extra_handlers=[handler], context=context,
                                  transport=capture, param_expander=expander) as logger:
```

Aplica el mismo cambio en `process_requests_async`: crea `capture`/`maps`/`expander`, usa `build_gateway(settings, transport=capture)` y pásalos al `ResultLogger`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_gui_controller.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gui/controller.py tests/test_gui_controller.py
git commit -m "feat: controller inyecta diagnostico en las corridas y expone build_share_zip"
```

---

### Task 7: Botón "Compartir (ZIP)" y params legibles en la GUI (`gui/app.py`)

**Files:**
- Modify: `gui/app.py`

**Interfaces:**
- Consumes: `controller.build_share_zip(run, dest)` (Task 6); `expand_params` para la vista de detalle.

- [ ] **Step 1: Add the "Compartir" button**

In `gui/app.py`, en `_build_logs_tab`, reemplaza el botón "Refrescar" (actualmente):

```python
        ttk.Button(parent, text="Refrescar", command=self._load_runs).pack(
            anchor="w", padx=8, pady=(0, 4)
        )
```

por una fila con ambos botones:

```python
        botones = ttk.Frame(parent)
        botones.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(botones, text="Refrescar", command=self._load_runs).pack(side="left")
        ttk.Button(botones, text="Compartir (ZIP)", command=self._share_run).pack(side="left", padx=6)
```

- [ ] **Step 2: Add a "Parametros" column to the detail tree**

En `_build_logs_tab`, en la sub-pestaña "Resultados", agrega la columna `parametros` a `det_cols` y su heading/width. Cambia:

```python
        det_cols = ("fila", "reporte", "estado", "formato", "duracion_seg", "archivo", "mensaje")
```
por:
```python
        det_cols = ("fila", "estado", "formato", "duracion_seg", "parametros", "archivo", "mensaje")
```

y en el bucle de columnas usa:

```python
        for col, text, width in (
            ("fila", "Fila", 50),
            ("estado", "Estado", 90),
            ("formato", "Formato", 70),
            ("duracion_seg", "Duracion(s)", 90),
            ("parametros", "Parametros", 280),
            ("archivo", "Archivo", 180),
            ("mensaje", "Mensaje", 260),
        ):
```

- [ ] **Step 3: Populate params in the detail rows**

En `_on_run_selected`, dentro del `for row in self.controller.read_run_results(...)`, calcula los params legibles y cambia el `values` del insert. Reemplaza el cuerpo del bucle por:

```python
        import json

        from certificados.diagnostics import expand_params

        maps = {
            field: {e.valor: e.descripcion for e in entries}
            for field, entries in self._catalogs.items()
        }
        for row in self.controller.read_run_results(run.results_path):
            estado = (row.get("estado") or "").upper()
            try:
                params = json.loads(row.get("parametros") or "{}")
            except (ValueError, TypeError):
                params = {}
            legibles = expand_params(params, maps)
            resumen = ", ".join(
                f"{k}={v}" for k, v in legibles.items() if v and not k.endswith("OBSERVACIONES")
            )
            self._detail_tree.insert(
                "", "end",
                values=(
                    row.get("fila", ""), row.get("estado", ""), row.get("formato", ""),
                    row.get("duracion_seg", ""), resumen, row.get("archivo", ""),
                    row.get("mensaje", ""),
                ),
                tags=(estado,) if estado in ("OK", "ERROR", "INVALIDO") else (),
            )
```

- [ ] **Step 4: Add the `_share_run` handler**

Agrega el método (junto a `_on_run_selected`):

```python
    def _share_run(self) -> None:
        """Empaqueta la ejecución seleccionada en un ZIP para enviar por correo."""
        selection = self._runs_tree.selection()
        if not selection:
            messagebox.showinfo("Compartir", "Selecciona una ejecución primero.", parent=self)
            return
        run = self._runs_by_iid.get(selection[0])
        if run is None:
            return
        stamp = run.results_path.stem.replace("resultados_", "")
        dest = filedialog.asksaveasfilename(
            title="Guardar diagnóstico",
            defaultextension=".zip",
            initialfile=f"diagnostico_{stamp}.zip",
            filetypes=[("Archivo ZIP", "*.zip")],
        )
        if not dest:
            return
        try:
            path = self.controller.build_share_zip(run, dest)
        except Exception as exc:
            messagebox.showerror("Compartir", f"No se pudo crear el ZIP:\n{exc}", parent=self)
            return
        messagebox.showinfo("Compartir", f"Diagnóstico guardado en:\n{path}", parent=self)
```

- [ ] **Step 5: Smoke check (import + construcción de widgets)**

Run: `.venv/Scripts/python.exe -c "import ast; ast.parse(open('gui/app.py', encoding='utf-8').read()); print('syntax OK')"`
Expected: `syntax OK`.

Manual (requiere entorno gráfico): abrir la app, pestaña Logs, seleccionar una corrida, confirmar que la columna Parametros muestra los valores legibles y que "Compartir (ZIP)" genera el archivo con los 6 miembros.

- [ ] **Step 6: Commit**

```bash
git add gui/app.py
git commit -m "feat: boton Compartir (ZIP) y columna de parametros legibles en Logs"
```

---

### Task 8: Verificación integral

**Files:** ninguno (validación).

- [ ] **Step 1: Run the full suite**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: PASS, cobertura global ≥80%.

- [ ] **Step 2: Sanity de seguridad (sin credenciales en artefactos)**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_diagnostics.py tests/test_log_share.py -q
```
Expected: PASS (redacción y config saneada verificadas).

- [ ] **Step 3: Commit (si hubo ajustes)**

```bash
git add -A
git commit -m "test: verificacion integral de logs mejorados y compartir"
```

---

## Self-Review

**Spec coverage:**
- Compartir ZIP (una ejecución) → Task 5 + Task 7. ✔
- Diagnóstico por fila (SOAP redactado, respuesta/fault, OK solo metadata) → Task 2 + Task 3. ✔
- Params legibles → Task 1 (`expand_params`), usado en Task 3 (JSONL) y Task 7 (GUI). ✔
- Contexto/entorno → Task 3 (`contexto.txt`) + Task 6 (`_run_context` enriquecido). ✔
- Config saneada sin user/pass; `.env` nunca → Task 5. ✔
- README en el zip → Task 5 (`_README`). ✔
- Redacción de credenciales garantizada por tests → Task 1, Task 2, Task 5. ✔
- Best-effort (no rompe la ejecución) → `_safe_record` (Task 2), try/except en `_jsonl` (Task 3). ✔
- `LogRun` rutas → Task 4. ✔
- Wiring de corridas → Task 6. ✔

**Type consistency:** `TransportCapture.record/get`, `TransportRecord` (soap/status/response_body/is_report/size), `build_gateway(settings, transport=None)`, `ResultLogger(..., transport=, param_expander=)`, `build_share_zip(run, dest, config_path)`, `expand_params(params, catalog_maps)` — usados de forma consistente entre tareas.

**Placeholder scan:** sin TBD/TODO; todo el código y los tests son concretos.
