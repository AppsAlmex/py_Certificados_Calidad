"""Custom exception hierarchy (Tarea 9).

All domain errors derive from ``CertificadoError`` so callers can catch the whole
family with one ``except`` while still being able to distinguish specific causes.
"""


class CertificadoError(Exception):
    """Base class for every error raised by this package."""


class ConfigError(CertificadoError):
    """Configuration missing or invalid (bad config.ini / .env)."""


class CSVReadError(CertificadoError):
    """The CSV file cannot be opened or its headers are invalid."""


class ValidationFailedError(CertificadoError):
    """A request failed validation. Carries the list of issues."""

    def __init__(self, issues):
        self.issues = list(issues)
        detail = "; ".join(str(i) for i in self.issues)
        super().__init__(f"Validacion fallida: {detail}")


class AuthenticationError(CertificadoError):
    """Service rejected the credentials (401/403 or SOAP auth fault)."""


class ReportConnectionError(CertificadoError):
    """Network problem reaching the report service (timeout / DNS / refused)."""


class ReportGenerationError(CertificadoError):
    """Service reached but did not return a valid report."""


class FileSaveError(CertificadoError):
    """The decoded report could not be written to disk."""
