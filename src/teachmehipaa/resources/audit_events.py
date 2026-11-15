# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.

from datetime import datetime

import httpx

from .._core._pagination import AsyncPage, SyncPage
from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types import (
    AuditEvent,
    AuditEventsPage,
    ListAuditEventsTransition,
    ListAuditEventsType,
)


class AuditEvents(SyncAPIResource):
    def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        type: ListAuditEventsType | NotGiven = NOT_GIVEN,
        transition: ListAuditEventsTransition | NotGiven = NOT_GIVEN,
        subject_id: str | NotGiven = NOT_GIVEN,
        since: datetime | NotGiven = NOT_GIVEN,
        until: datetime | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SyncPage[AuditEvent]:
        """List all audit events

        Returns a list of the organization's audit events, newest first. Filter by
        `type`, `transition`, `subjectId`, or a `since` and `until` range.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            type: Filter to one audit-event family.
            transition: Filter to one lifecycle transition.
            subject_id: Filter to one member (canonical subject id).
            since: Inclusive lower bound on `at` (ISO-8601 instant).
            until: Inclusive upper bound on `at` (ISO-8601 instant).
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/audit-events",
                query={
                    "limit": limit,
                    "cursor": cursor,
                    "type": type,
                    "transition": transition,
                    "subjectId": subject_id,
                    "since": since,
                    "until": until,
                },
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            AuditEventsPage,
            cursor_param="cursor",
        )


class AsyncAuditEvents(AsyncAPIResource):
    async def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        type: ListAuditEventsType | NotGiven = NOT_GIVEN,
        transition: ListAuditEventsTransition | NotGiven = NOT_GIVEN,
        subject_id: str | NotGiven = NOT_GIVEN,
        since: datetime | NotGiven = NOT_GIVEN,
        until: datetime | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[AuditEvent]:
        """List all audit events

        Returns a list of the organization's audit events, newest first. Filter by
        `type`, `transition`, `subjectId`, or a `since` and `until` range.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            type: Filter to one audit-event family.
            transition: Filter to one lifecycle transition.
            subject_id: Filter to one member (canonical subject id).
            since: Inclusive lower bound on `at` (ISO-8601 instant).
            until: Inclusive upper bound on `at` (ISO-8601 instant).
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/audit-events",
                query={
                    "limit": limit,
                    "cursor": cursor,
                    "type": type,
                    "transition": transition,
                    "subjectId": subject_id,
                    "since": since,
                    "until": until,
                },
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            AuditEventsPage,
            cursor_param="cursor",
        )
