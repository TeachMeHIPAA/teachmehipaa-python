# Hand-written for the tracer; the generator replaces this file. It attaches
# every top-level resource to the clients.
from __future__ import annotations

from .._core._pipeline import AsyncPipeline, SyncPipeline
from .learners import AsyncLearners, Learners


class SyncResources:
    learners: Learners

    def __init__(self, pipeline: SyncPipeline) -> None:
        self.learners = Learners(pipeline)


class AsyncResources:
    learners: AsyncLearners

    def __init__(self, pipeline: AsyncPipeline) -> None:
        self.learners = AsyncLearners(pipeline)
