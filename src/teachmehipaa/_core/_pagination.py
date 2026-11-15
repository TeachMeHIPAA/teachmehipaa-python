"""List responses. A list method returns one page; the page keeps the request
that fetched it so it can fetch the pages after it."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from ._models import BaseModel, LastResponse
from ._request import ApiRequest

if TYPE_CHECKING:
    from ._pipeline import AsyncPipeline, SyncPipeline

ItemT = TypeVar("ItemT")


class PageBody(BaseModel, Generic[ItemT]):
    """The wire shape every list endpoint answers with. Generated page models
    subclass it with their item type."""

    items: list[ItemT]
    next_cursor: str | None


class _Page(Generic[ItemT]):
    def __init__(
        self,
        body: PageBody[ItemT],
        *,
        request: ApiRequest,
        cursor_param: str,
    ) -> None:
        self._body = body
        # The request and the IR's cursor parameter are what fetching the next
        # page needs: the same request with the cursor replaced.
        self._request = request
        self._cursor_param = cursor_param

    @property
    def items(self) -> list[ItemT]:
        """The items on this page only."""
        return self._body.items

    @property
    def next_cursor(self) -> str | None:
        """The cursor of the next page, or `None` on the last page. A page can
        hold fewer items than the limit and still have a next page."""
        return self._body.next_cursor

    @property
    def last_response(self) -> LastResponse:
        return self._body.last_response

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(items={self.items!r}, "
            f"next_cursor={self.next_cursor!r})"
        )


class SyncPage(_Page[ItemT]):
    """One page of a list."""

    def __init__(
        self,
        body: PageBody[ItemT],
        *,
        pipeline: SyncPipeline,
        request: ApiRequest,
        cursor_param: str,
    ) -> None:
        super().__init__(body, request=request, cursor_param=cursor_param)
        self._pipeline = pipeline


class AsyncPage(_Page[ItemT]):
    """One page of a list, from the async client."""

    def __init__(
        self,
        body: PageBody[ItemT],
        *,
        pipeline: AsyncPipeline,
        request: ApiRequest,
        cursor_param: str,
    ) -> None:
        super().__init__(body, request=request, cursor_param=cursor_param)
        self._pipeline = pipeline
