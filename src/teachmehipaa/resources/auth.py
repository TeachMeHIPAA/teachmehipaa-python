# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.


import httpx

from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types import TokenIntrospection


class Auth(SyncAPIResource):
    def introspect(
        self,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> TokenIntrospection:
        """Retrieve the current token

        Describes the access token you call with: whether it belongs to an API client or
        a person, its organization, its scopes and when it expires. Needs no scope.

        Args:
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "GET",
                "/auth/introspection",
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            TokenIntrospection,
        )


class AsyncAuth(AsyncAPIResource):
    async def introspect(
        self,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> TokenIntrospection:
        """Retrieve the current token

        Describes the access token you call with: whether it belongs to an API client or
        a person, its organization, its scopes and when it expires. Needs no scope.

        Args:
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "GET",
                "/auth/introspection",
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            TokenIntrospection,
        )
