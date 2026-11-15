# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.


import httpx

from .._core._pagination import AsyncPage, SyncPage
from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types import (
    SeatOrder,
    SeatOrderCreated,
    SeatOrderCreateRequestPaymentParam,
    SeatOrderQuote,
    SeatOrdersPage,
)


class SeatOrders(SyncAPIResource):
    def create(
        self,
        *,
        quantity: int,
        payment: SeatOrderCreateRequestPaymentParam,
        client_reference: str | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SeatOrderCreated:
        """Create a seat order

        Buys seats at list price. Pay with a Stripe-hosted checkout, the organization's
        saved card, or an invoice when it's enabled. Send the `expectedTotal` and
        `currency` from the quote you showed the buyer: if the price changed, nothing is
        charged. Seats are granted once payment succeeds. Requires the `seats:purchase`
        or `billing:write` scope.

        Args:
            quantity: Seats to buy.
            payment: How to pay: `hosted_checkout` with a `returnUrl`,
                `saved_payment_method` with the card's `paymentMethodId`, or `invoice`.
                A `returnUrl` must be https and on your API client's allowlist.
            client_reference: Your own reference for the order.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/seat-orders",
                body={
                    "quantity": quantity,
                    "payment": payment,
                    "clientReference": client_reference,
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
            SeatOrderCreated,
        )

    def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SyncPage[SeatOrder]:
        """List all seat orders

        Returns a list of the organization's seat orders, oldest first. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/seat-orders",
                query={"limit": limit, "cursor": cursor},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            SeatOrdersPage,
            cursor_param="cursor",
            style="cursor",
        )

    def quote(
        self,
        *,
        quantity: int,
        currency: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SeatOrderQuote:
        """Quote a seat order

        Gets the list price for a number of seats in the organization's currency, before
        tax. The quote is for display and expires after 15 minutes. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
            quantity: Seats to quote.
            currency: The currency you expect to be charged in. It must match the
                organization's.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/seat-orders:quote",
                body={"quantity": quantity, "currency": currency},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            SeatOrderQuote,
        )

    def retrieve(
        self,
        seat_order_id: str,
        /,
        *,
        if_none_match: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SeatOrder:
        """Retrieve a seat order

        Retrieves a seat order, its status and the seats it granted. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
            seat_order_id: The seat order id (`so_` + ULID).
            if_none_match: An ETag the caller already holds.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/seat-orders/{seatOrderId}",
                path_params={"seatOrderId": seat_order_id},
                headers={"if-none-match": if_none_match},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            SeatOrder,
        )


class AsyncSeatOrders(AsyncAPIResource):
    async def create(
        self,
        *,
        quantity: int,
        payment: SeatOrderCreateRequestPaymentParam,
        client_reference: str | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SeatOrderCreated:
        """Create a seat order

        Buys seats at list price. Pay with a Stripe-hosted checkout, the organization's
        saved card, or an invoice when it's enabled. Send the `expectedTotal` and
        `currency` from the quote you showed the buyer: if the price changed, nothing is
        charged. Seats are granted once payment succeeds. Requires the `seats:purchase`
        or `billing:write` scope.

        Args:
            quantity: Seats to buy.
            payment: How to pay: `hosted_checkout` with a `returnUrl`,
                `saved_payment_method` with the card's `paymentMethodId`, or `invoice`.
                A `returnUrl` must be https and on your API client's allowlist.
            client_reference: Your own reference for the order.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/seat-orders",
                body={
                    "quantity": quantity,
                    "payment": payment,
                    "clientReference": client_reference,
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
            SeatOrderCreated,
        )

    async def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[SeatOrder]:
        """List all seat orders

        Returns a list of the organization's seat orders, oldest first. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/seat-orders",
                query={"limit": limit, "cursor": cursor},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            SeatOrdersPage,
            cursor_param="cursor",
            style="cursor",
        )

    async def quote(
        self,
        *,
        quantity: int,
        currency: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SeatOrderQuote:
        """Quote a seat order

        Gets the list price for a number of seats in the organization's currency, before
        tax. The quote is for display and expires after 15 minutes. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
            quantity: Seats to quote.
            currency: The currency you expect to be charged in. It must match the
                organization's.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "POST",
                "/organizations/{orgId}/seat-orders:quote",
                body={"quantity": quantity, "currency": currency},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            SeatOrderQuote,
        )

    async def retrieve(
        self,
        seat_order_id: str,
        /,
        *,
        if_none_match: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SeatOrder:
        """Retrieve a seat order

        Retrieves a seat order, its status and the seats it granted. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
            seat_order_id: The seat order id (`so_` + ULID).
            if_none_match: An ETag the caller already holds.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/seat-orders/{seatOrderId}",
                path_params={"seatOrderId": seat_order_id},
                headers={"if-none-match": if_none_match},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            SeatOrder,
        )
