# Hand-written for the tracer; the generator replaces this file.
from __future__ import annotations

import httpx

from .._core._request import ApiRequest, RequestOptions
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types.learner import Learner, LearnerLaunchLink, LearnerRemindAccepted

_LEARNER = "/organizations/{orgId}/learners/{learnerId}"


def _retrieve(
    learner_id: str, course_id: str | NotGiven, options: RequestOptions
) -> ApiRequest:
    return ApiRequest(
        "GET",
        _LEARNER,
        path_params={"learnerId": learner_id},
        query={"courseId": course_id},
        retry_safe=True,
        options=options,
    )


def _update(
    learner_id: str,
    if_match: str,
    name: str | NotGiven,
    external_id: str | NotGiven | None,
    course_id: str | NotGiven,
    options: RequestOptions,
) -> ApiRequest:
    return ApiRequest(
        "PATCH",
        _LEARNER,
        path_params={"learnerId": learner_id},
        query={"courseId": course_id},
        headers={"if-match": if_match},
        body={"name": name, "externalId": external_id},
        content_type="application/merge-patch+json",
        options=options,
    )


def _remind(
    learner_id: str, course_id: str | NotGiven, options: RequestOptions
) -> ApiRequest:
    return ApiRequest(
        "POST",
        f"{_LEARNER}:remind",
        path_params={"learnerId": learner_id},
        query={"courseId": course_id},
        retry_safe=True,
        idempotency_key_required=True,
        options=options,
    )


def _create_launch_link(
    learner_id: str, course_id: str | NotGiven, options: RequestOptions
) -> ApiRequest:
    return ApiRequest(
        "POST",
        f"{_LEARNER}:createLaunchLink",
        path_params={"learnerId": learner_id},
        query={"courseId": course_id},
        retry_safe=True,
        options=options,
    )


class Learners(SyncAPIResource):
    def retrieve(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Learner:
        """Retrieve a Learner's status in one Course (the Organization's
        default Course unless `course_id` is given)."""
        options = RequestOptions(max_retries=max_retries, timeout=timeout)
        return self._pipeline.request(
            _retrieve(learner_id, course_id, options), Learner
        )

    def update(
        self,
        learner_id: str,
        /,
        *,
        if_match: str,
        name: str | NotGiven = NOT_GIVEN,
        external_id: str | NotGiven | None = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Learner:
        """Update a Learner's name or External ID. Pass `external_id=None` to
        clear it. `if_match` is the ETag the Learner was read with."""
        options = RequestOptions(max_retries=max_retries, timeout=timeout)
        return self._pipeline.request(
            _update(learner_id, if_match, name, external_id, course_id, options),
            Learner,
        )

    def remind(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> LearnerRemindAccepted:
        """Send a Learner a reminder to finish their Training."""
        options = RequestOptions(
            max_retries=max_retries, timeout=timeout, idempotency_key=idempotency_key
        )
        return self._pipeline.request(
            _remind(learner_id, course_id, options), LearnerRemindAccepted
        )

    def create_launch_link(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> LearnerLaunchLink:
        """Create a single-use Launch link that signs the Learner straight
        into their Training."""
        options = RequestOptions(max_retries=max_retries, timeout=timeout)
        return self._pipeline.request(
            _create_launch_link(learner_id, course_id, options), LearnerLaunchLink
        )


class AsyncLearners(AsyncAPIResource):
    async def retrieve(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Learner:
        """Retrieve a Learner's status in one Course (the Organization's
        default Course unless `course_id` is given)."""
        options = RequestOptions(max_retries=max_retries, timeout=timeout)
        return await self._pipeline.request(
            _retrieve(learner_id, course_id, options), Learner
        )

    async def update(
        self,
        learner_id: str,
        /,
        *,
        if_match: str,
        name: str | NotGiven = NOT_GIVEN,
        external_id: str | NotGiven | None = NOT_GIVEN,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> Learner:
        """Update a Learner's name or External ID. Pass `external_id=None` to
        clear it. `if_match` is the ETag the Learner was read with."""
        options = RequestOptions(max_retries=max_retries, timeout=timeout)
        return await self._pipeline.request(
            _update(learner_id, if_match, name, external_id, course_id, options),
            Learner,
        )

    async def remind(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        idempotency_key: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> LearnerRemindAccepted:
        """Send a Learner a reminder to finish their Training."""
        options = RequestOptions(
            max_retries=max_retries, timeout=timeout, idempotency_key=idempotency_key
        )
        return await self._pipeline.request(
            _remind(learner_id, course_id, options), LearnerRemindAccepted
        )

    async def create_launch_link(
        self,
        learner_id: str,
        /,
        *,
        course_id: str | NotGiven = NOT_GIVEN,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
    ) -> LearnerLaunchLink:
        """Create a single-use Launch link that signs the Learner straight
        into their Training."""
        options = RequestOptions(max_retries=max_retries, timeout=timeout)
        return await self._pipeline.request(
            _create_launch_link(learner_id, course_id, options), LearnerLaunchLink
        )
