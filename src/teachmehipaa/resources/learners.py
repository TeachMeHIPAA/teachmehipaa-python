# Hand-written for the tracer; the generator replaces this file.
from __future__ import annotations

from .._core._request import ApiRequest
from .._core._resource import AsyncAPIResource, SyncAPIResource
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..types.learner import Learner


def _retrieve(learner_id: str, course_id: str | NotGiven) -> ApiRequest:
    return ApiRequest(
        "GET",
        "/organizations/{orgId}/learners/{learnerId}",
        path_params={"learnerId": learner_id},
        query={"courseId": course_id},
    )


class Learners(SyncAPIResource):
    def retrieve(
        self, learner_id: str, /, *, course_id: str | NotGiven = NOT_GIVEN
    ) -> Learner:
        """Retrieve a Learner's status in one Course (the Organization's
        default Course unless `course_id` is given)."""
        return self._pipeline.request(_retrieve(learner_id, course_id), Learner)


class AsyncLearners(AsyncAPIResource):
    async def retrieve(
        self, learner_id: str, /, *, course_id: str | NotGiven = NOT_GIVEN
    ) -> Learner:
        """Retrieve a Learner's status in one Course (the Organization's
        default Course unless `course_id` is given)."""
        return await self._pipeline.request(_retrieve(learner_id, course_id), Learner)
