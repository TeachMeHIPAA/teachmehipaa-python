"""`events.tail`: iterating the Event log from a remembered position."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from typing import TypeVar

import httpx

from .._core._pagination import AsyncPage, SyncPage
from .._core._sentinel import NOT_GIVEN, NotGiven
from ..resources.events import AsyncEventsBase, EventsBase
from ..types import Event, EventType

DEFAULT_INTERVAL = 2.0

_T = TypeVar("_T")


def _none_as_not_given(value: _T | None) -> _T | NotGiven:
    return NOT_GIVEN if value is None else value


class EventTail:
    """A position in the Event log, iterated with `for`.

    `last_event_id` is the id of the last Event handed out, or the `after`
    the tail started from. Save it to resume from the same place after a
    restart.
    """

    def __init__(
        self,
        events_after: Callable[[str | None], SyncPage[Event]],
        *,
        after: str | None,
        follow: bool,
        interval: float,
        stop: threading.Event | None,
        sleep: Callable[[float], None],
    ) -> None:
        self._last_event_id = after
        self._events = self._tail(events_after, follow, interval, stop, sleep)

    @property
    def last_event_id(self) -> str | None:
        return self._last_event_id

    def __iter__(self) -> EventTail:
        return self

    def __next__(self) -> Event:
        return next(self._events)

    def close(self) -> None:
        self._events.close()

    def _tail(
        self,
        events_after: Callable[[str | None], SyncPage[Event]],
        follow: bool,
        interval: float,
        stop: threading.Event | None,
        sleep: Callable[[float], None],
    ) -> Generator[Event, None, None]:
        def stopped() -> bool:
            return stop is not None and stop.is_set()

        while not stopped():
            # The log's `next_cursor` is None at the current end, so each poll
            # starts from the last Event handed out, not from a cursor.
            for event in events_after(self._last_event_id):
                if stopped():
                    return
                self._last_event_id = event.event_id
                yield event
                # Checked again before the loop can fetch another page.
                if stopped():
                    return
            if not follow or stopped():
                return
            sleep(interval)


class AsyncEventTail:
    """A position in the Event log, iterated with `async for`.

    `last_event_id` is the id of the last Event handed out, or the `after`
    the tail started from. Save it to resume from the same place after a
    restart.
    """

    def __init__(
        self,
        events_after: Callable[[str | None], Awaitable[AsyncPage[Event]]],
        *,
        after: str | None,
        follow: bool,
        interval: float,
        stop: asyncio.Event | None,
        sleep: Callable[[float], Awaitable[None]],
    ) -> None:
        self._last_event_id = after
        self._events = self._tail(events_after, follow, interval, stop, sleep)

    @property
    def last_event_id(self) -> str | None:
        return self._last_event_id

    def __aiter__(self) -> AsyncEventTail:
        return self

    async def __anext__(self) -> Event:
        return await anext(self._events)

    async def aclose(self) -> None:
        await self._events.aclose()

    async def _tail(
        self,
        events_after: Callable[[str | None], Awaitable[AsyncPage[Event]]],
        follow: bool,
        interval: float,
        stop: asyncio.Event | None,
        sleep: Callable[[float], Awaitable[None]],
    ) -> AsyncGenerator[Event, None]:
        def stopped() -> bool:
            return stop is not None and stop.is_set()

        while not stopped():
            async for event in await events_after(self._last_event_id):
                if stopped():
                    return
                self._last_event_id = event.event_id
                yield event
                if stopped():
                    return
            if not follow or stopped():
                return
            await _pause(sleep, interval, stop)


async def _pause(
    sleep: Callable[[float], Awaitable[None]],
    seconds: float,
    stop: asyncio.Event | None,
) -> None:
    """Sleeps, cut short when `stop` is set mid-wait."""
    if stop is None:
        await sleep(seconds)
        return
    waits = {asyncio.ensure_future(sleep(seconds)), asyncio.ensure_future(stop.wait())}
    try:
        await asyncio.wait(waits, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for wait in waits:
            wait.cancel()
        await asyncio.gather(*waits, return_exceptions=True)


class Events(EventsBase):
    def tail(
        self,
        *,
        after: str | None = None,
        type: EventType | None = None,
        limit: int | None = None,
        follow: bool = False,
        interval: float = DEFAULT_INTERVAL,
        stop: threading.Event | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> EventTail:
        """Tail the event log.

        Iterates the organization's events oldest first, after `after`. The
        log's `next_cursor` is `None` at the current end, so the tail keeps
        its own position in `last_event_id`. Once caught up it stops, or with
        `follow` polls again every `interval` seconds until the loop breaks
        or `stop` is set.

        Args:
            after: Yield only events after this event id (exclusive), such as
                a saved `last_event_id`. Omit it to start at the oldest
                retained event.
            type: Only events of this type.
            limit: How many events to fetch per request, between 1 and 100.
            follow: Once caught up, keep polling for new events.
            interval: Seconds between polls once caught up in follow mode.
            stop: Ends the tail at the next event or poll; the loop then exits
                normally. A request or wait in progress finishes first.
            max_retries: Overrides the client's `max_retries` for each request.
            timeout: Overrides the client's `timeout` for each request, in
                seconds.
            request_id: Sent as `x-request-id` on every request the tail
                makes, so its polls can be found in your logs and
                TeachMeHIPAA's.
        """

        def events_after(position: str | None) -> SyncPage[Event]:
            return self.list(
                after=_none_as_not_given(position),
                type=_none_as_not_given(type),
                limit=_none_as_not_given(limit),
                max_retries=max_retries,
                timeout=timeout,
                request_id=request_id,
            )

        return EventTail(
            events_after,
            after=after,
            follow=follow,
            interval=interval,
            stop=stop,
            sleep=self._pipeline.sleep,
        )


class AsyncEvents(AsyncEventsBase):
    def tail(
        self,
        *,
        after: str | None = None,
        type: EventType | None = None,
        limit: int | None = None,
        follow: bool = False,
        interval: float = DEFAULT_INTERVAL,
        stop: asyncio.Event | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        timeout: float | httpx.Timeout | NotGiven = NOT_GIVEN,
        request_id: str | NotGiven = NOT_GIVEN,
    ) -> AsyncEventTail:
        """Tail the event log.

        Iterates the organization's events oldest first, after `after`. The
        log's `next_cursor` is `None` at the current end, so the tail keeps
        its own position in `last_event_id`. Once caught up it stops, or with
        `follow` polls again every `interval` seconds until the loop breaks
        or `stop` is set.

        Args:
            after: Yield only events after this event id (exclusive), such as
                a saved `last_event_id`. Omit it to start at the oldest
                retained event.
            type: Only events of this type.
            limit: How many events to fetch per request, between 1 and 100.
            follow: Once caught up, keep polling for new events.
            interval: Seconds between polls once caught up in follow mode.
            stop: Ends the tail at the next event or poll, including mid-wait;
                the loop then exits normally. A request in flight finishes
                first.
            max_retries: Overrides the client's `max_retries` for each request.
            timeout: Overrides the client's `timeout` for each request, in
                seconds.
            request_id: Sent as `x-request-id` on every request the tail
                makes, so its polls can be found in your logs and
                TeachMeHIPAA's.
        """

        def events_after(position: str | None) -> Awaitable[AsyncPage[Event]]:
            return self.list(
                after=_none_as_not_given(position),
                type=_none_as_not_given(type),
                limit=_none_as_not_given(limit),
                max_retries=max_retries,
                timeout=timeout,
                request_id=request_id,
            )

        return AsyncEventTail(
            events_after,
            after=after,
            follow=follow,
            interval=interval,
            stop=stop,
            sleep=self._pipeline.sleep,
        )
