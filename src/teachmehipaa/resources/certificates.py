# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.

from typing import Literal, overload

import httpx

from .._core._models import (
    AsyncBinaryStream,
    BinaryResponse,
    BinaryStream,
)
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
    Certificate,
    CertificateLinks,
    CertificatesExportRequestFormat,
    CertificatesPage,
)


class Certificates(SyncAPIResource):
    @overload
    def download_pdf(
        self,
        cert_id: str,
        /,
        *,
        stream: Literal[False] = False,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> BinaryResponse: ...

    @overload
    def download_pdf(
        self,
        cert_id: str,
        /,
        *,
        stream: Literal[True],
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> BinaryStream: ...

    @overload
    def download_pdf(
        self,
        cert_id: str,
        /,
        *,
        stream: bool,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> BinaryResponse | BinaryStream: ...

    def download_pdf(
        self,
        cert_id: str,
        /,
        *,
        stream: bool = False,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> BinaryResponse | BinaryStream:
        """Download a certificate.

        Downloads the certificate as a PDF. Revoked and expired certificates are
        watermarked. Requires the `certificates:read` scope.

        Returns the file's bytes with its content type and filename, or with
        `stream=True` a stream to read them from.

        Args:
            stream: Return a stream (`BinaryStream`, or `AsyncBinaryStream` on the async
                client) as soon as the headers arrive instead of reading the whole file.
                Use it as a context manager so the connection is released.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        api_request = ApiRequest(
            "GET",
            "/organizations/{orgId}/certificates/{certId}/content",
            path_params={"certId": cert_id},
            binary_content_type="application/pdf",
            org_scoped=True,
            retry_safe=True,
            options=RequestOptions(
                max_retries=max_retries, timeout=timeout, request_id=request_id
            ),
        )
        if stream:
            return self._pipeline.request_binary_stream(api_request)
        return self._pipeline.request_binary(api_request)

    def export(
        self,
        *,
        format: CertificatesExportRequestFormat,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Export certificates.

        Exports the organization's certificate records as CSV. Requires the
        `certificates:read` scope.

        Args:
            format: The file format. Only `csv` today.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        return request_operation(
            self._pipeline,
            ApiRequest(
                "POST",
                "/organizations/{orgId}/certificates:export",
                body={"format": format},
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
            Operation,
        )

    def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        subject_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> SyncPage[Certificate]:
        """List all certificates.

        Returns a list of the organization's certificates. Pass `subjectId` to list one
        learner's.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            subject_id: Filter to one holder (canonical subject id).
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
                "/organizations/{orgId}/certificates",
                query={"limit": limit, "cursor": cursor, "subjectId": subject_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            CertificatesPage,
            cursor_param="cursor",
        )

    def retrieve(
        self,
        cert_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> Certificate:
        """Retrieve a certificate.

        Retrieves a certificate.

        Args:
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
                "/organizations/{orgId}/certificates/{certId}",
                path_params={"certId": cert_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            Certificate,
        )

    def retrieve_links(
        self,
        cert_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> CertificateLinks:
        """Retrieve certificate links.

        Retrieves the certificate's LinkedIn add-to-profile link and its public `tme.so`
        verification link. Requires the `certificates:read` scope.

        Args:
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
                "/organizations/{orgId}/certificates/{certId}/credentials",
                path_params={"certId": cert_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            CertificateLinks,
        )


class AsyncCertificates(AsyncAPIResource):
    @overload
    async def download_pdf(
        self,
        cert_id: str,
        /,
        *,
        stream: Literal[False] = False,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> BinaryResponse: ...

    @overload
    async def download_pdf(
        self,
        cert_id: str,
        /,
        *,
        stream: Literal[True],
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> AsyncBinaryStream: ...

    @overload
    async def download_pdf(
        self,
        cert_id: str,
        /,
        *,
        stream: bool,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> BinaryResponse | AsyncBinaryStream: ...

    async def download_pdf(
        self,
        cert_id: str,
        /,
        *,
        stream: bool = False,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> BinaryResponse | AsyncBinaryStream:
        """Download a certificate.

        Downloads the certificate as a PDF. Revoked and expired certificates are
        watermarked. Requires the `certificates:read` scope.

        Returns the file's bytes with its content type and filename, or with
        `stream=True` a stream to read them from.

        Args:
            stream: Return a stream (`BinaryStream`, or `AsyncBinaryStream` on the async
                client) as soon as the headers arrive instead of reading the whole file.
                Use it as a context manager so the connection is released.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        api_request = ApiRequest(
            "GET",
            "/organizations/{orgId}/certificates/{certId}/content",
            path_params={"certId": cert_id},
            binary_content_type="application/pdf",
            org_scoped=True,
            retry_safe=True,
            options=RequestOptions(
                max_retries=max_retries, timeout=timeout, request_id=request_id
            ),
        )
        if stream:
            return await self._pipeline.request_binary_stream(api_request)
        return await self._pipeline.request_binary(api_request)

    async def export(
        self,
        *,
        format: CertificatesExportRequestFormat,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> AsyncOperation:
        """Export certificates.

        Exports the organization's certificate records as CSV. Requires the
        `certificates:read` scope.

        Args:
            format: The file format. Only `csv` today.
            idempotency_key: Overrides the key generated for this call. Retries reuse
                the same key.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
            request_id: Sent as `x-request-id` on every attempt, so this call can be
                found in your logs and TeachMeHIPAA's. The API echoes it on
                `last_response` and on errors if it matches `^[A-Za-z0-9._-]{1,128}$`,
                and replaces it otherwise.
        """
        return await async_request_operation(
            self._pipeline,
            ApiRequest(
                "POST",
                "/organizations/{orgId}/certificates:export",
                body={"format": format},
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
            AsyncOperation,
        )

    async def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        subject_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[Certificate]:
        """List all certificates.

        Returns a list of the organization's certificates. Pass `subjectId` to list one
        learner's.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            subject_id: Filter to one holder (canonical subject id).
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
                "/organizations/{orgId}/certificates",
                query={"limit": limit, "cursor": cursor, "subjectId": subject_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            CertificatesPage,
            cursor_param="cursor",
        )

    async def retrieve(
        self,
        cert_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> Certificate:
        """Retrieve a certificate.

        Retrieves a certificate.

        Args:
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
                "/organizations/{orgId}/certificates/{certId}",
                path_params={"certId": cert_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            Certificate,
        )

    async def retrieve_links(
        self,
        cert_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> CertificateLinks:
        """Retrieve certificate links.

        Retrieves the certificate's LinkedIn add-to-profile link and its public `tme.so`
        verification link. Requires the `certificates:read` scope.

        Args:
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
                "/organizations/{orgId}/certificates/{certId}/credentials",
                path_params={"certId": cert_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(
                    max_retries=max_retries, timeout=timeout, request_id=request_id
                ),
            ),
            CertificateLinks,
        )
