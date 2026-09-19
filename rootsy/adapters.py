import abc
from typing import TYPE_CHECKING, ClassVar, Protocol, Self, cast

import attrs

from rootsy.exceptions import ParserNotFoundError
from rootsy.types import GedcomLine, ParsingContext

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["GedcomParser", "GedcomRecord", "ParserNotFoundError", "ParsingContext"]


@attrs.frozen(kw_only=True)
class GedcomRecord(abc.ABC):
    """Base class for all GEDCOM records/structures."""

    tag: ClassVar[str]  # Will be defined by each subclass
    # Set when the tag alone does not identify the structure, as `SOUR` does not:
    # under HEAD it is the file's source system, at level 0 it is a source record.
    tag_path: ClassVar[tuple[str, ...] | None] = None

    # Lines of this structure that no field of the model holds: tags rootsy does
    # not parse yet and vendor extensions such as `_UID`. Nothing is dropped.
    unparsed: list[GedcomLine] = attrs.field(factory=list)

    @classmethod
    def from_lines(cls, lines: list[GedcomLine]) -> Self:
        """Create instance from GEDCOM lines.

        This provides a standard interface for creating any GEDCOM
        """
        # Imported here, not at the top: the registry imports every parser,
        # and every parser imports the models that subclass this class.
        from rootsy.registry import get_parser_for_path  # noqa: PLC0415

        parser = get_parser_for_path(cls.tag_path or (cls.tag,))

        if parser is None:
            raise ParserNotFoundError(cls.tag)

        context = ParsingContext()
        result, _ = parser.parse(lines, context)
        # The registry holds the parser registered under this class's tag, and
        # that parser builds this class; the type system cannot see the pairing.
        return cast("Self", result)


class GedcomParser[Result: GedcomRecord](Protocol):
    """Protocol for parsing specific record types."""

    handles_tag: ClassVar[str]
    # Full tag path this parser claims, for a tag that means different things in
    # different places. A parser with a path is only reached through that path.
    handles_path: ClassVar[tuple[str, ...] | None] = None

    def parse(
        self,
        lines: Sequence[GedcomLine],
        context: ParsingContext,
    ) -> tuple[Result, int]:
        """Parse record from GEDCOM lines."""
        raise NotImplementedError
