from collections.abc import Sequence
from typing import Any, ClassVar

import attrs

from rootsy.adapters import GedcomParser
from rootsy.models import Event, EventType, GedcomDate
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
                    data["notes"].append(note_text(span))
                    data["unparsed"].extend(
                        note for note in span[1:] if note.tag not in {"CONC", "CONT"}
                    )
                case "SOUR":
                    data["citations"].extend(span)
                case _:
                    data["unparsed"].extend(span)

            i += len(span)

        return Event(**data), i


def substructure_length(lines: Sequence[GedcomLine], start: int) -> int:
    """Count the line at `start` and every line nested under it."""
    length = 1
    while (
        start + length < len(lines) and lines[start + length].level > lines[start].level
    ):
        length += 1
    return length


def note_text(lines: Sequence[GedcomLine]) -> str:
    """Join a NOTE with its CONT (new line) and CONC (same line) continuations."""
    text = lines[0].value
    for line in lines[1:]:
        match line.tag:
            case "CONT":
                text = f"{text}\n{line.value}"
            case "CONC":
                text = f"{text}{line.value}"
    return text
