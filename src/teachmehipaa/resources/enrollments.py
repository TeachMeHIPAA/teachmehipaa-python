# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.

from typing import overload

import httpx
from pydantic import TypeAdapter

from .._core._files import FileInput
from .._core._models import (
    ETagSource,
    NotModified,
)
from .._core._pagination import AsyncPage, SyncPage
from .._core._request import ApiRequest, RequestOptions, with_fixed
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types import (
    CancelEnrollmentResponse,
    Enrollment,
    EnrollmentActionAccepted,
    EnrollmentsBatchRequestOperation,
    EnrollmentsBatchRequestSelectEnrollmentIdsParam,
    EnrollmentsBatchRequestSelectFilterParam,
    EnrollmentsBatchResults,
    EnrollmentsExportRequestFormat,
    EnrollmentsListPage,
    ImportOptionsParam,
    ImportPreview,
    ListEnrollmentsArchived,
    ListEnrollmentsInclude,
    ListEnrollmentsStatus,
    Operation,
    OrgEnrollmentListItem,
)

_CANCEL_ENROLLMENT_RESPONSE: TypeAdapter[CancelEnrollmentResponse] = TypeAdapter(
    CancelEnrollmentResponse
)


class Enrollments(SyncAPIResource):
    def batch(
        self,
        *,
        operation: EnrollmentsBatchRequestOperation,
        select: EnrollmentsBatchRequestSelectEnrollmentIdsParam,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> EnrollmentsBatchResults:
        """Update many enrollments

        Reminds, resends, cancels, renews, archives or unarchives up to 500 enrollments
        in one request, chosen by id or by filter. Each enrollment succeeds or fails on
        its own. Requires the `enrollments:write` scope.

        Args:
            operation: What to do to each enrollment: `remind`, `resendInvite`,
                `cancel`, `recertify`, `archive` or `unarchive`.
            select: The enrollments to act on: a list of `enrollmentIds` (up to 500), or
                a `filter`.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments:batch",
                body={"operation": operation, "select": select},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            EnrollmentsBatchResults,
        )

    def batch_by_filter(
        self,
        *,
        operation: EnrollmentsBatchRequestOperation,
        select: EnrollmentsBatchRequestSelectFilterParam,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Update many enrollments

        Reminds, resends, cancels, renews, archives or unarchives up to 500 enrollments
        in one request, chosen by id or by filter. Each enrollment succeeds or fails on
        its own. Requires the `enrollments:write` scope.

        Args:
            operation: What to do to each enrollment: `remind`, `resendInvite`,
                `cancel`, `recertify`, `archive` or `unarchive`.
            select: The enrollments to act on: a list of `enrollmentIds` (up to 500), or
                a `filter`.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments:batch",
                body={"operation": operation, "select": select},
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

    def cancel(
        self,
        enrollment_id: str,
        /,
        *,
        refund: bool | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> CancelEnrollmentResponse:
        """Cancel an enrollment

        Cancels an invite that hasn't been accepted yet and returns its seat to the
        pool. With `refund: true`, refunds the seat to the card that paid for it
        instead. The enrollment remains, with status `CANCELLED`. Requires the
        `enrollments:write` scope.

        Args:
            refund: Refund the seat to the card that paid for it instead of returning it
                to the pool. Defaults to `false`.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_union(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments/{enrollmentId}:cancel",
                path_params={"enrollmentId": enrollment_id},
                body={"refund": refund},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            _CANCEL_ENROLLMENT_RESPONSE,
        )

    def create(
        self,
        *,
        email: str,
        name: str | NotGiven = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Enrollment:
        """Create an enrollment

        Invites a person to a course, creating their profile if needed, and uses one
        seat. The course defaults to `hipaa`. Requires the `enrollments:write` scope.

        Args:
            email: The learner's email address.
            name: The learner's full name.
            course_id: The course to invite them to. Defaults to `hipaa`.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments",
                body={"email": email, "name": name, "courseId": course_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            Enrollment,
        )

    def export(
        self,
        *,
        format: EnrollmentsExportRequestFormat,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Export enrollments

        Exports the organization's enrollments as CSV. Requires the `enrollments:read`
        scope.

        Args:
            format: The file format. Only `csv` today.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments:export",
                body={"format": format},
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

    def import_(
        self,
        *,
        file: FileInput,
        options: ImportOptionsParam | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Import learners from CSV

        Invites everyone in a CSV file with an `email` column (and optional `name` and
        `courseId`). Send `validateOnly: true` first to preview the file without
        inviting anyone. Up to 500 rows. Requires the `enrollments:write` scope.

        Args:
            file: UTF-8 CSV (RFC 4180: quoted fields, `""` escapes, CRLF/LF). Header row
                required.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments:import",
                body={
                    "file": file,
                    "options": with_fixed(options, {"validate_only": False}),
                },
                content_type="multipart/form-data",
                binary_parts={"file": "text/csv"},
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
        status: ListEnrollmentsStatus | NotGiven = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        archived: ListEnrollmentsArchived | NotGiven = NOT_GIVEN,
        include: ListEnrollmentsInclude | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SyncPage[OrgEnrollmentListItem]:
        """List all enrollments

        Returns a list of the organization's enrollments. Filter by `status`, `courseId`
        or `archived`. Requires the `enrollments:read` scope.

        Args:
            limit: How many objects to return, between 1 and 1000. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            status: Filter on the derived effectiveStatus.
            include: Opt-in enrichment. With `priorCertificate`, an item carries
                `priorCertificate` (object, or null when the server confirmed there is
                none). The key is omitted on an item whose answer is unknown, and on
                every item of the page if the certificate lookup failed; clients must
                treat a missing key as unknown, never as null.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/enrollments",
                query={
                    "limit": limit,
                    "cursor": cursor,
                    "status": status,
                    "courseId": course_id,
                    "archived": archived,
                    "include": include,
                },
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            EnrollmentsListPage,
            cursor_param="cursor",
            style="cursor",
        )

    def preview_import(
        self,
        *,
        file: FileInput,
        options: ImportOptionsParam | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> ImportPreview:
        """Import learners from CSV

        Invites everyone in a CSV file with an `email` column (and optional `name` and
        `courseId`). Send `validateOnly: true` first to preview the file without
        inviting anyone. Up to 500 rows. Requires the `enrollments:write` scope.

        Args:
            file: UTF-8 CSV (RFC 4180: quoted fields, `""` escapes, CRLF/LF). Header row
                required.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments:import",
                body={
                    "file": file,
                    "options": with_fixed(options, {"validate_only": True}),
                },
                content_type="multipart/form-data",
                binary_parts={"file": "text/csv"},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            ImportPreview,
        )

    def remind(
        self,
        enrollment_id: str,
        /,
        *,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> EnrollmentActionAccepted:
        """Remind an enrollment

        Emails the learner again: the invitation if they haven't joined, or a reminder
        linking to the training if they have. Requires the `enrollments:write` scope.

        Args:
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments/{enrollmentId}:remind",
                path_params={"enrollmentId": enrollment_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            EnrollmentActionAccepted,
        )

    def renew(
        self,
        enrollment_id: str,
        /,
        *,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Enrollment:
        """Renew an enrollment

        Starts the next certification cycle for a certified learner and invites them
        again, using one seat. Retrying never uses a second seat. Requires the
        `enrollments:write` scope.

        Args:
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments/{enrollmentId}:renew",
                path_params={"enrollmentId": enrollment_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            Enrollment,
        )

    def resend_invite(
        self,
        enrollment_id: str,
        /,
        *,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> EnrollmentActionAccepted:
        """Resend an invite

        Sends a pending invite again, within the same cycle. To invite a certified
        learner again, renew the enrollment. Requires the `enrollments:write` scope.

        Args:
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments/{enrollmentId}:resendInvite",
                path_params={"enrollmentId": enrollment_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            EnrollmentActionAccepted,
        )

    @overload
    def retrieve(
        self,
        enrollment_id: str,
        /,
        *,
        if_none_match: NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Enrollment: ...

    @overload
    def retrieve(
        self,
        enrollment_id: str,
        /,
        *,
        if_none_match: ETagSource,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Enrollment | NotModified: ...

    def retrieve(
        self,
        enrollment_id: str,
        /,
        *,
        if_none_match: ETagSource | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Enrollment | NotModified:
        """Retrieve an enrollment

        Retrieves an enrollment. Requires the `enrollments:read` scope.

        Args:
            if_none_match: The ETag of the copy the caller holds, or that copy itself.
                When it is still current the API answers 304 and the method returns
                `NotModified`.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_conditional(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/enrollments/{enrollmentId}",
                path_params={"enrollmentId": enrollment_id},
                if_none_match=if_none_match,
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Enrollment,
        )


class AsyncEnrollments(AsyncAPIResource):
    async def batch(
        self,
        *,
        operation: EnrollmentsBatchRequestOperation,
        select: EnrollmentsBatchRequestSelectEnrollmentIdsParam,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> EnrollmentsBatchResults:
        """Update many enrollments

        Reminds, resends, cancels, renews, archives or unarchives up to 500 enrollments
        in one request, chosen by id or by filter. Each enrollment succeeds or fails on
        its own. Requires the `enrollments:write` scope.

        Args:
            operation: What to do to each enrollment: `remind`, `resendInvite`,
                `cancel`, `recertify`, `archive` or `unarchive`.
            select: The enrollments to act on: a list of `enrollmentIds` (up to 500), or
                a `filter`.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments:batch",
                body={"operation": operation, "select": select},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            EnrollmentsBatchResults,
        )

    async def batch_by_filter(
        self,
        *,
        operation: EnrollmentsBatchRequestOperation,
        select: EnrollmentsBatchRequestSelectFilterParam,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Update many enrollments

        Reminds, resends, cancels, renews, archives or unarchives up to 500 enrollments
        in one request, chosen by id or by filter. Each enrollment succeeds or fails on
        its own. Requires the `enrollments:write` scope.

        Args:
            operation: What to do to each enrollment: `remind`, `resendInvite`,
                `cancel`, `recertify`, `archive` or `unarchive`.
            select: The enrollments to act on: a list of `enrollmentIds` (up to 500), or
                a `filter`.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments:batch",
                body={"operation": operation, "select": select},
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

    async def cancel(
        self,
        enrollment_id: str,
        /,
        *,
        refund: bool | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> CancelEnrollmentResponse:
        """Cancel an enrollment

        Cancels an invite that hasn't been accepted yet and returns its seat to the
        pool. With `refund: true`, refunds the seat to the card that paid for it
        instead. The enrollment remains, with status `CANCELLED`. Requires the
        `enrollments:write` scope.

        Args:
            refund: Refund the seat to the card that paid for it instead of returning it
                to the pool. Defaults to `false`.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_union(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments/{enrollmentId}:cancel",
                path_params={"enrollmentId": enrollment_id},
                body={"refund": refund},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            _CANCEL_ENROLLMENT_RESPONSE,
        )

    async def create(
        self,
        *,
        email: str,
        name: str | NotGiven = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Enrollment:
        """Create an enrollment

        Invites a person to a course, creating their profile if needed, and uses one
        seat. The course defaults to `hipaa`. Requires the `enrollments:write` scope.

        Args:
            email: The learner's email address.
            name: The learner's full name.
            course_id: The course to invite them to. Defaults to `hipaa`.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments",
                body={"email": email, "name": name, "courseId": course_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            Enrollment,
        )

    async def export(
        self,
        *,
        format: EnrollmentsExportRequestFormat,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Export enrollments

        Exports the organization's enrollments as CSV. Requires the `enrollments:read`
        scope.

        Args:
            format: The file format. Only `csv` today.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments:export",
                body={"format": format},
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

    async def import_(
        self,
        *,
        file: FileInput,
        options: ImportOptionsParam | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Import learners from CSV

        Invites everyone in a CSV file with an `email` column (and optional `name` and
        `courseId`). Send `validateOnly: true` first to preview the file without
        inviting anyone. Up to 500 rows. Requires the `enrollments:write` scope.

        Args:
            file: UTF-8 CSV (RFC 4180: quoted fields, `""` escapes, CRLF/LF). Header row
                required.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments:import",
                body={
                    "file": file,
                    "options": with_fixed(options, {"validate_only": False}),
                },
                content_type="multipart/form-data",
                binary_parts={"file": "text/csv"},
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

    async def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        status: ListEnrollmentsStatus | NotGiven = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        archived: ListEnrollmentsArchived | NotGiven = NOT_GIVEN,
        include: ListEnrollmentsInclude | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[OrgEnrollmentListItem]:
        """List all enrollments

        Returns a list of the organization's enrollments. Filter by `status`, `courseId`
        or `archived`. Requires the `enrollments:read` scope.

        Args:
            limit: How many objects to return, between 1 and 1000. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            status: Filter on the derived effectiveStatus.
            include: Opt-in enrichment. With `priorCertificate`, an item carries
                `priorCertificate` (object, or null when the server confirmed there is
                none). The key is omitted on an item whose answer is unknown, and on
                every item of the page if the certificate lookup failed; clients must
                treat a missing key as unknown, never as null.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/enrollments",
                query={
                    "limit": limit,
                    "cursor": cursor,
                    "status": status,
                    "courseId": course_id,
                    "archived": archived,
                    "include": include,
                },
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            EnrollmentsListPage,
            cursor_param="cursor",
            style="cursor",
        )

    async def preview_import(
        self,
        *,
        file: FileInput,
        options: ImportOptionsParam | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> ImportPreview:
        """Import learners from CSV

        Invites everyone in a CSV file with an `email` column (and optional `name` and
        `courseId`). Send `validateOnly: true` first to preview the file without
        inviting anyone. Up to 500 rows. Requires the `enrollments:write` scope.

        Args:
            file: UTF-8 CSV (RFC 4180: quoted fields, `""` escapes, CRLF/LF). Header row
                required.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments:import",
                body={
                    "file": file,
                    "options": with_fixed(options, {"validate_only": True}),
                },
                content_type="multipart/form-data",
                binary_parts={"file": "text/csv"},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            ImportPreview,
        )

    async def remind(
        self,
        enrollment_id: str,
        /,
        *,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> EnrollmentActionAccepted:
        """Remind an enrollment

        Emails the learner again: the invitation if they haven't joined, or a reminder
        linking to the training if they have. Requires the `enrollments:write` scope.

        Args:
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments/{enrollmentId}:remind",
                path_params={"enrollmentId": enrollment_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            EnrollmentActionAccepted,
        )

    async def renew(
        self,
        enrollment_id: str,
        /,
        *,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Enrollment:
        """Renew an enrollment

        Starts the next certification cycle for a certified learner and invites them
        again, using one seat. Retrying never uses a second seat. Requires the
        `enrollments:write` scope.

        Args:
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments/{enrollmentId}:renew",
                path_params={"enrollmentId": enrollment_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            Enrollment,
        )

    async def resend_invite(
        self,
        enrollment_id: str,
        /,
        *,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> EnrollmentActionAccepted:
        """Resend an invite

        Sends a pending invite again, within the same cycle. To invite a certified
        learner again, renew the enrollment. Requires the `enrollments:write` scope.

        Args:
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/enrollments/{enrollmentId}:resendInvite",
                path_params={"enrollmentId": enrollment_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            EnrollmentActionAccepted,
        )

    @overload
    async def retrieve(
        self,
        enrollment_id: str,
        /,
        *,
        if_none_match: NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Enrollment: ...

    @overload
    async def retrieve(
        self,
        enrollment_id: str,
        /,
        *,
        if_none_match: ETagSource,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Enrollment | NotModified: ...

    async def retrieve(
        self,
        enrollment_id: str,
        /,
        *,
        if_none_match: ETagSource | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Enrollment | NotModified:
        """Retrieve an enrollment

        Retrieves an enrollment. Requires the `enrollments:read` scope.

        Args:
            if_none_match: The ETag of the copy the caller holds, or that copy itself.
                When it is still current the API answers 304 and the method returns
                `NotModified`.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_conditional(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/enrollments/{enrollmentId}",
                path_params={"enrollmentId": enrollment_id},
                if_none_match=if_none_match,
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Enrollment,
        )
