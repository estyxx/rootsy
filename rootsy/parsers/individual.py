import re
from typing import TYPE_CHECKING, Any, ClassVar

import attrs

from rootsy.adapters import GedcomParser
from rootsy.lines import joined_text, non_continuation_lines, substructure_length
from rootsy.models import Individual
from rootsy.parsers.event import EventParser
from rootsy.parsers.multimedia import MultimediaParser
from rootsy.parsers.vendor import RECORD_TAGS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rootsy.types import GedcomLine, ParsingContext

# Tags of the INDI substructures parsed as events.
EVENT_TAGS = frozenset({"BIRT", "BURI", "DEAT", "RESI"})

# Pieces of a personal name, by the field of `Individual` they fill. The spec
# nests them under NAME; MyHeritage adds `_MARNM` there for a married name.
NAME_PIECES = {
    "GIVN": "given_name",
    "SURN": "surname",
    "NPFX": "name_prefix",
    "_MARNM": "married_name",
}

# A NAME value: "Given /Surname/ Suffix", where any part may be empty.
NAME_PARTS = re.compile(r"^(?P<given>[^/]*)/(?P<surname>[^/]*)/?(?P<suffix>.*)$")


@attrs.frozen
class IndividualParser(GedcomParser[Individual]):
    """Parser for the INDI record."""

    handles_tag: ClassVar[str] = Individual.tag

    def parse(
        self,
        lines: Sequence[GedcomLine],
        context: ParsingContext,
    ) -> tuple[Individual, int]:
        """Parse an individual record and all its substructures."""
        data: dict[str, Any] = {
            "id": lines[0].xref,
            "events": [],
            "child_of_families": [],
            "spouse_in_families": [],
            "occupations": [],
            "notes": [],
            "media": [],
            "vendor": {},
            "citations": [],
            "unparsed": [],
        }
        level = lines[0].level
        context.enter_level(lines[0])
        events = EventParser()
        media = MultimediaParser()

        i = 1
        while i < len(lines) and lines[i].level > level:
            line = lines[i]
            context.enter_level(line)
            # Most tags are a single line; a structure says how long it is.
            consumed = 1

            match line.tag:
                case "NAME":
                    data["name"] = line.value
                case tag if (field := NAME_PIECES.get(tag)) is not None:
                    data[field] = line.value
                case "SEX":
                    data["sex"] = line.value
                case "EMAIL":
                    data["email"] = line.value
                case "OCCU":
                    data["occupations"].append(line.value)
                case "_UID":
                    data["uid"] = line.value
                case tag if tag in RECORD_TAGS:
                    data["vendor"][tag] = line.value
                # FAMC tag points to a family where this person is a child.
                case "FAMC":
                    data["child_of_families"].append(line.value)
                # FAMS tag points to a family where this person is a spouse or parent.
                case "FAMS":
                    data["spouse_in_families"].append(line.value)
                case "NOTE":
                    span = _span(lines, i)
                    data["notes"].append(joined_text(span))
                    data["unparsed"].extend(non_continuation_lines(span))
                    consumed = len(span)
                case "SOUR":
                    span = _span(lines, i)
                    data["citations"].extend(span)
                    consumed = len(span)
                case "OBJE":
                    item, consumed = media.parse(lines[i:], context)
                    data["media"].append(item)
                case tag if tag in EVENT_TAGS:
                    event, consumed = events.parse(lines[i:], context)
                    data["events"].append(event)
                # Untyped events, CHAN, … and the vendor tags not named above.
                case _:
                    data["unparsed"].append(line)

            i += consumed

        _derive_name_parts(data)

        return Individual(**data), i


def _span(lines: Sequence[GedcomLine], start: int) -> Sequence[GedcomLine]:
    """Take the line at `start` and every line nested under it."""
    return lines[start : start + substructure_length(lines, start)]


def _derive_name_parts(data: dict[str, Any]) -> None:
    """Fill in given_name and surname from NAME when GIVN/SURN are absent."""
    if not (name := data.get("name")):
        return
    given_name, surname = split_name(name)
    data.setdefault("given_name", given_name)
    data.setdefault("surname", surname)


def split_name(value: str) -> tuple[str | None, str | None]:
    """Split a "Given /Surname/ Suffix" NAME value into given name and surname."""
    match = NAME_PARTS.match(value)
    if match is None:
        # No slashes at all: the whole value is the given name.
        return value.strip() or None, None
    return match["given"].strip() or None, match["surname"].strip() or None
