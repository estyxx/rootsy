import re
from collections.abc import Sequence
from typing import Any, ClassVar

import attrs

from rootsy.adapters import GedcomParser
from rootsy.models import Individual
from rootsy.parsers.event import EventParser
from rootsy.types import GedcomLine, ParsingContext

# Tags of the INDI substructures parsed as events.
EVENT_TAGS = frozenset({"BIRT", "DEAT", "RESI"})

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
            "events": [],
            "child_of_families": [],
            "spouse_in_families": [],
            "unparsed": [],
        }
        lines_consumed = 0
        events = EventParser()

        # Process each line
        i = 0
        while i < len(lines):
            line = lines[i]

            # If we've hit another top-level record, we're done
            if i > 0 and line.level == 0:
                break

            # Update context
            context.enter_level(line)
            lines_consumed += 1

            match line.tag:
                case "INDI":
                    data["id"] = line.xref
                case "NAME":
                    data["name"] = line.value
                case "GIVN":
                    data["given_name"] = line.value
                case "SURN":
                    data["surname"] = line.value
                case "SEX":
                    data["sex"] = line.value
                case "EMAIL":
                    data["email"] = line.value
                # FAMC tag points to a family where this person is a child.
                case "FAMC":
                    data["child_of_families"].append(line.value)
                # FAMS tag points to a family where this person is a spouse or parent.
                case "FAMS":
                    data["spouse_in_families"].append(line.value)
                case tag if tag in EVENT_TAGS:
                    event, event_lines = events.parse(lines[i:], context)
                    data["events"].append(event)
                    lines_consumed += event_lines - 1
                    i += event_lines - 1
                # Untyped events, NOTE, OBJE, CHAN, … and vendor extensions.
                case _:
                    data["unparsed"].append(line)

            i += 1

        _derive_name_parts(data)

        return Individual(**data), lines_consumed


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
