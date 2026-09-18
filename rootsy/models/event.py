from enum import Enum
from typing import ClassVar

import attrs

from rootsy.adapters import GedcomRecord
from rootsy.models.date import GedcomDate
from rootsy.types import GedcomLine


class EventType(Enum):
    """Type of an event, named by the GEDCOM tag that introduces it."""

    BIRTH = "BIRT"
    DEATH = "DEAT"
    MARRIAGE = "MARR"
    DIVORCE = "DIV"
    BAPTISM = "BAPM"
    RESIDENCE = "RESI"
    OTHER = "EVEN"


@attrs.frozen(slots=True, kw_only=True)
class Event(GedcomRecord):
    """An event plus the EVENT_DETAIL substructure every event type shares."""

    tag: ClassVar[str] = "EVEN"

    type: EventType
    date: GedcomDate | None = None
    place: str | None = None  # PLAC
    notes: list[str] = attrs.field(factory=list)  # NOTE, continuations joined
    # SOUR citations are kept verbatim until there is a citation parser.
    citations: list[GedcomLine] = attrs.field(factory=list)
    unparsed: list[GedcomLine] = attrs.field(factory=list)
