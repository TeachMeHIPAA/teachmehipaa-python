# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.


import httpx

from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types import ComplianceSummary


class Compliance(SyncAPIResource):
    def retrieve(
        self,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> ComplianceSummary:
        """Retrieve the compliance summary

        Counts the organization's learners in one course by status. Removed learners
        aren't counted.

        Args:
            course_id: The course. Defaults to the organization's default course.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/compliance",
                query={"courseId": course_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            ComplianceSummary,
        )


class AsyncCompliance(AsyncAPIResource):
    async def retrieve(
        self,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> ComplianceSummary:
        """Retrieve the compliance summary

        Counts the organization's learners in one course by status. Removed learners
        aren't counted.

        Args:
            course_id: The course. Defaults to the organization's default course.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "GET",
                "/organizations/{orgId}/compliance",
                query={"courseId": course_id},
                org_scoped=True,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            ComplianceSummary,
        )
