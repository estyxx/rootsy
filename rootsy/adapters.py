import abc
from collections.abc import Sequence
from typing import ClassVar, Protocol, Self

import attrs

from rootsy.types import GedcomLine, ParsingContext


class ParserNotFoundError(Exception):
    """Exception raised when no parser is found for a given tag."""

    def __init__(self, tag: str) -> None:
        self.tag = tag
        super().__init__(f"No parser found for tag {tag}")


@attrs.frozen(kw_only=True)
class GedcomRecord(abc.ABC):
    """Base class for all GEDCOM records/structures."""

    tag: ClassVar[str]  # Will be defined by each subclass

    @classmethod
    def from_lines(cls, lines: list[GedcomLine]) -> Self:
        """Create instance from GEDCOM lines.

        This provides a standard interface for creating any GEDCOM
        """
        # Get the appropriate parser using the tag
        from rootsy.registry import get_parser_for_tag

        parser = get_parser_for_tag(cls.tag)

        if parser is None:
            raise ParserNotFoundError(cls.tag)

        context = ParsingContext()
        result, _ = parser.parse(lines, context)
        return result


class GedcomParser[Result: GedcomRecord](Protocol):
    """Protocol for parsing specific record types."""

    handles_tag: ClassVar[str]

    def parse(
        self,
        lines: Sequence[GedcomLine],
        context: ParsingContext,
    ) -> tuple[GedcomRecord, int]:
        """Parse record from GEDCOM lines."""
        raise NotImplementedError
