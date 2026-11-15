# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.


import httpx

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
        )

    def retrieve(
        self,
        course_id: str,
        /,
        *,
        if_none_match: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Course:
        """Retrieve a course

        Retrieves a course from the public catalog.

        Args:
            if_none_match: An ETag the caller already holds.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return self._pipeline.request(
            ApiRequest(
                "GET",
                "/courses/{courseId}",
                path_params={"courseId": course_id},
                headers={"if-none-match": if_none_match},
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
        )

    async def retrieve(
        self,
        course_id: str,
        /,
        *,
        if_none_match: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Course:
        """Retrieve a course

        Retrieves a course from the public catalog.

        Args:
            if_none_match: An ETag the caller already holds.
            max_retries: Overrides the client's `max_retries` for this call.
            timeout: Overrides the client's `timeout` for this call, in seconds.
        """
        return await self._pipeline.request(
            ApiRequest(
                "GET",
                "/courses/{courseId}",
                path_params={"courseId": course_id},
                headers={"if-none-match": if_none_match},
                authenticated=False,
                retry_safe=True,
                options=RequestOptions(max_retries=max_retries, timeout=timeout),
            ),
            Course,
        )
