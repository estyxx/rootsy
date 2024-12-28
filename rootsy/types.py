from typing import ClassVar, Self

import attrs


@attrs.frozen(slots=True, kw_only=True)
class GedcomLine:
    """Represents a single line in a GEDCOM file."""

    level: int
    tag: str
    value: str
    xref: str | None = None

    # Minimum required parts in a GEDCOM line (level + tag)
    MIN_PARTS: ClassVar[int] = 2  # A GEDCOM line must have at least a level and a tag

    @classmethod
    def from_string(cls, line: str) -> Self | None:
        """Parse a GEDCOM line into its components."""
        parts = line.split(maxsplit=2)
        if len(parts) < cls.MIN_PARTS:
            return None

        level = int(parts[0])
        remainder = parts[1:]

        # Handle cross-reference IDs
        if remainder[0].startswith("@") and remainder[0].endswith("@"):
            xref = remainder[0]
            tag = remainder[1] if len(remainder) > 1 else ""
            value = remainder[2] if len(remainder) > cls.MIN_PARTS else ""
        else:
            xref = None
            tag = remainder[0]
            value = remainder[1] if len(remainder) > 1 else ""

        return cls(
            level=level,
            tag=tag,
            value=value,
            xref=xref,
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
