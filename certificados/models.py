"""Data model that represents a single report request and its results (Tarea 1).

These are plain data holders with no I/O, so any component (CSV, DB, queue, API)
can produce a ``ReportRequest`` and any executor can consume it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ReportRequest:
    """One report to generate.

    Attributes
    ----------
    row_number:
        1-based position in the source (CSV data rows start at 2 because row 1
        is the header). Used for traceability in logs and validation messages.
    params:
        Oracle BI Publisher report parameters (``P_EMBARQUE`` ...). Kept as a raw
        dict so new report parameters can be added without touching this class.
    output_format:
        ``attributeFormat`` for the service: ``pdf`` | ``xml`` | ``xlsx``.
    output_name:
        Optional explicit output file name. When empty a name is derived.
    """

    row_number: int
    params: Dict[str, str] = field(default_factory=dict)
    output_format: str = "pdf"
    output_name: Optional[str] = None

    def field_values(self) -> Dict[str, str]:
        """Flatten params + meta fields into one dict for validation rules."""
        values = dict(self.params)
        values["FORMATO_SALIDA"] = self.output_format
        values["NOMBRE_ARCHIVO"] = self.output_name or ""
        return values

    def resolved_name(self) -> str:
        """File name to write, deriving one from the shipment id when absent."""
        if self.output_name:
            base = self.output_name
            if base.lower().endswith(f".{self.output_format.lower()}"):
                return base
            return f"{base}.{self.output_format}"
        embarque = self.params.get("P_EMBARQUE") or "reporte"
        return f"Certificado_{embarque}.{self.output_format}"


@dataclass
class ReportResult:
    """Outcome of a successful report generation."""

    request: ReportRequest
    file_path: Path
    size_bytes: int


@dataclass
class BatchSummary:
    """Aggregated counters produced by the batch processor (Tarea 6)."""

    total: int = 0
    success: int = 0
    invalid: int = 0
    failed: int = 0

    @property
    def processed_ok(self) -> bool:
        return self.failed == 0 and self.invalid == 0

    def __str__(self) -> str:
        return (
            f"total={self.total} ok={self.success} "
            f"invalidos={self.invalid} fallidos={self.failed}"
        )
