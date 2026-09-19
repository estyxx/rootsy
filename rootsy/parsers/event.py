from typing import TYPE_CHECKING, Any, ClassVar

import attrs

from rootsy.adapters import GedcomParser
from rootsy.lines import joined_text, non_continuation_lines, substructure_length
from rootsy.models import Event, EventType, GedcomDate

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rootsy.types import GedcomLine, ParsingContext


@attrs.frozen
class EventParser(GedcomParser[Event]):
    """Parser for any event, from its tag down to the end of its EVENT_DETAIL.

    The event type comes from the tag of the first line, so callers must only
    hand over a structure whose tag `EventType` knows (`BIRT`, `MARR`, …).
    """

    handles_tag: ClassVar[str] = Event.tag

    def parse(
        self,
        lines: Sequence[GedcomLine],
        context: ParsingContext,
    ) -> tuple[Event, int]:
        """Parse an event structure from its first line."""
        data: dict[str, Any] = {
            "type": EventType(lines[0].tag),
            "notes": [],
            "citations": [],
            "unparsed": [],
        }
        level = lines[0].level
        context.enter_level(lines[0])

        i = 1
        while i < len(lines) and lines[i].level > level:
            line = lines[i]
            context.enter_level(line)
            # The line plus every line nested under it.
            span = lines[i : i + substructure_length(lines, i)]

            match line.tag:
                case "DATE":
                    data["date"] = GedcomDate.from_string(line.value)
                    data["unparsed"].extend(span[1:])  # TIME, PHRASE, …
                case "PLAC":
                    data["place"] = line.value
                    data["unparsed"].extend(span[1:])  # FORM, MAP, …
                case "NOTE":
                    data["notes"].append(joined_text(span))
                    data["unparsed"].extend(non_continuation_lines(span))
                case "SOUR":
                    data["citations"].extend(span)
                case _:
                    data["unparsed"].extend(span)

            i += len(span)

        return Event(**data), i
