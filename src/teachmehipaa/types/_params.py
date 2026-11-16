# Generated from openapi/sdk-ir.json — do not edit.
# Regenerate with `uv run python scripts/generate.py`.

from collections.abc import Sequence

from typing_extensions import Required, TypedDict

from ._models import EnrollmentsBatchRequestSelectFilterFilterStatus


class EnrollmentsBatchRequestSelectEnrollmentIdsParam(TypedDict, total=False):
    enrollment_ids: Required[Sequence[str]]


class EnrollmentsBatchRequestSelectFilterFilterParam(TypedDict, total=False):
    status: EnrollmentsBatchRequestSelectFilterFilterStatus
    course_id: str
    archived: bool


class EnrollmentsBatchRequestSelectFilterParam(TypedDict, total=False):
    filter: Required[EnrollmentsBatchRequestSelectFilterFilterParam]


class ImportOptionsParam(TypedDict, total=False):
    course_id: str
    """The course to invite everyone to. Defaults to the organization's default course.
    """


class LearnerBatchUpsertRequestItemsItemParam(TypedDict, total=False):
    email: Required[str]
    name: str
    external_id: str
    course_id: str
