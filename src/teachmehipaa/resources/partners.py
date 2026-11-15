# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.

from collections.abc import Sequence

import httpx

from .._core._pagination import AsyncPage, SyncPage
from .._core._pipeline import AsyncPipeline, SyncPipeline
from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types import (
    Partner,
    PartnerOrganization,
    PartnerOrganizationCreated,
    PartnerOrganizationCreateScopesItem,
    PartnerOrganizationsPage,
)


class PartnersOrganizations(SyncAPIResource):
    def create(
        self,
        partner_id: str,
        /,
        *,
        name: str,
        admin_email: str,
        admin_name: str | NotGiven = NOT_GIVEN,
        scopes: Sequence[PartnerOrganizationCreateScopesItem],
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> PartnerOrganizationCreated:
        """Create a customer organization.

        Creates an organization for a customer with your app already connected, and
        emails its administrator a link to sign in. The organization has no seats until
        seats are bought for it. Requires the `partner:orgs:write` scope.

        Args:
            partner_id: The partner account, `ptn_…`. Must be the partner the token was
                issued for.
            name: The organization's name.
            admin_email: The email address of the organization's administrator.
            admin_name: The administrator's full name.
            scopes: The scopes your app gets on the new organization. A subset of your
                app's scopes.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/partners/{partnerId}/organizations",
                path_params={"partnerId": partner_id},
                body={
                    "name": name,
                    "adminEmail": admin_email,
                    "adminName": admin_name,
                    "scopes": scopes,
                },
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                    request_id=request_id,
                ),
            ),
            PartnerOrganizationCreated,
        )

    def list(
        self,
        partner_id: str,
        /,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SyncPage[PartnerOrganization]:
        """List all customer organizations.

        Returns a list of the organizations you created. `grantActive` is `false` once a
        customer disconnects your app. Requires the `partner:orgs:read` scope.

        Args:
            partner_id: The partner account, `ptn_…`. Must be the partner the token was
                issued for.
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
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
                "/partners/{partnerId}/organizations",
                path_params={"partnerId": partner_id},
                query={"limit": limit, "cursor": cursor},
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            PartnerOrganizationsPage,
            cursor_param="cursor",
        )


class AsyncPartnersOrganizations(AsyncAPIResource):
    async def create(
        self,
        partner_id: str,
        /,
        *,
        name: str,
        admin_email: str,
        admin_name: str | NotGiven = NOT_GIVEN,
        scopes: Sequence[PartnerOrganizationCreateScopesItem],
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> PartnerOrganizationCreated:
        """Create a customer organization.

        Creates an organization for a customer with your app already connected, and
        emails its administrator a link to sign in. The organization has no seats until
        seats are bought for it. Requires the `partner:orgs:write` scope.

        Args:
            partner_id: The partner account, `ptn_…`. Must be the partner the token was
                issued for.
            name: The organization's name.
            admin_email: The email address of the organization's administrator.
            admin_name: The administrator's full name.
            scopes: The scopes your app gets on the new organization. A subset of your
                app's scopes.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/partners/{partnerId}/organizations",
                path_params={"partnerId": partner_id},
                body={
                    "name": name,
                    "adminEmail": admin_email,
                    "adminName": admin_name,
                    "scopes": scopes,
                },
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                    request_id=request_id,
                ),
            ),
            PartnerOrganizationCreated,
        )

    async def list(
        self,
        partner_id: str,
        /,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[PartnerOrganization]:
        """List all customer organizations.

        Returns a list of the organizations you created. `grantActive` is `false` once a
        customer disconnects your app. Requires the `partner:orgs:read` scope.

        Args:
            partner_id: The partner account, `ptn_…`. Must be the partner the token was
                issued for.
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
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
                "/partners/{partnerId}/organizations",
                path_params={"partnerId": partner_id},
                query={"limit": limit, "cursor": cursor},
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            PartnerOrganizationsPage,
            cursor_param="cursor",
        )


class Partners(SyncAPIResource):
    organizations: PartnersOrganizations

    def __init__(self, pipeline: SyncPipeline) -> None:
        super().__init__(pipeline)
        self.organizations = PartnersOrganizations(pipeline)

    def retrieve(
        self,
        partner_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> Partner:
        """Retrieve your partner account.

        Retrieves your partner account, including how many organizations you can create.
        Requires the `partner:orgs:read` scope.

        Args:
            partner_id: The partner account, `ptn_…`. Must be the partner the token was
                issued for.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        return self._pipeline.request(
            ApiRequest(
                "GET",
                "/partners/{partnerId}",
                path_params={"partnerId": partner_id},
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            Partner,
        )


class AsyncPartners(AsyncAPIResource):
    organizations: AsyncPartnersOrganizations

    def __init__(self, pipeline: AsyncPipeline) -> None:
        super().__init__(pipeline)
        self.organizations = AsyncPartnersOrganizations(pipeline)

    async def retrieve(
        self,
        partner_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> Partner:
        """Retrieve your partner account.

        Retrieves your partner account, including how many organizations you can create.
        Requires the `partner:orgs:read` scope.

        Args:
            partner_id: The partner account, `ptn_…`. Must be the partner the token was
                issued for.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        return await self._pipeline.request(
            ApiRequest(
                "GET",
                "/partners/{partnerId}",
                path_params={"partnerId": partner_id},
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            Partner,
        )
