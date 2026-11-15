# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.


import httpx

from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types import Operation


class Operations(SyncAPIResource):
    def retrieve(
        self,
        operation_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Retrieve an operation

        Retrieves a bulk operation and its result. Operations are kept for 24 hours.

        Args:
            operation_id: The server-minted opaque operation id.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/operations/{operationId}",
                path_params={"operationId": operation_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Operation,
        )


class AsyncOperations(AsyncAPIResource):
    async def retrieve(
        self,
        operation_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Retrieve an operation

        Retrieves a bulk operation and its result. Operations are kept for 24 hours.

        Args:
            operation_id: The server-minted opaque operation id.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/operations/{operationId}",
                path_params={"operationId": operation_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Operation,
        )
