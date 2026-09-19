from typing import TYPE_CHECKING, Any, ClassVar

import attrs

from rootsy.adapters import GedcomParser
from rootsy.models import Family
from rootsy.parsers.event import EventParser

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rootsy.types import GedcomLine, ParsingContext


@attrs.frozen
class FamilyParser(GedcomParser[Family]):
    """Parser for the FAM record."""

    handles_tag: ClassVar[str] = Family.tag

    def parse(
        self,
        lines: Sequence[GedcomLine],
        context: ParsingContext,
    ) -> tuple[Family, int]:
        """Parse record from GEDCOM lines."""
        data: dict[str, Any] = {
            "children": [],
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
                case "FAM":
                    data["id"] = line.xref
                case "HUSB":
                    data["husband"] = line.value
                case "WIFE":
                    data["wife"] = line.value
                case "CHIL":
                    data["children"].append(line.value)
                case "MARR" | "DIV":
                    event, event_lines = events.parse(lines[i:], context)
                    key = "marriage_event" if line.tag == "MARR" else "divorce_event"
                    data[key] = event
                    lines_consumed += event_lines - 1
                    i += event_lines - 1
                # Other events, SLGS, NOTE, SOUR, … and vendor extensions.
                case _:
                    data["unparsed"].append(line)

            i += 1

        return Family(**data), lines_consumed
