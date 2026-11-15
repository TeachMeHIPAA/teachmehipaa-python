# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.

from collections.abc import Sequence

import httpx

from .._core._pagination import AsyncPage, SyncPage
from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from .._operations import (
    AsyncOperation,
    Operation,
    async_request_operation,
    request_operation,
)
from ..types import (
    Learner,
    LearnerBatchUpsertRequestDelivery,
    LearnerBatchUpsertRequestItemsItemParam,
    LearnerBatchUpsertRequestSeatPolicy,
    LearnerCreateRequestDelivery,
    LearnerCreateRequestSeatPolicy,
    LearnerLaunchLink,
    LearnerRemindAccepted,
    LearnersExportRequestFormat,
    LearnersPage,
    LearnerStatus,
    LearnerUpsertRequestDelivery,
    LearnerUpsertRequestSeatPolicy,
    LearnerWriteResult,
)


class Learners(SyncAPIResource):
    def batch_upsert(
        self,
        *,
        items: Sequence[LearnerBatchUpsertRequestItemsItemParam],
        delivery: LearnerBatchUpsertRequestDelivery | NotGiven = NOT_GIVEN,
        seat_policy: LearnerBatchUpsertRequestSeatPolicy | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Create many learners

        Creates or retrieves up to 500 learners in one request. Each item works like
        creating one learner and succeeds or fails on its own.

        Args:
            items: Up to 500 learners, each with the same fields as creating one
                learner.
            delivery: Applies to every item. `email` (default) sends invites; `none`
                sends nothing.
            seat_policy: Applies to every item. `require_available` fails an item when
                no seat is free.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return request_operation(
            self._pipeline,
            ApiRequest(
                "POST",
                "/organizations/{orgId}/learners:batchUpsert",
                body={"items": items, "delivery": delivery, "seatPolicy": seat_policy},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            Operation,
        )

    def create(
        self,
        *,
        email: str,
        name: str | NotGiven = NOT_GIVEN,
        external_id: str | NotGiven = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        delivery: LearnerCreateRequestDelivery | NotGiven = NOT_GIVEN,
        seat_policy: LearnerCreateRequestSeatPolicy | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> LearnerWriteResult:
        """Create a learner

        Adds a person to the organization and invites them to a course in one call,
        using one seat. If the email or `externalId` already belongs to an active
        learner in the course, nothing is created. With `delivery: "none"`, no email is
        sent and the response includes a `joinUrl` for you to deliver.

        `created` is true when this call created the Learner (201) and false when it
        already existed (200).

        Args:
            email: The learner's email address.
            name: The learner's full name.
            external_id: Your own id for the learner, unique within the organization.
            course_id: The course to invite them to. Defaults to the organization's
                default course.
            delivery: `email` (default) sends the invite email. `none` sends nothing and
                returns `joinUrl` for you to deliver.
            seat_policy: `require_available` fails with `409` when no seat is free.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_write_result(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/learners",
                body={
                    "email": email,
                    "name": name,
                    "externalId": external_id,
                    "courseId": course_id,
                    "delivery": delivery,
                    "seatPolicy": seat_policy,
                },
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            LearnerWriteResult,
        )

    def create_launch_link(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> LearnerLaunchLink:
        """Create a launch link

        Creates a link that opens the course with the learner already signed in, for a
        "Start training" button in your product. The link works once and expires after 5
        minutes: create it when the learner clicks, then redirect them to it. Never
        email, store or log it. Only for a learner who has accepted their invite.

        Args:
            learner_id: The learner's canonical subject id (sub_… ULID).
            course_id: The course. Defaults to the organization's default course.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/learners/{learnerId}:createLaunchLink",
                path_params={"learnerId": learner_id},
                query={"courseId": course_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            LearnerLaunchLink,
        )

    def export(
        self,
        *,
        format: LearnersExportRequestFormat,
        course_id: str | NotGiven = NOT_GIVEN,
        status: LearnerStatus | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Export learners

        Exports the organization's learners in one course as CSV, optionally only those
        with one `status`. Requires the `learners:read` scope.

        Args:
            format: The file format. Only `csv` today.
            course_id: The course to export. Defaults to the organization's default
                course.
            status: Only export learners with this status.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return request_operation(
            self._pipeline,
            ApiRequest(
                "POST",
                "/organizations/{orgId}/learners:export",
                body={"format": format, "courseId": course_id, "status": status},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            Operation,
        )

    def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        email: str | NotGiven = NOT_GIVEN,
        external_id: str | NotGiven = NOT_GIVEN,
        status: LearnerStatus | NotGiven = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SyncPage[Learner]:
        """List all learners

        Returns a list of the organization's learners in one course, with each learner's
        status, dates and current certificate. Filter by `status`, or find one learner
        by `email` or `externalId`.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            external_id: The integration's own id for the learner (unique per
                organization), or the SCIM `externalId` when none was set.
            course_id: The course. Defaults to the organization's default course.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/learners",
                query={
                    "limit": limit,
                    "cursor": cursor,
                    "email": email,
                    "externalId": external_id,
                    "status": status,
                    "courseId": course_id,
                },
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            LearnersPage,
            cursor_param="cursor",
            style="cursor",
        )

    def offboard(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        if_match: str | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Learner:
        """Offboard a learner

        Removes a learner from the organization. A learner who hasn't started has their
        invite cancelled and the seat returned; a learner who has started keeps their
        training history and certificates. Releases the learner's `externalId`.

        Args:
            learner_id: The learner's canonical subject id (sub_… ULID).
            course_id: The course. Defaults to the organization's default course.
            if_match: The ETag the object was read with (`last_response.etag`).
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/learners/{learnerId}:offboard",
                path_params={"learnerId": learner_id},
                query={"courseId": course_id},
                headers={"if-match": if_match},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            Learner,
        )

    def remind(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> LearnerRemindAccepted:
        """Remind a learner

        Emails the learner a reminder: the invite again if they haven't started, or a
        nudge to finish if they have.

        Args:
            learner_id: The learner's canonical subject id (sub_… ULID).
            course_id: The course. Defaults to the organization's default course.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/learners/{learnerId}:remind",
                path_params={"learnerId": learner_id},
                query={"courseId": course_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            LearnerRemindAccepted,
        )

    def retrieve(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Learner:
        """Retrieve a learner

        Retrieves a learner's status in one course.

        Args:
            learner_id: The learner's canonical subject id (sub_… ULID).
            course_id: The course. Defaults to the organization's default course.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/learners/{learnerId}",
                path_params={"learnerId": learner_id},
                query={"courseId": course_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Learner,
        )

    def update(
        self,
        learner_id: str,
        /,
        *,
        if_match: str,
        name: str | NotGiven = NOT_GIVEN,
        external_id: str | NotGiven | None = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Learner:
        """Update a learner

        Updates a learner's `name` or `externalId`; parameters you don't send are left
        unchanged. Send the body as `application/merge-patch+json` with the learner's
        current `ETag` in `If-Match`.

        Args:
            learner_id: The learner's canonical subject id (sub_… ULID).
            if_match: The ETag the object was read with (`last_response.etag`).
            name: The learner's full name.
            external_id: Your own id for the learner. Set it to `null` to clear it.
            course_id: The course. Defaults to the organization's default course.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "PATCH",
                "/organizations/{orgId}/learners/{learnerId}",
                path_params={"learnerId": learner_id},
                body={"name": name, "externalId": external_id},
                content_type="application/merge-patch+json",
                query={"courseId": course_id},
                headers={"if-match": if_match},
                org_scoped=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Learner,
        )

    def upsert_by_external_id(
        self,
        external_id: str,
        /,
        *,
        email: str,
        name: str | NotGiven = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        delivery: LearnerUpsertRequestDelivery | NotGiven = NOT_GIVEN,
        seat_policy: LearnerUpsertRequestSeatPolicy | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> LearnerWriteResult:
        """Create or retrieve a learner by your id

        Makes sure a learner exists for your own id. Creates and invites the learner the
        first time, and returns them on every later call, so a sync job can replay it
        safely. Never uses a second seat.

        `created` is true when this call created the Learner (201) and false when it
        already existed (200).

        Args:
            external_id: Your id for the learner, URL-encoded.
            email: The learner's email address.
            name: The learner's full name.
            course_id: The course to invite them to. Defaults to the organization's
                default course.
            delivery: `email` (default) sends the invite email. `none` sends nothing and
                returns `joinUrl` for you to deliver.
            seat_policy: `require_available` fails with `409` when no seat is free.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_write_result(
            ApiRequest(
                "PUT",
                "/organizations/{orgId}/learners/by-external-id/{externalId}",
                path_params={"externalId": external_id},
                body={
                    "email": email,
                    "name": name,
                    "courseId": course_id,
                    "delivery": delivery,
                    "seatPolicy": seat_policy,
                },
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            LearnerWriteResult,
        )


class AsyncLearners(AsyncAPIResource):
    async def batch_upsert(
        self,
        *,
        items: Sequence[LearnerBatchUpsertRequestItemsItemParam],
        delivery: LearnerBatchUpsertRequestDelivery | NotGiven = NOT_GIVEN,
        seat_policy: LearnerBatchUpsertRequestSeatPolicy | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncOperation:
        """Create many learners

        Creates or retrieves up to 500 learners in one request. Each item works like
        creating one learner and succeeds or fails on its own.

        Args:
            items: Up to 500 learners, each with the same fields as creating one
                learner.
            delivery: Applies to every item. `email` (default) sends invites; `none`
                sends nothing.
            seat_policy: Applies to every item. `require_available` fails an item when
                no seat is free.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await async_request_operation(
            self._pipeline,
            ApiRequest(
                "POST",
                "/organizations/{orgId}/learners:batchUpsert",
                body={"items": items, "delivery": delivery, "seatPolicy": seat_policy},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            AsyncOperation,
        )

    async def create(
        self,
        *,
        email: str,
        name: str | NotGiven = NOT_GIVEN,
        external_id: str | NotGiven = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        delivery: LearnerCreateRequestDelivery | NotGiven = NOT_GIVEN,
        seat_policy: LearnerCreateRequestSeatPolicy | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> LearnerWriteResult:
        """Create a learner

        Adds a person to the organization and invites them to a course in one call,
        using one seat. If the email or `externalId` already belongs to an active
        learner in the course, nothing is created. With `delivery: "none"`, no email is
        sent and the response includes a `joinUrl` for you to deliver.

        `created` is true when this call created the Learner (201) and false when it
        already existed (200).

        Args:
            email: The learner's email address.
            name: The learner's full name.
            external_id: Your own id for the learner, unique within the organization.
            course_id: The course to invite them to. Defaults to the organization's
                default course.
            delivery: `email` (default) sends the invite email. `none` sends nothing and
                returns `joinUrl` for you to deliver.
            seat_policy: `require_available` fails with `409` when no seat is free.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_write_result(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/learners",
                body={
                    "email": email,
                    "name": name,
                    "externalId": external_id,
                    "courseId": course_id,
                    "delivery": delivery,
                    "seatPolicy": seat_policy,
                },
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            LearnerWriteResult,
        )

    async def create_launch_link(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> LearnerLaunchLink:
        """Create a launch link

        Creates a link that opens the course with the learner already signed in, for a
        "Start training" button in your product. The link works once and expires after 5
        minutes: create it when the learner clicks, then redirect them to it. Never
        email, store or log it. Only for a learner who has accepted their invite.

        Args:
            learner_id: The learner's canonical subject id (sub_… ULID).
            course_id: The course. Defaults to the organization's default course.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/learners/{learnerId}:createLaunchLink",
                path_params={"learnerId": learner_id},
                query={"courseId": course_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            LearnerLaunchLink,
        )

    async def export(
        self,
        *,
        format: LearnersExportRequestFormat,
        course_id: str | NotGiven = NOT_GIVEN,
        status: LearnerStatus | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncOperation:
        """Export learners

        Exports the organization's learners in one course as CSV, optionally only those
        with one `status`. Requires the `learners:read` scope.

        Args:
            format: The file format. Only `csv` today.
            course_id: The course to export. Defaults to the organization's default
                course.
            status: Only export learners with this status.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await async_request_operation(
            self._pipeline,
            ApiRequest(
                "POST",
                "/organizations/{orgId}/learners:export",
                body={"format": format, "courseId": course_id, "status": status},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            AsyncOperation,
        )

    async def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        email: str | NotGiven = NOT_GIVEN,
        external_id: str | NotGiven = NOT_GIVEN,
        status: LearnerStatus | NotGiven = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[Learner]:
        """List all learners

        Returns a list of the organization's learners in one course, with each learner's
        status, dates and current certificate. Filter by `status`, or find one learner
        by `email` or `externalId`.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            external_id: The integration's own id for the learner (unique per
                organization), or the SCIM `externalId` when none was set.
            course_id: The course. Defaults to the organization's default course.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/learners",
                query={
                    "limit": limit,
                    "cursor": cursor,
                    "email": email,
                    "externalId": external_id,
                    "status": status,
                    "courseId": course_id,
                },
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            LearnersPage,
            cursor_param="cursor",
            style="cursor",
        )

    async def offboard(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        if_match: str | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Learner:
        """Offboard a learner

        Removes a learner from the organization. A learner who hasn't started has their
        invite cancelled and the seat returned; a learner who has started keeps their
        training history and certificates. Releases the learner's `externalId`.

        Args:
            learner_id: The learner's canonical subject id (sub_… ULID).
            course_id: The course. Defaults to the organization's default course.
            if_match: The ETag the object was read with (`last_response.etag`).
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/learners/{learnerId}:offboard",
                path_params={"learnerId": learner_id},
                query={"courseId": course_id},
                headers={"if-match": if_match},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            Learner,
        )

    async def remind(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> LearnerRemindAccepted:
        """Remind a learner

        Emails the learner a reminder: the invite again if they haven't started, or a
        nudge to finish if they have.

        Args:
            learner_id: The learner's canonical subject id (sub_… ULID).
            course_id: The course. Defaults to the organization's default course.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/learners/{learnerId}:remind",
                path_params={"learnerId": learner_id},
                query={"courseId": course_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            LearnerRemindAccepted,
        )

    async def retrieve(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Learner:
        """Retrieve a learner

        Retrieves a learner's status in one course.

        Args:
            learner_id: The learner's canonical subject id (sub_… ULID).
            course_id: The course. Defaults to the organization's default course.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/learners/{learnerId}",
                path_params={"learnerId": learner_id},
                query={"courseId": course_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Learner,
        )

    async def update(
        self,
        learner_id: str,
        /,
        *,
        if_match: str,
        name: str | NotGiven = NOT_GIVEN,
        external_id: str | NotGiven | None = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Learner:
        """Update a learner

        Updates a learner's `name` or `externalId`; parameters you don't send are left
        unchanged. Send the body as `application/merge-patch+json` with the learner's
        current `ETag` in `If-Match`.

        Args:
            learner_id: The learner's canonical subject id (sub_… ULID).
            if_match: The ETag the object was read with (`last_response.etag`).
            name: The learner's full name.
            external_id: Your own id for the learner. Set it to `null` to clear it.
            course_id: The course. Defaults to the organization's default course.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "PATCH",
                "/organizations/{orgId}/learners/{learnerId}",
                path_params={"learnerId": learner_id},
                body={"name": name, "externalId": external_id},
                content_type="application/merge-patch+json",
                query={"courseId": course_id},
                headers={"if-match": if_match},
                org_scoped=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Learner,
        )

    async def upsert_by_external_id(
        self,
        external_id: str,
        /,
        *,
        email: str,
        name: str | NotGiven = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        delivery: LearnerUpsertRequestDelivery | NotGiven = NOT_GIVEN,
        seat_policy: LearnerUpsertRequestSeatPolicy | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> LearnerWriteResult:
        """Create or retrieve a learner by your id

        Makes sure a learner exists for your own id. Creates and invites the learner the
        first time, and returns them on every later call, so a sync job can replay it
        safely. Never uses a second seat.

        `created` is true when this call created the Learner (201) and false when it
        already existed (200).

        Args:
            external_id: Your id for the learner, URL-encoded.
            email: The learner's email address.
            name: The learner's full name.
            course_id: The course to invite them to. Defaults to the organization's
                default course.
            delivery: `email` (default) sends the invite email. `none` sends nothing and
                returns `joinUrl` for you to deliver.
            seat_policy: `require_available` fails with `409` when no seat is free.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_write_result(
            ApiRequest(
                "PUT",
                "/organizations/{orgId}/learners/by-external-id/{externalId}",
                path_params={"externalId": external_id},
                body={
                    "email": email,
                    "name": name,
                    "courseId": course_id,
                    "delivery": delivery,
                    "seatPolicy": seat_policy,
                },
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            LearnerWriteResult,
        )
