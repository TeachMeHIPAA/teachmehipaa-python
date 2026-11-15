# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.


import httpx

from .._core._models import BinaryResponse
from .._core._pagination import AsyncPage, SyncPage
from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types import (
    Certificate,
    CertificateLinks,
    CertificatesExportRequestFormat,
    CertificatesPage,
    Operation,
)


class Certificates(SyncAPIResource):
    def download_pdf(
        self,
        cert_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> BinaryResponse:
        """Download a certificate

        Downloads the certificate as a PDF. Revoked and expired certificates are
        watermarked. Requires the `certificates:read` scope.

        Returns the file's bytes with its content type and filename.

        Args:
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_binary(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/certificates/{certId}/content",
                path_params={"certId": cert_id},
                headers={"accept": "application/pdf"},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            )
        )

    def export(
        self,
        *,
        format: CertificatesExportRequestFormat,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Export certificates

        Exports the organization's certificate records as CSV. Requires the
        `certificates:read` scope.

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
                "/organizations/{orgId}/certificates:export",
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

    def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        subject_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SyncPage[Certificate]:
        """List all certificates

        Returns a list of the organization's certificates. Pass `subjectId` to list one
        learner's.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            subject_id: Filter to one holder (canonical subject id).
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/certificates",
                query={"limit": limit, "cursor": cursor, "subjectId": subject_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
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
    ) -> Certificate:
        """Retrieve a certificate

        Retrieves a certificate.

        Args:
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/certificates/{certId}",
                path_params={"certId": cert_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
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
    ) -> CertificateLinks:
        """Retrieve certificate links

        Retrieves the certificate's LinkedIn add-to-profile link and its public `tme.so`
        verification link. Requires the `certificates:read` scope.

        Args:
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/certificates/{certId}/credentials",
                path_params={"certId": cert_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            CertificateLinks,
        )


class AsyncCertificates(AsyncAPIResource):
    async def download_pdf(
        self,
        cert_id: str,
        /,
        *,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> BinaryResponse:
        """Download a certificate

        Downloads the certificate as a PDF. Revoked and expired certificates are
        watermarked. Requires the `certificates:read` scope.

        Returns the file's bytes with its content type and filename.

        Args:
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_binary(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/certificates/{certId}/content",
                path_params={"certId": cert_id},
                headers={"accept": "application/pdf"},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            )
        )

    async def export(
        self,
        *,
        format: CertificatesExportRequestFormat,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Operation:
        """Export certificates

        Exports the organization's certificate records as CSV. Requires the
        `certificates:read` scope.

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
                "/organizations/{orgId}/certificates:export",
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

    async def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        subject_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[Certificate]:
        """List all certificates

        Returns a list of the organization's certificates. Pass `subjectId` to list one
        learner's.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            subject_id: Filter to one holder (canonical subject id).
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/certificates",
                query={"limit": limit, "cursor": cursor, "subjectId": subject_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
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
    ) -> Certificate:
        """Retrieve a certificate

        Retrieves a certificate.

        Args:
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/certificates/{certId}",
                path_params={"certId": cert_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
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
    ) -> CertificateLinks:
        """Retrieve certificate links

        Retrieves the certificate's LinkedIn add-to-profile link and its public `tme.so`
        verification link. Requires the `certificates:read` scope.

        Args:
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/certificates/{certId}/credentials",
                path_params={"certId": cert_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            CertificateLinks,
        )
