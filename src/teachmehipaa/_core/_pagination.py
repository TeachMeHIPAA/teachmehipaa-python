"""List responses. A list method returns one page; the page keeps the request
that fetched it so it can fetch the pages after it."""

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator, Iterator
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
        position_field: str | None,
    ) -> None:
        self._body = body
        # The request and the IR's cursor parameter are what fetching the next
        # page needs: the same request with the cursor replaced.
        self._request = request
        self._cursor_param = cursor_param
        self._position_field = position_field

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

    def has_next_page(self) -> bool:
        """Whether the API said more items follow (`next_cursor` is not
        `None`)."""
        return self._body.next_cursor is not None

    def _next_request(self) -> ApiRequest:
        next_cursor = self._body.next_cursor
        if next_cursor is None:
            raise RuntimeError("this is the last page; check has_next_page() first")
        # The first call's filters and limit carry over unchanged; the server,
        # not the client, validates them.
        query = {**self._request.query, self._cursor_param: self._position(next_cursor)}
        return dataclasses.replace(self._request, query=query)

    def _position(self, next_cursor: str) -> str:
        """The next page's cursor. A list the IR pages `after` an item (the
        Event log) keys on that item's id: `next_cursor` is the last id while
        more rows exist, so the last item is the authoritative position.
        Every other list sends the opaque `next_cursor`."""
        if self._position_field is None or not self._body.items:
            return next_cursor
        position = getattr(self._body.items[-1], self._position_field, None)
        return position if isinstance(position, str) else next_cursor

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
        position_field: str | None,
    ) -> None:
        super().__init__(
            body,
            request=request,
            cursor_param=cursor_param,
            position_field=position_field,
        )
        self._pipeline = pipeline

    def __iter__(self) -> Iterator[ItemT]:
        """Every item on this page and the pages after it, each page fetched
        only when the loop reaches it."""
        for page in self.iter_pages():
            yield from page.items

    def auto_paging_iter(self) -> Iterator[ItemT]:
        """The same as iterating the page; named as in Stripe's library."""
        return iter(self)

    def get_next_page(self) -> SyncPage[ItemT]:
        """Fetches the next page with the same filters and limit. Raises
        `RuntimeError` on the last page: check `has_next_page()` first."""
        return self._pipeline.request_page(
            self._next_request(),
            type(self._body),
            cursor_param=self._cursor_param,
            position_field=self._position_field,
        )

    def iter_pages(self) -> Iterator[SyncPage[ItemT]]:
        """This page, then each page after it, fetched as the loop asks."""
        page = self
        yield page
        while page.has_next_page():
            page = page.get_next_page()
            yield page


class AsyncPage(_Page[ItemT]):
    """One page of a list, from the async client.

    As in Stripe's library, await the list call for the first page, then
    `async for` over the page for every item:
    `async for learner in await client.learners.list():`.
    """

    def __init__(
        self,
        body: PageBody[ItemT],
        *,
        pipeline: AsyncPipeline,
        request: ApiRequest,
        cursor_param: str,
        position_field: str | None,
    ) -> None:
        super().__init__(
            body,
            request=request,
            cursor_param=cursor_param,
            position_field=position_field,
        )
        self._pipeline = pipeline

    async def __aiter__(self) -> AsyncIterator[ItemT]:
        """Every item on this page and the pages after it, each page fetched
        only when the loop reaches it."""
        async for page in self.iter_pages():
            for item in page.items:
                yield item

    def auto_paging_iter(self) -> AsyncIterator[ItemT]:
        """The same as iterating the page; named as in Stripe's library."""
        return aiter(self)

    async def get_next_page(self) -> AsyncPage[ItemT]:
        """Fetches the next page with the same filters and limit. Raises
        `RuntimeError` on the last page: check `has_next_page()` first."""
        return await self._pipeline.request_page(
            self._next_request(),
            type(self._body),
            cursor_param=self._cursor_param,
            position_field=self._position_field,
        )

    async def iter_pages(self) -> AsyncIterator[AsyncPage[ItemT]]:
        """This page, then each page after it, fetched as the loop asks."""
        page = self
        yield page
        while page.has_next_page():
            page = await page.get_next_page()
            yield page
