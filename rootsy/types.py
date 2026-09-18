from __future__ import annotations

import re
from typing import Self

import attrs

# `level [xref] tag [value]`: the delimiter is a single space and the value runs
# to the end of the line, so it may itself contain spaces and `@` characters.
_LINE = re.compile(
    r"^(?P<level>\d+)"
    r"(?: +(?P<xref>@[^@\s]+@))?"
    r" +(?P<tag>\S+)"
    r"(?: (?P<value>.*))?$",
)


@attrs.frozen(slots=True, kw_only=True)
class GedcomLine:
    """Represents a single line in a GEDCOM file."""

    level: int
    tag: str
    value: str
    xref: str | None = None
    # Where the line came from, for error messages. A line means the same thing
    # wherever it was read from, so it is left out of equality.
    line_number: int | None = attrs.field(default=None, eq=False)

    @classmethod
    def from_string(cls, line: str, line_number: int | None = None) -> Self | None:
        """Parse a GEDCOM line into its components, or `None` if it is not one."""
        match = _LINE.match(line.strip())
        if match is None:
            return None

        return cls(
            level=int(match["level"]),
            tag=match["tag"],
            value=match["value"] or "",
            xref=match["xref"],
            line_number=line_number,
        )


class ParsingContext:
    """Manages parsing state and hierarchy tracking.

    Shared across all parsers to maintain consistent state.
    """

    def __init__(self) -> None:
        self._current_level: int = -1
        self._current_path: list[str] = []

    @property
    def current_level(self) -> int:
        return self._current_level

    @property
    def path(self) -> tuple[str, ...]:
        """Current parsing path as tuple of tags."""
        return tuple(self._current_path)

    def enter_level(self, line: GedcomLine) -> None:
        """Update context for entering a new level."""
        while self._current_level >= line.level:
            self._current_path.pop()
            self._current_level -= 1

        self._current_path.append(line.tag)
        self._current_level = line.level

    def __str__(self) -> str:
        return " > ".join(self._current_path)
