# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.


import httpx

from .._core._pagination import AsyncPage, SyncPage
from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types import Event, EventType, OrgEventsPage


class Events(SyncAPIResource):
    def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        after: str | NotGiven = NOT_GIVEN,
        type: EventType | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SyncPage[Event]:
        """List all events

        Returns a list of the organization's events from the last 30 days, oldest first.
        Pass the last `eventId` you processed as `after` to resume where you stopped,
        and `type` to list one event type.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            after: Return events after this event id (exclusive). The previous page's
                `nextCursor`.
            type: Filter to one event type.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/events",
                query={"limit": limit, "after": after, "type": type},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            OrgEventsPage,
            cursor_param="after",
        )


class AsyncEvents(AsyncAPIResource):
    async def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        after: str | NotGiven = NOT_GIVEN,
        type: EventType | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[Event]:
        """List all events

        Returns a list of the organization's events from the last 30 days, oldest first.
        Pass the last `eventId` you processed as `after` to resume where you stopped,
        and `type` to list one event type.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            after: Return events after this event id (exclusive). The previous page's
                `nextCursor`.
            type: Filter to one event type.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/events",
                query={"limit": limit, "after": after, "type": type},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            OrgEventsPage,
            cursor_param="after",
        )
