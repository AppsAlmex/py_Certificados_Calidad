"""Report execution (Tarea 5, Dependency Inversion + Interface Segregation).

``ReportGateway`` is the abstraction the rest of the system depends on. The
concrete ``OracleReportClient`` talks SOAP to Oracle BI Publisher, but callers
(the batch processor, getReport.py) only know the interface, so the transport can
be swapped (mock, REST, queue) without changing them.

Authentication, request building, sending, parsing and saving are separate
methods so each concern can be tested and replaced independently.
"""
from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from pathlib import Path
from xml.sax.saxutils import escape

import requests
from lxml import etree

from .config import Settings
from .exceptions import (
    AuthenticationError,
    FileSaveError,
    ReportConnectionError,
    ReportGenerationError,
)
from .models import ReportRequest, ReportResult


class ReportGateway(ABC):
    """The single method consumers depend on."""

    @abstractmethod
    def run_report(self, request: ReportRequest) -> ReportResult:
        ...


class OracleReportClient(ReportGateway):
    """SOAP client for Oracle BI Publisher ReportService v2."""

    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self._settings = settings
        # Session injected for testability (Dependency Inversion).
        self._session = session or requests.Session()
        # Con verify_ssl=false requests emite InsecureRequestWarning en cada
        # llamada; si el usuario apago la verificacion a proposito, evitamos el ruido.
        if not settings.verify_ssl:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # -- public API ---------------------------------------------------------
    def run_report(self, request: ReportRequest) -> ReportResult:
        soap = self._build_soap(request)
        response = self._send(soap)
        content = self._extract_report(response)
        return self._save(request, content)

    # -- steps --------------------------------------------------------------
    def _build_soap(self, request: ReportRequest) -> str:
        param_xml = "".join(
            f"""
        <v2:item>
            <v2:name>{escape(name)}</v2:name>
            <v2:values>
                <v2:item>{escape(value)}</v2:item>
            </v2:values>
        </v2:item>"""
            for name, value in request.params.items()
        )
        return f"""
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:v2="http://xmlns.oracle.com/oxp/service/v2">
   <soapenv:Header/>
   <soapenv:Body>
      <v2:runReport>
         <v2:reportRequest>
            <v2:attributeFormat>{escape(request.output_format)}</v2:attributeFormat>
            <v2:parameterNameValues>
               <v2:listOfParamNameValues>
                  {param_xml}
               </v2:listOfParamNameValues>
            </v2:parameterNameValues>
            <v2:reportAbsolutePath>{escape(self._settings.report_path.strip())}</v2:reportAbsolutePath>
         </v2:reportRequest>
         <v2:userID>{escape(self._settings.user)}</v2:userID>
         <v2:password>{escape(self._settings.password)}</v2:password>
      </v2:runReport>
   </soapenv:Body>
</soapenv:Envelope>
""".strip()

    def _send(self, soap: str) -> requests.Response:
        headers = {"Content-Type": "text/xml; charset=UTF-8"}
        try:
            response = self._session.post(
                self._settings.service_url,
                data=soap.encode("utf-8"),
                headers=headers,
                verify=self._settings.verify_ssl,
                # (connect, read): read cubre reportes que tardan hasta ~70 min.
                timeout=self._settings.request_timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise ReportConnectionError(f"Timeout al llamar al servicio: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise ReportConnectionError(f"No hay conexion con el servicio: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise ReportConnectionError(f"Error de red: {exc}") from exc

        if response.status_code in (401, 403):
            raise AuthenticationError(
                f"Credenciales rechazadas (HTTP {response.status_code})"
            )
        if response.status_code != 200:
            raise ReportGenerationError(
                f"Respuesta HTTP {response.status_code}: {response.text[:500]}"
            )
        return response

    def _extract_report(self, response: requests.Response) -> bytes:
        ctype = response.headers.get("Content-Type", "")
        if "xml" not in ctype.lower():
            raise ReportGenerationError(
                f"Respuesta no XML (Content-Type: {ctype}). Endpoint o auth incorrectos."
            )
        try:
            root = etree.fromstring(response.content)
        except etree.XMLSyntaxError as exc:
            raise ReportGenerationError(f"XML de respuesta invalido: {exc}") from exc

        # A SOAP fault usually means bad credentials or bad report path.
        faults = root.xpath("//*[local-name()='faultstring']/text()")
        if faults:
            message = faults[0]
            if "auth" in message.lower() or "credential" in message.lower():
                raise AuthenticationError(message)
            raise ReportGenerationError(f"SOAP fault: {message}")

        report_bytes = root.xpath("//*[local-name()='reportBytes']/text()")
        if not report_bytes:
            raise ReportGenerationError("La respuesta no contiene reportBytes")
        try:
            return base64.b64decode(report_bytes[0])
        except (ValueError, base64.binascii.Error) as exc:
            raise ReportGenerationError(f"reportBytes no es base64 valido: {exc}") from exc

    def _save(self, request: ReportRequest, content: bytes) -> ReportResult:
        out_dir = self._settings.output_dir
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / request.resolved_name()
            path.write_bytes(content)
        except OSError as exc:
            raise FileSaveError(f"No se pudo guardar el reporte: {exc}") from exc
        return ReportResult(request=request, file_path=path, size_bytes=len(content))
