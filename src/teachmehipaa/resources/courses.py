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
from ..types import Course, CoursesPage


class Courses(SyncAPIResource):
    def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> SyncPage[Course]:
        """List all courses

        Returns a list of the courses in the public catalog. Needs no access token.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/courses",
                query={"limit": limit, "cursor": cursor},
                authenticated=False,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            CoursesPage,
            cursor_param="cursor",
            style="cursor",
        )

    @overload
    def retrieve(
        self,
        course_id: str,
        /,
        *,
        if_none_match: NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Course: ...

    @overload
    def retrieve(
        self,
        course_id: str,
        /,
        *,
        if_none_match: ETagSource,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Course | NotModified: ...

    def retrieve(
        self,
        course_id: str,
        /,
        *,
        if_none_match: ETagSource | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Course | NotModified:
        """Retrieve a course

        Retrieves a course from the public catalog.

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
                "/courses/{courseId}",
                path_params={"courseId": course_id},
                if_none_match=if_none_match,
                authenticated=False,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Course,
        )


class AsyncCourses(AsyncAPIResource):
    async def list(
        self,
        *,
        limit: int | NotGiven = NOT_GIVEN,
        cursor: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> AsyncPage[Course]:
        """List all courses

        Returns a list of the courses in the public catalog. Needs no access token.

        Args:
            limit: How many objects to return, between 1 and 100. Defaults to 20.
            cursor: The `nextCursor` from the previous page.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request_page(
            ApiRequest(
                "GET",
                "/courses",
                query={"limit": limit, "cursor": cursor},
                authenticated=False,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            CoursesPage,
            cursor_param="cursor",
            style="cursor",
        )

    @overload
    async def retrieve(
        self,
        course_id: str,
        /,
        *,
        if_none_match: NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Course: ...

    @overload
    async def retrieve(
        self,
        course_id: str,
        /,
        *,
        if_none_match: ETagSource,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Course | NotModified: ...

    async def retrieve(
        self,
        course_id: str,
        /,
        *,
        if_none_match: ETagSource | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Course | NotModified:
        """Retrieve a course

        Retrieves a course from the public catalog.

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
                "/courses/{courseId}",
                path_params={"courseId": course_id},
                if_none_match=if_none_match,
                authenticated=False,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Course,
        )
