# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.


import httpx

from .._core._pagination import AsyncPage, SyncPage
from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types import Event, EventType, OrgEventsPage


class EventsBase(SyncAPIResource):
    """The generated methods of `events`. The client exposes the hand-written subclass
    `Events` in `_extensions/events.py`.
    """

    def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        after: str | NotGiven = NOT_GIVEN,
        type: EventType | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SyncPage[Event]:
        """List all events.

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
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        return self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/events",
                query={"limit": limit, "after": after, "type": type},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            OrgEventsPage,
            cursor_param="after",
            position_field="event_id",
        )


class AsyncEventsBase(AsyncAPIResource):
    """The generated methods of `events`. The client exposes the hand-written subclass
    `AsyncEvents` in `_extensions/events.py`.
    """

    async def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        after: str | NotGiven = NOT_GIVEN,
        type: EventType | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[Event]:
        """List all events.

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
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        return await self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/events",
                query={"limit": limit, "after": after, "type": type},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            OrgEventsPage,
            cursor_param="after",
            position_field="event_id",
        )
