import datetime
import enum
from typing import TYPE_CHECKING, Any, Self

import attrs

from rootsy.models.date import GedcomDate

if TYPE_CHECKING:
    from rootsy.models.family import Family
    from rootsy.models.header import Header
    from rootsy.models.individual import Individual
    from rootsy.models.source import SourceRecord
    from rootsy.types import GedcomLine


def _serialise(_: Any, __: Any, value: Any) -> Any:  # noqa: ANN401
    """Turn the values models hold into something `json.dumps` accepts."""
    match value:
        # A GEDCOM date is rarely a calendar date, so JSON keeps it as written.
        case GedcomDate():
            return value.raw
        case enum.Enum():
            return value.value
        case datetime.datetime() | datetime.date():
            return value.isoformat()
        case _:
            return value


@attrs.frozen(slots=True, kw_only=True)
class SkippedRecord:
    """A level-0 record no parser claimed, named so a caller can report it."""

    tag: str
    xref: str | None = None
    line_number: int | None = None

    @classmethod
    def from_line(cls, line: GedcomLine) -> Self:
        """Describe the record the given level-0 line opens."""
        return cls(tag=line.tag, xref=line.xref, line_number=line.line_number)


@attrs.define(slots=True, kw_only=True)
class GedcomStructure:
    """A class to represent the structure of a GEDCOM file."""

    # A file may be missing its header, or be truncated before it: parsing what
    # is there still beats raising.
    header: Header | None = None
    individuals: dict[str, Individual] = attrs.field(factory=dict)
    families: dict[str, Family] = attrs.field(factory=dict)
    sources: dict[str, SourceRecord] = attrs.field(factory=dict)
    # Level-0 records rootsy has no parser for. They are counted, not dropped
    # silently, so `rootsy stats` can say how much of a file went unread.
    skipped: list[SkippedRecord] = attrs.field(factory=list)

    def add_individual(self, individual: Individual) -> None:
        """Add an individual to the GedcomStructure."""
        self.individuals[individual.id] = individual

    def add_family(self, family: Family) -> None:
        """Add a family to the GedcomStructure."""
        self.families[family.id] = family

    def add_source(self, source: SourceRecord) -> None:
        """Add a source record to the GedcomStructure.

        A record without an xref cannot be cited, so there is nothing to key it
        by and it is left out.
        """
        if source.id is not None:
            self.sources[source.id] = source

    def add_skipped(self, line: GedcomLine) -> None:
        """Record that the level-0 record opened by `line` went unparsed."""
        self.skipped.append(SkippedRecord.from_line(line))

    def to_dict(self) -> dict[str, Any]:
        """Convert the GedcomStructure to a dictionary."""
        return attrs.asdict(self, value_serializer=_serialise)
