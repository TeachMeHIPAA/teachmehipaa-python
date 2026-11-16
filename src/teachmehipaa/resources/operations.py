# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.


import httpx

from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from .._operations import (
    AsyncOperation,
    Operation,
    async_request_operation,
    request_operation,
)


class Operations(SyncAPIResource):
    def retrieve(
        self,
        operation_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Retrieve an operation.

        Retrieves a bulk operation and its result. Operations are kept for 24 hours.

        Args:
            operation_id: The server-minted opaque operation id.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        return request_operation(
            self._pipeline,
            ApiRequest(
                "GET",
                "/organizations/{orgId}/operations/{operationId}",
                path_params={"operationId": operation_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
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
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> AsyncOperation:
        """Retrieve an operation.

        Retrieves a bulk operation and its result. Operations are kept for 24 hours.

        Args:
            operation_id: The server-minted opaque operation id.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        return await async_request_operation(
            self._pipeline,
            ApiRequest(
                "GET",
                "/organizations/{orgId}/operations/{operationId}",
                path_params={"operationId": operation_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            AsyncOperation,
        )
