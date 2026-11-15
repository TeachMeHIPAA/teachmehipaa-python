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
    WebhookDeliveryResult,
    async_request_operation,
    request_operation,
)
from ..types import (
    EventType,
    WebhookSubscription,
    WebhookSubscriptionCreated,
    WebhookSubscriptionsPage,
)


class WebhookSubscriptions(SyncAPIResource):
    def create(
        self,
        *,
        endpoint_url: str,
        event_types: Sequence[EventType],
        description: str | NotGiven = NOT_GIVEN,
        seats_low_threshold: int | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> WebhookSubscriptionCreated:
        """Create a webhook subscription

        Subscribes an HTTPS endpoint to event types and creates its signing secret.
        Requires the `webhooks:manage` or `org:admin` scope.

        Args:
            endpoint_url: The HTTPS URL to deliver events to.
            event_types: The event types to deliver.
            description: A description for your own reference.
            seats_low_threshold: Send `seats.low` when available seats drop to this
                number. Defaults to 5.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/webhook-subscriptions",
                body={
                    "endpointUrl": endpoint_url,
                    "eventTypes": event_types,
                    "description": description,
                    "seatsLowThreshold": seats_low_threshold,
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
            WebhookSubscriptionCreated,
        )

    def delete(
        self,
        subscription_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> None:
        """Delete a webhook subscription

        Deletes a webhook subscription and its signing secret. Requires the
        `webhooks:manage` or `org:admin` scope.

        Returns `None`: the API answers 204 No Content.

        Args:
            subscription_id: The webhook subscription id.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        self._pipeline.request_empty(
            ApiRequest(
                "DELETE",
                "/organizations/{orgId}/webhook-subscriptions/{subscriptionId}",
                path_params={"subscriptionId": subscription_id},
                org_scoped=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            )
        )

    def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SyncPage[WebhookSubscription]:
        """List all webhook subscriptions

        Returns a list of the organization's webhook subscriptions. Signing secrets are
        never returned. Requires the `webhooks:manage` or `org:admin` scope.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/webhook-subscriptions",
                query={"limit": limit, "cursor": cursor},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            WebhookSubscriptionsPage,
            cursor_param="cursor",
            style="cursor",
        )

    def redrive(
        self,
        subscription_id: str,
        /,
        *,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation[WebhookDeliveryResult]:
        """Retry failed deliveries

        Delivers the subscription's failed events again. Requires the `webhooks:manage`
        or `org:admin` scope.

        Args:
            subscription_id: The webhook subscription id.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return request_operation(
            self._pipeline,
            ApiRequest(
                "POST",
                "/organizations/{orgId}/webhook-subscriptions/{subscriptionId}:redrive",
                path_params={"subscriptionId": subscription_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            Operation[WebhookDeliveryResult],
        )

    def retrieve(
        self,
        subscription_id: str,
        /,
        *,
        if_none_match: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> WebhookSubscription:
        """Retrieve a webhook subscription

        Retrieves a webhook subscription. Requires the `webhooks:manage` or `org:admin`
        scope.

        Args:
            subscription_id: The webhook subscription id.
            if_none_match: An ETag the caller already holds.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/webhook-subscriptions/{subscriptionId}",
                path_params={"subscriptionId": subscription_id},
                headers={"if-none-match": if_none_match},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            WebhookSubscription,
        )

    def test(
        self,
        subscription_id: str,
        /,
        *,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation[WebhookDeliveryResult]:
        """Send a test event

        Sends a signed test delivery to the subscription's endpoint, so you can check
        your verifier. Requires the `webhooks:manage` or `org:admin` scope.

        Args:
            subscription_id: The webhook subscription id.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return request_operation(
            self._pipeline,
            ApiRequest(
                "POST",
                "/organizations/{orgId}/webhook-subscriptions/{subscriptionId}:test",
                path_params={"subscriptionId": subscription_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            Operation[WebhookDeliveryResult],
        )

    def update(
        self,
        subscription_id: str,
        /,
        *,
        if_match: str,
        endpoint_url: str | NotGiven = NOT_GIVEN,
        event_types: Sequence[EventType] | NotGiven = NOT_GIVEN,
        enabled: bool | NotGiven = NOT_GIVEN,
        description: str | NotGiven | None = NOT_GIVEN,
        seats_low_threshold: int | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> WebhookSubscription:
        """Update a webhook subscription

        Updates a webhook subscription; parameters you don't send are left unchanged.
        Send its current `ETag` in `If-Match`. The signing secret doesn't change.
        Requires the `webhooks:manage` or `org:admin` scope.

        Args:
            subscription_id: The webhook subscription id.
            if_match: The ETag the object was read with (`last_response.etag`).
            endpoint_url: The HTTPS URL to deliver events to.
            event_types: The event types to deliver.
            enabled: Turn deliveries on or off.
            description: A description for your own reference.
            seats_low_threshold: Send `seats.low` when available seats drop to this
                number.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "PATCH",
                "/organizations/{orgId}/webhook-subscriptions/{subscriptionId}",
                path_params={"subscriptionId": subscription_id},
                body={
                    "endpointUrl": endpoint_url,
                    "eventTypes": event_types,
                    "enabled": enabled,
                    "description": description,
                    "seatsLowThreshold": seats_low_threshold,
                },
                content_type="application/merge-patch+json",
                headers={"if-match": if_match},
                org_scoped=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            WebhookSubscription,
        )


class AsyncWebhookSubscriptions(AsyncAPIResource):
    async def create(
        self,
        *,
        endpoint_url: str,
        event_types: Sequence[EventType],
        description: str | NotGiven = NOT_GIVEN,
        seats_low_threshold: int | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> WebhookSubscriptionCreated:
        """Create a webhook subscription

        Subscribes an HTTPS endpoint to event types and creates its signing secret.
        Requires the `webhooks:manage` or `org:admin` scope.

        Args:
            endpoint_url: The HTTPS URL to deliver events to.
            event_types: The event types to deliver.
            description: A description for your own reference.
            seats_low_threshold: Send `seats.low` when available seats drop to this
                number. Defaults to 5.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/webhook-subscriptions",
                body={
                    "endpointUrl": endpoint_url,
                    "eventTypes": event_types,
                    "description": description,
                    "seatsLowThreshold": seats_low_threshold,
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
            WebhookSubscriptionCreated,
        )

    async def delete(
        self,
        subscription_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> None:
        """Delete a webhook subscription

        Deletes a webhook subscription and its signing secret. Requires the
        `webhooks:manage` or `org:admin` scope.

        Returns `None`: the API answers 204 No Content.

        Args:
            subscription_id: The webhook subscription id.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        await self._pipeline.request_empty(
            ApiRequest(
                "DELETE",
                "/organizations/{orgId}/webhook-subscriptions/{subscriptionId}",
                path_params={"subscriptionId": subscription_id},
                org_scoped=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            )
        )

    async def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[WebhookSubscription]:
        """List all webhook subscriptions

        Returns a list of the organization's webhook subscriptions. Signing secrets are
        never returned. Requires the `webhooks:manage` or `org:admin` scope.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/webhook-subscriptions",
                query={"limit": limit, "cursor": cursor},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            WebhookSubscriptionsPage,
            cursor_param="cursor",
            style="cursor",
        )

    async def redrive(
        self,
        subscription_id: str,
        /,
        *,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncOperation[WebhookDeliveryResult]:
        """Retry failed deliveries

        Delivers the subscription's failed events again. Requires the `webhooks:manage`
        or `org:admin` scope.

        Args:
            subscription_id: The webhook subscription id.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await async_request_operation(
            self._pipeline,
            ApiRequest(
                "POST",
                "/organizations/{orgId}/webhook-subscriptions/{subscriptionId}:redrive",
                path_params={"subscriptionId": subscription_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            AsyncOperation[WebhookDeliveryResult],
        )

    async def retrieve(
        self,
        subscription_id: str,
        /,
        *,
        if_none_match: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> WebhookSubscription:
        """Retrieve a webhook subscription

        Retrieves a webhook subscription. Requires the `webhooks:manage` or `org:admin`
        scope.

        Args:
            subscription_id: The webhook subscription id.
            if_none_match: An ETag the caller already holds.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/webhook-subscriptions/{subscriptionId}",
                path_params={"subscriptionId": subscription_id},
                headers={"if-none-match": if_none_match},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            WebhookSubscription,
        )

    async def test(
        self,
        subscription_id: str,
        /,
        *,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncOperation[WebhookDeliveryResult]:
        """Send a test event

        Sends a signed test delivery to the subscription's endpoint, so you can check
        your verifier. Requires the `webhooks:manage` or `org:admin` scope.

        Args:
            subscription_id: The webhook subscription id.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await async_request_operation(
            self._pipeline,
            ApiRequest(
                "POST",
                "/organizations/{orgId}/webhook-subscriptions/{subscriptionId}:test",
                path_params={"subscriptionId": subscription_id},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            AsyncOperation[WebhookDeliveryResult],
        )

    async def update(
        self,
        subscription_id: str,
        /,
        *,
        if_match: str,
        endpoint_url: str | NotGiven = NOT_GIVEN,
        event_types: Sequence[EventType] | NotGiven = NOT_GIVEN,
        enabled: bool | NotGiven = NOT_GIVEN,
        description: str | NotGiven | None = NOT_GIVEN,
        seats_low_threshold: int | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> WebhookSubscription:
        """Update a webhook subscription

        Updates a webhook subscription; parameters you don't send are left unchanged.
        Send its current `ETag` in `If-Match`. The signing secret doesn't change.
        Requires the `webhooks:manage` or `org:admin` scope.

        Args:
            subscription_id: The webhook subscription id.
            if_match: The ETag the object was read with (`last_response.etag`).
            endpoint_url: The HTTPS URL to deliver events to.
            event_types: The event types to deliver.
            enabled: Turn deliveries on or off.
            description: A description for your own reference.
            seats_low_threshold: Send `seats.low` when available seats drop to this
                number.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "PATCH",
                "/organizations/{orgId}/webhook-subscriptions/{subscriptionId}",
                path_params={"subscriptionId": subscription_id},
                body={
                    "endpointUrl": endpoint_url,
                    "eventTypes": event_types,
                    "enabled": enabled,
                    "description": description,
                    "seatsLowThreshold": seats_low_threshold,
                },
                content_type="application/merge-patch+json",
                headers={"if-match": if_match},
                org_scoped=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            WebhookSubscription,
        )
