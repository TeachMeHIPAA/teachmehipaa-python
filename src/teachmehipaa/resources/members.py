# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.


import httpx

from .._core._pagination import AsyncPage, SyncPage
from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types import ListMembersRole, Member, MemberListItem, MembersPage


class Members(SyncAPIResource):
    def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        include: str | NotGiven = NOT_GIVEN,
        role: ListMembersRole | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SyncPage[MemberListItem]:
        """List all members

        Returns a list of the organization's members, its admins and learners. Pass
        `role=admin` to list only admins.

        Args:
            limit: How many objects to return, between 1 and 1000. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            include: Opt-in, comma-separated. With `enrollmentSubject`, a member whose
                `subjectId` is null carries `enrollmentSubjectId`: the subject their
                email resolves to (a never-signed-in invitee), or null when none. Use it
                only to match the member to Enrollments; it is not an address for member
                routes. With `holdsInvitation`, each learner carries `holdsInvitation`:
                whether the organization has an invitation for their email or a Seat
                bound to them. Each key is omitted when its lookup failed.
            role: Only admins (paginated).
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/members",
                query={
                    "limit": limit,
                    "cursor": cursor,
                    "include": include,
                    "role": role,
                },
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            MembersPage,
            cursor_param="cursor",
            style="cursor",
        )

    def retrieve(
        self,
        subject_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Member:
        """Retrieve a member

        Retrieves a member of the organization.

        Args:
            subject_id: The member's id.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/members/{subjectId}",
                path_params={"subjectId": subject_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Member,
        )


class AsyncMembers(AsyncAPIResource):
    async def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        include: str | NotGiven = NOT_GIVEN,
        role: ListMembersRole | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[MemberListItem]:
        """List all members

        Returns a list of the organization's members, its admins and learners. Pass
        `role=admin` to list only admins.

        Args:
            limit: How many objects to return, between 1 and 1000. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            include: Opt-in, comma-separated. With `enrollmentSubject`, a member whose
                `subjectId` is null carries `enrollmentSubjectId`: the subject their
                email resolves to (a never-signed-in invitee), or null when none. Use it
                only to match the member to Enrollments; it is not an address for member
                routes. With `holdsInvitation`, each learner carries `holdsInvitation`:
                whether the organization has an invitation for their email or a Seat
                bound to them. Each key is omitted when its lookup failed.
            role: Only admins (paginated).
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/members",
                query={
                    "limit": limit,
                    "cursor": cursor,
                    "include": include,
                    "role": role,
                },
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            MembersPage,
            cursor_param="cursor",
            style="cursor",
        )

    async def retrieve(
        self,
        subject_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Member:
        """Retrieve a member

        Retrieves a member of the organization.

        Args:
            subject_id: The member's id.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/members/{subjectId}",
                path_params={"subjectId": subject_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Member,
        )
