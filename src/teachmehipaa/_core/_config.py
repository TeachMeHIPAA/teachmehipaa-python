from __future__ import annotations

import platform
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, TypedDict, TypeVar, get_args

import httpx

from .._version import __version__

Environment = Literal["live", "sandbox"]
T = TypeVar("T")

ENVIRONMENT_BASE_URLS: Mapping[Environment, str] = MappingProxyType(
    {
        "live": "https://api.tme.so/v1",
        "sandbox": "https://sandbox.api.tme.so/v1",
    }
)

TOKEN_PATH = "/auth/token"  # noqa: S105 -- a path, not a secret

DEFAULT_MAX_RETRIES = 2
# The same in every TeachMeHIPAA SDK, and Stripe's default.
DEFAULT_TIMEOUT = 80.0


class _AppInfoOptional(TypedDict, total=False):
    version: str
    url: str


class AppInfo(_AppInfoOptional):
    """Identifies the calling integration in the User-Agent."""

    name: str


@dataclass(frozen=True)
class ClientConfig:
    environment: Environment
    base_url: str
    organization_id: str | None
    scopes: tuple[str, ...] | None
    max_retries: int
    timeout: httpx.Timeout
    user_agent: str
    clock: Callable[[], float]


def make_config(
    *,
    environment: Environment,
    base_url: str | None,
    organization_id: str | None,
    scopes: Sequence[str] | None,
    max_retries: int,
    timeout: float | httpx.Timeout,
    app_info: AppInfo | None,
    clock: Callable[[], float] | None,
) -> ClientConfig:
    if max_retries < 0:
        raise ValueError("max_retries must be zero or more")
    return ClientConfig(
        environment=environment,
        base_url=resolve_base_url(environment, base_url),
        organization_id=organization_id,
        scopes=None if scopes is None else tuple(scopes),
        max_retries=max_retries,
        timeout=httpx.Timeout(timeout),
        user_agent=_user_agent(app_info),
        clock=clock or time.monotonic,
    )


def for_environment(values: Mapping[Environment, T], environment: Environment) -> T:
    """`environment`'s entry in `values`, refusing a name that isn't an
    Environment."""
    if environment not in get_args(Environment):
        raise ValueError(
            f"environment must be 'live' or 'sandbox', not {environment!r}"
        )
    return values[environment]


def resolve_base_url(environment: Environment, base_url: str | None) -> str:
    environment_url = for_environment(ENVIRONMENT_BASE_URLS, environment)
    return (base_url or environment_url).rstrip("/")


def _user_agent(app_info: AppInfo | None) -> str:
    agent = (
        f"teachmehipaa-python/{__version__} "
        f"python/{platform.python_version()} httpx/{httpx.__version__}"
    )
    if app_info is None:
        return agent
    app = app_info["name"]
    if "version" in app_info:
        app += f"/{app_info['version']}"
    if "url" in app_info:
        app += f" ({app_info['url']})"
    return f"{agent} {app}"
