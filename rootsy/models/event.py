import datetime
from enum import Enum, auto
from typing import Any, ClassVar

import attrs

from rootsy.adapters import GedcomRecord


class EventType(Enum):
    """Enum representing the types of events in a GEDCOM file."""

    BIRTH = auto()
    DEATH = auto()
    MARRIAGE = auto()
    DIVORCE = auto()
    BAPTISM = auto()


@attrs.frozen(slots=True, kw_only=True)
class Event(GedcomRecord):
    """Comprehensive event representation."""

    tag: ClassVar[str] = "EVEN"

    type: EventType
    date: datetime.date | None = None
    place: str | None = None
    additional_details: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True, kw_only=True)
class EventDetail(GedcomRecord):
    """Details of an event."""

    tag: ClassVar[str] = "EVEN"

    type: EventType
    date: datetime.date | None = None
    place: str | None = None
