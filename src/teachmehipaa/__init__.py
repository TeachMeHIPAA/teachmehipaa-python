"""The official Python library for the TeachMeHIPAA Developer API."""

from ._client import AsyncTeachMeHipaa, TeachMeHipaa
from ._core._config import AppInfo, Environment
from ._core._errors import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    ConflictError,
    FieldError,
    IdempotencyError,
    InvalidRequestError,
    NotFoundError,
    OAuthError,
    PermissionDeniedError,
    PreconditionFailedError,
    RateLimitError,
    TeachMeHipaaError,
)
from ._core._models import LastResponse
from ._core._sentinel import NOT_GIVEN, NotGiven
from ._version import __version__

__all__ = [
    "NOT_GIVEN",
    "APIConnectionError",
    "APIError",
    "APITimeoutError",
    "AppInfo",
    "AsyncTeachMeHipaa",
    "AuthenticationError",
    "ConflictError",
    "Environment",
    "FieldError",
    "IdempotencyError",
    "InvalidRequestError",
    "LastResponse",
    "NotFoundError",
    "NotGiven",
    "OAuthError",
    "PermissionDeniedError",
    "PreconditionFailedError",
    "RateLimitError",
    "TeachMeHipaa",
    "TeachMeHipaaError",
    "__version__",
]
