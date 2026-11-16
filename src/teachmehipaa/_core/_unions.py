"""Variant selection for the generated union types.

Unions use pydantic callable discriminators rather than its built-in tagged
unions, because a built-in one raises on a tag it doesn't know. `/v1` adds
variants over time (ADR-0006), so an unknown tag must land on a tolerant
fallback model instead.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Sequence
from typing import Any

# The tag of a property union's fallback variant. Not a valid wire value, so
# it never shadows a real one.
UNKNOWN_VARIANT = "<unknown>"


def by_property(
    wire_name: str, attribute: str, tags: Collection[str]
) -> Callable[[Any], str]:
    """Select the variant named by the `wire_name` property, or the
    fallback when the value is one this library doesn't know."""

    def select(value: Any) -> str:
        tag = (
            value.get(wire_name)
            if isinstance(value, dict)
            else getattr(value, attribute, None)
        )
        return tag if isinstance(tag, str) and tag in tags else UNKNOWN_VARIANT

    return select


def by_presence(
    variants: Sequence[tuple[str, str]], fallback: str | None
) -> Callable[[Any], str | None]:
    """Select the first variant whose marker property is present.

    `variants` pairs each marker property's wire name with the variant's tag
    (its class name). Without a marker the value is the `fallback` variant,
    or invalid when there is none.
    """

    def select(value: Any) -> str | None:
        if not isinstance(value, dict):
            return type(value).__name__
        for wire_name, tag in variants:
            if wire_name in value:
                return tag
        return fallback

    return select
