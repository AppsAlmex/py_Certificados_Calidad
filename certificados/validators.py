"""Parameter validation (Tarea 4, SRP + Open/Closed Principle).

Validation is expressed as a list of small ``ValidationRule`` objects. Adding a
new check means adding a new rule class (or instance) — existing code is not
modified. The ``RequestValidator`` just runs every rule and aggregates issues.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Sequence

from .models import ReportRequest


@dataclass
class ValidationIssue:
    """A single problem found in a request, located by row and field."""

    row: int
    field: str
    message: str

    def __str__(self) -> str:
        return f"fila {self.row}, columna '{self.field}': {self.message}"


@dataclass
class ValidationResult:
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)


class ValidationRule(ABC):
    """Strategy: inspect a request, return zero or more issues."""

    @abstractmethod
    def validate(self, request: ReportRequest) -> List[ValidationIssue]:
        ...


class RequiredFieldRule(ValidationRule):
    def __init__(self, field_name: str):
        self.field_name = field_name

    def validate(self, request: ReportRequest) -> List[ValidationIssue]:
        value = request.field_values().get(self.field_name, "")
        if not str(value).strip():
            return [ValidationIssue(request.row_number, self.field_name, "campo obligatorio vacio")]
        return []


class ChoiceRule(ValidationRule):
    def __init__(self, field_name: str, allowed: Iterable[str], case_insensitive: bool = True):
        self.field_name = field_name
        self.case_insensitive = case_insensitive
        self.allowed = [a.lower() if case_insensitive else a for a in allowed]

    def validate(self, request: ReportRequest) -> List[ValidationIssue]:
        raw = str(request.field_values().get(self.field_name, "")).strip()
        candidate = raw.lower() if self.case_insensitive else raw
        if candidate and candidate not in self.allowed:
            return [
                ValidationIssue(
                    request.row_number,
                    self.field_name,
                    f"valor '{raw}' no permitido (esperado: {', '.join(self.allowed)})",
                )
            ]
        return []


class NumericRule(ValidationRule):
    """Value must be an integer. Empty is allowed unless ``allow_empty`` is False."""

    def __init__(self, field_name: str, allow_empty: bool = True):
        self.field_name = field_name
        self.allow_empty = allow_empty

    def validate(self, request: ReportRequest) -> List[ValidationIssue]:
        raw = str(request.field_values().get(self.field_name, "")).strip()
        if not raw:
            if self.allow_empty:
                return []
            return [ValidationIssue(request.row_number, self.field_name, "valor numerico requerido")]
        if not raw.lstrip("-").isdigit():
            return [ValidationIssue(request.row_number, self.field_name, f"'{raw}' no es un numero entero")]
        return []


class DateRule(ValidationRule):
    """Value must match ``date_format``. Reusable for reports that use dates."""

    def __init__(self, field_name: str, date_format: str = "%Y-%m-%d", allow_empty: bool = True):
        self.field_name = field_name
        self.date_format = date_format
        self.allow_empty = allow_empty

    def validate(self, request: ReportRequest) -> List[ValidationIssue]:
        raw = str(request.field_values().get(self.field_name, "")).strip()
        if not raw:
            if self.allow_empty:
                return []
            return [ValidationIssue(request.row_number, self.field_name, "fecha requerida")]
        try:
            datetime.strptime(raw, self.date_format)
        except ValueError:
            return [
                ValidationIssue(
                    request.row_number,
                    self.field_name,
                    f"fecha '{raw}' no cumple formato {self.date_format}",
                )
            ]
        return []


class RequestValidator:
    """Runs a collection of rules and aggregates their issues."""

    def __init__(self, rules: Sequence[ValidationRule] | None = None):
        self._rules: List[ValidationRule] = list(rules or [])

    def add_rule(self, rule: ValidationRule) -> "RequestValidator":
        self._rules.append(rule)
        return self

    def validate(self, request: ReportRequest) -> ValidationResult:
        issues: List[ValidationIssue] = []
        for rule in self._rules:
            issues.extend(rule.validate(request))
        return ValidationResult(valid=not issues, issues=issues)


def build_default_validator() -> RequestValidator:
    """Rule set for the Certificado de Calidad report."""
    return RequestValidator(
        [
            RequiredFieldRule("P_EMBARQUE"),
            RequiredFieldRule("P_FORMATO"),
            RequiredFieldRule("P_INSPECTOR"),
            RequiredFieldRule("P_PLANTA_PROD"),
            # P_TANQUE es opcional (no requerido) tanto en CSV como en el individual.
            ChoiceRule("FORMATO_SALIDA", ["pdf", "xml", "xlsx"]),
            NumericRule("P_CANTIDAD1", allow_empty=True),
            NumericRule("P_CANTIDAD2", allow_empty=True),
            NumericRule("P_CANTIDAD3", allow_empty=True),
            NumericRule("P_CANTIDAD4", allow_empty=True),
        ]
    )
