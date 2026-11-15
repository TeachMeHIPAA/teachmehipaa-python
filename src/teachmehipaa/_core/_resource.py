from __future__ import annotations

from ._pipeline import AsyncPipeline, SyncPipeline


class SyncAPIResource:
    def __init__(self, pipeline: SyncPipeline) -> None:
        self._pipeline = pipeline


class AsyncAPIResource:
    def __init__(self, pipeline: AsyncPipeline) -> None:
        self._pipeline = pipeline
