from __future__ import annotations

from typing import Final, Literal, final


@final
class NotGiven:
    """Marks a parameter the caller did not pass, so that `None` stays
    available as an explicit value (for example "clear this field")."""

    def __bool__(self) -> Literal[False]:
        return False

    def __repr__(self) -> str:
        return "NOT_GIVEN"


NOT_GIVEN: Final = NotGiven()
