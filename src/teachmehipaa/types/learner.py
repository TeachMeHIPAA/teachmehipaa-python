# Hand-written for the tracer; the generator replaces this file.
from __future__ import annotations

from datetime import datetime
from typing import Literal

from .._core._models import BaseModel

LearnerStatus = (
    Literal[
        "not_started",
        "invite_bounced",
        "in_progress",
        "compliant",
        "expiring_soon",
        "expired",
        "removed",
    ]
    | str
)


class LearnerCourse(BaseModel):
    course_id: str
    title: str


class LearnerCertificate(BaseModel):
    certificate_id: str
    issued_at: datetime
    expires_at: datetime
    verify_url: str | None
    pdf_url: str


class Learner(BaseModel):
    """A Member taking a Training, seen from the Organization's side."""

    learner_id: str
    email: str
    name: str | None
    external_id: str | None
    status: LearnerStatus
    course: LearnerCourse
    invited_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    due_at: datetime | None
    certificate: LearnerCertificate | None
