# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.


import httpx

from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types import BillingPaymentMethod, PaymentMethodPrepare, PaymentMethodSetup


class PaymentMethod(SyncAPIResource):
    def confirm(
        self,
        *,
        setup_intent_id: str,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> BillingPaymentMethod:
        """Finish saving a card

        Makes the card from a confirmed SetupIntent the organization's default for seat
        orders. Safe to repeat. Requires the `seats:purchase` or `billing:write` scope.

        Args:
            setup_intent_id: The SetupIntent you confirmed with Stripe.js.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/billing/payment-method:confirm",
                body={"setupIntentId": setup_intent_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            BillingPaymentMethod,
        )

    def delete(
        self,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> None:
        """Delete the saved card

        Removes the saved card. Seats already bought aren't affected. Requires the
        `seats:purchase` or `billing:write` scope.

        Returns `None`: the API answers 204 No Content.

        Args:
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        self._pipeline.request_empty(
            ApiRequest(
                "DELETE",
                "/organizations/{orgId}/billing/payment-method",
                org_scoped=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            )
        )

    def prepare(
        self,
        *,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> PaymentMethodPrepare:
        """Start saving a card

        Creates a Stripe SetupIntent for a card form in your own page. Confirm it with
        Stripe.js, then finish saving the card. Saving a card never charges it. Requires
        the `seats:purchase` or `billing:write` scope.

        Args:
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/billing/payment-method:prepare",
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            PaymentMethodPrepare,
        )

    def retrieve(
        self,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> BillingPaymentMethod:
        """Retrieve the saved card

        Retrieves the card seat orders charge: its brand, last four digits and expiry.
        Card numbers are never returned. Requires the `seats:purchase` or
        `billing:write` scope.

        Args:
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/billing/payment-method",
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            BillingPaymentMethod,
        )

    def setup(
        self,
        *,
        return_url: str,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> PaymentMethodSetup:
        """Save a card with Checkout

        Creates a Stripe-hosted page where the buyer saves the card that seat orders
        charge. The card becomes the organization's default. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
            return_url: Where Stripe sends the buyer afterwards. Must be https and on
                your client's allowlist.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/billing/payment-method:setup",
                body={"returnUrl": return_url},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            PaymentMethodSetup,
        )


class AsyncPaymentMethod(AsyncAPIResource):
    async def confirm(
        self,
        *,
        setup_intent_id: str,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> BillingPaymentMethod:
        """Finish saving a card

        Makes the card from a confirmed SetupIntent the organization's default for seat
        orders. Safe to repeat. Requires the `seats:purchase` or `billing:write` scope.

        Args:
            setup_intent_id: The SetupIntent you confirmed with Stripe.js.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/billing/payment-method:confirm",
                body={"setupIntentId": setup_intent_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            BillingPaymentMethod,
        )

    async def delete(
        self,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> None:
        """Delete the saved card

        Removes the saved card. Seats already bought aren't affected. Requires the
        `seats:purchase` or `billing:write` scope.

        Returns `None`: the API answers 204 No Content.

        Args:
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        await self._pipeline.request_empty(
            ApiRequest(
                "DELETE",
                "/organizations/{orgId}/billing/payment-method",
                org_scoped=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            )
        )

    async def prepare(
        self,
        *,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> PaymentMethodPrepare:
        """Start saving a card

        Creates a Stripe SetupIntent for a card form in your own page. Confirm it with
        Stripe.js, then finish saving the card. Saving a card never charges it. Requires
        the `seats:purchase` or `billing:write` scope.

        Args:
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/billing/payment-method:prepare",
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            PaymentMethodPrepare,
        )

    async def retrieve(
        self,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> BillingPaymentMethod:
        """Retrieve the saved card

        Retrieves the card seat orders charge: its brand, last four digits and expiry.
        Card numbers are never returned. Requires the `seats:purchase` or
        `billing:write` scope.

        Args:
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/billing/payment-method",
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            BillingPaymentMethod,
        )

    async def setup(
        self,
        *,
        return_url: str,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> PaymentMethodSetup:
        """Save a card with Checkout

        Creates a Stripe-hosted page where the buyer saves the card that seat orders
        charge. The card becomes the organization's default. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
            return_url: Where Stripe sends the buyer afterwards. Must be https and on
                your client's allowlist.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/billing/payment-method:setup",
                body={"returnUrl": return_url},
                org_scoped=True,
                retry_safe=True,
                idempotency_key_required=True,
                options=RequestOptions(
                    max_retries=max_retries,
                    timeout=timeout,
                    idempotency_key=idempotency_key,
                ),
            ),
            PaymentMethodSetup,
        )
