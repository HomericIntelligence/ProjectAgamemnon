"""Exception hierarchy for the agamemnon-client package."""

from __future__ import annotations


class AgamemnonError(Exception):
    """Base exception for all Agamemnon client errors."""


class AgamemnonConnectionError(AgamemnonError):
    """Raised when the client cannot connect to the Agamemnon service."""


class AgamemnonAPIError(AgamemnonError):
    """Raised when the Agamemnon API returns a non-2xx response."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")
