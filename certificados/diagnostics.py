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
