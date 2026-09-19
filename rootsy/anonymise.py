"""Replace the personal data in a parsed GEDCOM with stand-ins.

A family file is mostly information about people who are alive, so it cannot be
attached to a bug report, committed as a test fixture or handed to a demo as it
is. Anonymising one keeps everything that says how the file is *shaped* - who
is whose child, how many events a record carries, which tags an exporter emits
- and throws away everything that says who those people are.

    from rootsy.anonymise import anonymise
    from rootsy.parser import parse_gedcom

    safe = anonymise(parse_gedcom("family.ged"))

The result is another `GedcomStructure`, so it exports to JSON like any other.
"""

from __future__ import annotations

import collections
import enum
import re
from typing import TYPE_CHECKING

import attrs

from rootsy.models import (
    Address,
    Event,
    Family,
    GedcomDate,
    GedcomStructure,
    Header,
    HeaderSource,
    Individual,
    SkippedRecord,
    SourceRecord,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rootsy.types import GedcomLine

__all__ = ["AnonymisationPolicy", "DatePolicy", "anonymise"]

# RFC 2606 reserves these for documentation, so a stand-in can never reach
# someone by accident.
EXAMPLE_DOMAIN = "example.com"
EXAMPLE_URL = "https://example.com"

# A value that is nothing but a cross-reference, such as `@I1@`. It names a
# record rather than a person, so it is mapped instead of dropped.
_POINTER = re.compile(r"^@[^@\s]+@$")


class DatePolicy(enum.Enum):
    """How much of a date an anonymisation keeps."""

    KEEP = "keep"  # every date as it was written
    YEAR = "year"  # the year alone, dropping qualifiers, months and days
    REMOVE = "remove"  # no dates at all


@attrs.frozen(slots=True, kw_only=True)
class AnonymisationPolicy:
    """What an anonymisation keeps of the file it is given.

    The defaults keep only what a parser test or a tree-shaped demo needs: the
    year of each event, and whether each person was recorded as male or female.
    """

    dates: DatePolicy = DatePolicy.YEAR
    keep_sex: bool = True
    keep_places: bool = False
    # Xrefs name records, not people, but an exporter's numbering can still be
    # recognisable. Off by default, so `@I500123@` becomes `@I1@`.
    keep_xrefs: bool = False


def anonymise(
    structure: GedcomStructure,
    policy: AnonymisationPolicy | None = None,
) -> GedcomStructure:
    """Return a copy of `structure` with every personal detail replaced.

    The tree keeps its shape: cross-references still point where they pointed,
    people who shared a surname still share one, and a place named twice is
    named twice. The original structure is left untouched.
    """
    return _Anonymiser(policy=policy or AnonymisationPolicy()).structure(structure)


@attrs.define(slots=True)
class _Placeholders:
    """Hands out `Surname1`, `Surname2`, … one stand-in per distinct value.

    The same value always gets the same stand-in, so two brothers keep one
    surname between them and a place named in ten records stays one place.
    """

    seen: dict[tuple[str, str], str] = attrs.field(factory=dict)
    counts: collections.Counter[str] = attrs.field(factory=collections.Counter)

    def of(self, prefix: str, value: str) -> str:
        """Return the stand-in this value has, giving it one if it has none."""
        key = (prefix, value)
        if key not in self.seen:
            self.counts[prefix] += 1
            self.seen[key] = f"{prefix}{self.counts[prefix]}"
        return self.seen[key]

    def maybe(self, prefix: str, value: str | None) -> str | None:
        """Stand in for a value that a record may not carry at all."""
        return None if value is None else self.of(prefix, value)


@attrs.define(slots=True, kw_only=True)
class _Anonymiser:
    """Rebuilds every record of one file, remembering the stand-ins it hands out."""

    policy: AnonymisationPolicy
    labels: _Placeholders = attrs.field(factory=_Placeholders)
    # Original xref → the one its record was given, so pointers stay valid.
    xrefs: dict[str, str] = attrs.field(factory=dict)

    def structure(self, original: GedcomStructure) -> GedcomStructure:
        """Rebuild a whole file, records and cross-references alike."""
        self.plan_xrefs(original)

        anonymised = GedcomStructure(
            header=None if original.header is None else self.header(original.header),
            skipped=[self.skipped(record) for record in original.skipped],
        )
        for individual in original.individuals.values():
            anonymised.add_individual(self.individual(individual))
        for family in original.families.values():
            anonymised.add_family(self.family(family))
        for source in original.sources.values():
            anonymised.add_source(self.source(source))

        return anonymised

    def plan_xrefs(self, original: GedcomStructure) -> None:
        """Name every record `@I1@`, `@F1@`, `@S1@`, before anything points at one."""
        keyed: tuple[tuple[str, Iterable[str]], ...] = (
            ("I", original.individuals),
            ("F", original.families),
            ("S", original.sources),
        )
        for prefix, xrefs in keyed:
            for number, xref in enumerate(xrefs, start=1):
                self.xrefs[xref] = f"@{prefix}{number}@"

    # Records ---------------------------------------------------------------

    def individual(self, individual: Individual) -> Individual:
        """Rebuild a person as `Given3 /Surname1/`, keeping their family links."""
        number = self.labels.of("", individual.id)
        given = f"Given{number}" if individual.given_name else None
        surname = self.labels.maybe("Surname", individual.surname)

        return Individual(
            id=self.xref(individual.id),
            name=_slashed_name(individual.name, given, surname),
            given_name=given,
            surname=surname,
            sex=individual.sex if self.policy.keep_sex else None,
            events=[self.event(event) for event in individual.events],
            child_of_families=[
                self.xref(xref) for xref in individual.child_of_families
            ],
            spouse_in_families=[
                self.xref(xref) for xref in individual.spouse_in_families
            ],
            email=self.maybe_email(individual.email),
            unparsed=self.lines(individual.unparsed),
        )

    def family(self, family: Family) -> Family:
        """Rebuild a family: the same people in the same roles, under new names."""
        return Family(
            id=self.xref(family.id),
            husband=self.maybe_xref(family.husband),
            wife=self.maybe_xref(family.wife),
            children=[self.xref(child) for child in family.children],
            marriage_event=self.maybe_event(family.marriage_event),
            divorce_event=self.maybe_event(family.divorce_event),
            unparsed=self.lines(family.unparsed),
        )

    def source(self, source: SourceRecord) -> SourceRecord:
        """Rebuild a source record. Its title and text often name the family."""
        return SourceRecord(
            id=self.maybe_xref(source.id),
            title=self.labels.maybe("Source ", source.title),
            author=self.labels.maybe("Author ", source.author),
            publication=self.labels.maybe("Publication ", source.publication),
            text=self.labels.maybe("Text ", source.text),
            unparsed=self.lines(source.unparsed),
        )

    def header(self, header: Header) -> Header:
        """Keep what says how the file was written, drop what says who wrote it."""
        return Header(
            encoding=header.encoding,
            version=header.version,
            # The exporter names itself here, and its quirks are the reason to
            # keep an anonymised file around at all.
            source=None if header.source is None else self.header_source(header.source),
            destination=header.destination,
            transmission_date=self.date(header.transmission_date),
            language=header.language,
            copyright=None,  # COPR usually names whoever exported the file
            unparsed=self.lines(header.unparsed),
        )

    def header_source(self, source: HeaderSource) -> HeaderSource:
        """Keep the software's own identity; replace the database it exported."""
        return HeaderSource(
            system_id=source.system_id,
            version=source.version,
            name=source.name,
            corporation=source.corporation,
            data_name=self.labels.maybe("Database", source.data_name),
            data_date=self.date(source.data_date),
            data_copyright=None,
            address=None if source.address is None else self.address(source.address),
            unparsed=self.lines(source.unparsed),
        )

    def skipped(self, record: SkippedRecord) -> SkippedRecord:
        """Keep the tag and the line a skipped record was found at, not its xref."""
        return SkippedRecord(
            tag=record.tag,
            xref=self.maybe_xref(record.xref),
            line_number=record.line_number,
        )

    # Substructures ---------------------------------------------------------

    def event(self, event: Event) -> Event:
        """Rebuild an event: the same type, a date and place that name nobody."""
        return Event(
            type=event.type,
            date=self.date(event.date),
            place=self.place(event.place),
            notes=[self.labels.of("Note ", note) for note in event.notes],
            citations=self.lines(event.citations),
            unparsed=self.lines(event.unparsed),
        )

    def maybe_event(self, event: Event | None) -> Event | None:
        """Rebuild an event a record may not have."""
        return None if event is None else self.event(event)

    def address(self, address: Address) -> Address:
        """Replace a postal address, keeping only that the record had one."""
        return Address(
            full=self.labels.of("Address", address.full),
            city=self.place(address.city),
            country=address.country if self.policy.keep_places else None,
            phone=[self.labels.of("Phone", phone) for phone in address.phone or []],
            email=[self.email(email) for email in address.email or []],
            fax=[self.labels.of("Fax", fax) for fax in address.fax or []],
            web=EXAMPLE_URL if address.web else None,
            unparsed=self.lines(address.unparsed),
        )

    # Values ----------------------------------------------------------------

    def date(self, date: GedcomDate | None) -> GedcomDate | None:
        """Reduce a date to what the policy keeps of it.

        Under `YEAR` a date is rewritten as its year alone: a qualifier or a
        date phrase can carry as much as the date itself ("BEF her wedding").
        """
        if date is None or self.policy.dates is DatePolicy.KEEP:
            return date
        if self.policy.dates is DatePolicy.REMOVE or date.year is None:
            return None
        return GedcomDate.from_string(str(date.year))

    def place(self, place: str | None) -> str | None:
        """Stand in for a place name, unless the policy keeps places."""
        if place is None or self.policy.keep_places:
            return place
        return self.labels.of("Place", place)

    def email(self, email: str) -> str:
        """Stand in for an address, in the domain reserved for examples."""
        return f"{self.labels.of('person', email)}@{EXAMPLE_DOMAIN}"

    def maybe_email(self, email: str | None) -> str | None:
        """Stand in for an address a record may not carry."""
        return None if email is None else self.email(email)

    def xref(self, xref: str) -> str:
        """Map a cross-reference to the one its record was given."""
        if self.policy.keep_xrefs:
            return xref
        # A pointer to a record this file does not hold still names something,
        # so it gets a stand-in of its own rather than being left as it was.
        return self.xrefs.setdefault(xref, f"@X{len(self.xrefs) + 1}@")

    def maybe_xref(self, xref: str | None) -> str | None:
        """Map a cross-reference a record may not carry."""
        return None if xref is None else self.xref(xref)

    def lines(self, lines: list[GedcomLine]) -> list[GedcomLine]:
        """Keep the shape of the lines no model field holds, and drop their values."""
        return [self.line(line) for line in lines]

    def line(self, line: GedcomLine) -> GedcomLine:
        """Keep a line's level, tag and place in the file; drop what it says.

        The value of a tag rootsy does not model could say anything at all, so
        only a value that is purely a cross-reference survives, mapped like
        every other pointer.
        """
        value = self.xref(line.value) if _POINTER.match(line.value) else ""
        return attrs.evolve(line, value=value, xref=self.maybe_xref(line.xref))


def _slashed_name(
    name: str | None,
    given: str | None,
    surname: str | None,
) -> str | None:
    """Write the stand-in parts back in the `Given /Surname/` form NAME uses."""
    if name is None:
        return None
    return f"{given or ''} /{surname or ''}/".strip()
