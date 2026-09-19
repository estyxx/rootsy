"""Count what a parsed GEDCOM file kept but did not model.

Every parser puts the lines no field of its model holds into `unparsed`, and
`parse_gedcom` keeps a `SkippedRecord` for every level-0 tag no parser claimed.
Both are there so nothing is lost, but a list of lines says little about a file
of ten thousand of them. `coverage` counts them instead: which tags turned up,
under which record and under which parent, and how often.

    from rootsy.coverage import coverage
    from rootsy.parser import parse_gedcom

    report = coverage(parse_gedcom("family.ged"))

The answer says what to model next, in the order the file asks for it.
"""

from __future__ import annotations

import collections
import itertools
from typing import TYPE_CHECKING

import attrs

from rootsy.adapters import GedcomRecord
from rootsy.models import Event

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from rootsy.models import GedcomStructure
    from rootsy.types import GedcomLine

__all__ = ["Coverage", "RecordCoverage", "TagCount", "coverage"]

# The level-0 records `GedcomStructure` has a home for, by the tag they are
# read from. A record type with nowhere to go yet cannot be counted here.
_RECORD_TAGS = ("HEAD", "INDI", "FAM", "SOUR")


@attrs.frozen(slots=True, kw_only=True)
class TagCount:
    """How often one tag path came up, named from its level-0 record down."""

    path: tuple[str, ...]
    count: int

    def __str__(self) -> str:
        return " > ".join(self.path)


@attrs.frozen(slots=True, kw_only=True)
class RecordCoverage:
    """The unparsed tags of one kind of level-0 record, most frequent first."""

    tag: str
    records: int  # how many records of this kind the file held
    records_with_unparsed: int
    paths: list[TagCount] = attrs.field(factory=list)

    @property
    def lines(self) -> int:
        """How many unparsed lines those records hold between them."""
        return sum(path.count for path in self.paths)


@attrs.frozen(slots=True, kw_only=True)
class Coverage:
    """What one file went through rootsy without being modelled."""

    # Only the record types that left something unparsed, worst first.
    records: list[RecordCoverage] = attrs.field(factory=list)
    skipped: list[TagCount] = attrs.field(factory=list)

    @property
    def unparsed_lines(self) -> int:
        """How many lines went unparsed across every record of the file."""
        return sum(record.lines for record in self.records)

    @property
    def skipped_records(self) -> int:
        """How many level-0 records no parser claimed."""
        return sum(tag.count for tag in self.skipped)


def coverage(structure: GedcomStructure) -> Coverage:
    """Count the tags `structure` kept unparsed, by record type and tag path."""
    headers = [] if structure.header is None else [structure.header]
    by_tag: dict[str, Iterable[GedcomRecord]] = {
        "HEAD": headers,
        "INDI": structure.individuals.values(),
        "FAM": structure.families.values(),
        "SOUR": structure.sources.values(),
    }
    groups = [_record_coverage(tag, by_tag[tag]) for tag in _RECORD_TAGS]

    return Coverage(
        records=sorted(
            (group for group in groups if group.paths),
            key=lambda group: (-group.lines, group.tag),
        ),
        skipped=_counted((record.tag,) for record in structure.skipped),
    )


def _record_coverage(tag: str, records: Iterable[GedcomRecord]) -> RecordCoverage:
    """Count the unparsed tags of every record read from one level-0 tag."""
    per_record = [list(_walk(record, (tag,))) for record in records]

    return RecordCoverage(
        tag=tag,
        records=len(per_record),
        records_with_unparsed=sum(1 for paths in per_record if paths),
        paths=_counted(itertools.chain.from_iterable(per_record)),
    )


def _counted(paths: Iterable[tuple[str, ...]]) -> list[TagCount]:
    """Count each path and order them by how often they came up."""
    counts = collections.Counter(paths)
    return [
        TagCount(path=path, count=count)
        for path, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _walk(record: GedcomRecord, path: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
    """Name every unparsed line of a record and of the structures it holds."""
    yield from _line_paths(path, record.unparsed)
    for substructure in _substructures(record):
        yield from _walk(substructure, (*path, _tag_of(substructure)))


def _substructures(record: GedcomRecord) -> Iterator[GedcomRecord]:
    """Every nested structure a record holds, whatever field it sits in."""
    for field in attrs.fields(type(record)):
        match getattr(record, field.name):
            case GedcomRecord() as substructure:
                yield substructure
            case list() as values:
                yield from (v for v in values if isinstance(v, GedcomRecord))


def _tag_of(record: GedcomRecord) -> str:
    """Name a structure by the tag it was read from; an event by its type."""
    return record.type.value if isinstance(record, Event) else record.tag


def _line_paths(
    base: tuple[str, ...],
    lines: list[GedcomLine],
) -> Iterator[tuple[str, ...]]:
    """Name each unparsed line by the tags it sits under, from `base` down.

    Ancestry comes from the levels of the lines themselves, so a line nested
    under another unparsed line reads as `INDI > OBJE > FILE`. A parent the
    parser read itself, such as the `DATE` above a `TIME`, is not in the list
    and so is not in the path either.
    """
    ancestors: list[GedcomLine] = []

    for line in lines:
        while ancestors and ancestors[-1].level >= line.level:
            ancestors.pop()
        yield (*base, *(ancestor.tag for ancestor in ancestors), line.tag)
        ancestors.append(line)
