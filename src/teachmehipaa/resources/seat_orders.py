# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.

from typing import overload

import httpx

from .._core._models import (
    ETagSource,
    NotModified,
)
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
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SeatOrderCreated:
        """Create a seat order.

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
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
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
                    request_id=request_id,
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
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SyncPage[SeatOrder]:
        """List all seat orders.

        Returns a list of the organization's seat orders, oldest first. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
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
                "/organizations/{orgId}/seat-orders",
                query={"limit": limit, "cursor": cursor},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            SeatOrdersPage,
            cursor_param="cursor",
        )

    def quote(
        self,
        *,
        quantity: int,
        currency: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SeatOrderQuote:
        """Quote a seat order.

        Gets the list price for a number of seats in the organization's currency, before
        tax. The quote is for display and expires after 15 minutes. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
            quantity: Seats to quote.
            currency: The currency you expect to be charged in. It must match the
                organization's.
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
                "/organizations/{orgId}/seat-orders:quote",
                body={"quantity": quantity, "currency": currency},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            SeatOrderQuote,
        )

    @overload
    def retrieve(
        self,
        seat_order_id: str,
        /,
        *,
        if_none_match: NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SeatOrder: ...

    @overload
    def retrieve(
        self,
        seat_order_id: str,
        /,
        *,
        if_none_match: ETagSource,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SeatOrder | NotModified: ...

    def retrieve(
        self,
        seat_order_id: str,
        /,
        *,
        if_none_match: ETagSource | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SeatOrder | NotModified:
        """Retrieve a seat order.

        Retrieves a seat order, its status and the seats it granted. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
            seat_order_id: The seat order id (`so_` + ULID).
            if_none_match: The ETag of the copy the caller holds, or that copy itself.
                When it is still current the API answers 304 and the method returns
                `NotModified`.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        return self._pipeline.request_conditional(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/seat-orders/{seatOrderId}",
                path_params={"seatOrderId": seat_order_id},
                if_none_match=if_none_match,
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
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
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SeatOrderCreated:
        """Create a seat order.

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
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
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
                    request_id=request_id,
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
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[SeatOrder]:
        """List all seat orders.

        Returns a list of the organization's seat orders, oldest first. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
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
                "/organizations/{orgId}/seat-orders",
                query={"limit": limit, "cursor": cursor},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            SeatOrdersPage,
            cursor_param="cursor",
        )

    async def quote(
        self,
        *,
        quantity: int,
        currency: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SeatOrderQuote:
        """Quote a seat order.

        Gets the list price for a number of seats in the organization's currency, before
        tax. The quote is for display and expires after 15 minutes. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
            quantity: Seats to quote.
            currency: The currency you expect to be charged in. It must match the
                organization's.
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
                "/organizations/{orgId}/seat-orders:quote",
                body={"quantity": quantity, "currency": currency},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            SeatOrderQuote,
        )

    @overload
    async def retrieve(
        self,
        seat_order_id: str,
        /,
        *,
        if_none_match: NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SeatOrder: ...

    @overload
    async def retrieve(
        self,
        seat_order_id: str,
        /,
        *,
        if_none_match: ETagSource,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SeatOrder | NotModified: ...

    async def retrieve(
        self,
        seat_order_id: str,
        /,
        *,
        if_none_match: ETagSource | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SeatOrder | NotModified:
        """Retrieve a seat order.

        Retrieves a seat order, its status and the seats it granted. Requires the
        `seats:purchase` or `billing:write` scope.

        Args:
            seat_order_id: The seat order id (`so_` + ULID).
            if_none_match: The ETag of the copy the caller holds, or that copy itself.
                When it is still current the API answers 304 and the method returns
                `NotModified`.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        return await self._pipeline.request_conditional(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/seat-orders/{seatOrderId}",
                path_params={"seatOrderId": seat_order_id},
                if_none_match=if_none_match,
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            SeatOrder,
        )
