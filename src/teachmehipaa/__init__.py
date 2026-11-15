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
    WebhookSignatureError,
    WebhookSignatureErrorCode,
)
from ._core._files import FileInput
from ._core._models import BinaryResponse, LastResponse
from ._core._pagination import AsyncPage, SyncPage
from ._core._sentinel import NOT_GIVEN, NotGiven
from ._extensions.events import AsyncEventTail, EventTail
from ._version import __version__
from ._webhooks import Webhook

__all__ = [
    "NOT_GIVEN",
    "APIConnectionError",
    "APIError",
    "APITimeoutError",
    "AppInfo",
    "AsyncEventTail",
    "AsyncPage",
    "AsyncTeachMeHipaa",
    "AuthenticationError",
    "BinaryResponse",
    "ConflictError",
    "Environment",
    "EventTail",
    "FieldError",
    "FileInput",
    "IdempotencyError",
    "InvalidRequestError",
    "LastResponse",
    "NotFoundError",
    "NotGiven",
    "OAuthError",
    "PermissionDeniedError",
    "PreconditionFailedError",
    "RateLimitError",
    "SyncPage",
    "TeachMeHipaa",
    "TeachMeHipaaError",
    "Webhook",
    "WebhookSignatureError",
    "WebhookSignatureErrorCode",
    "__version__",
]
