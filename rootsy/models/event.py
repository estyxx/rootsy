from enum import Enum
from typing import TYPE_CHECKING, ClassVar

import attrs

from rootsy.adapters import GedcomRecord

if TYPE_CHECKING:
    from rootsy.models.address import Address
    from rootsy.models.date import GedcomDate
    from rootsy.types import GedcomLine


class EventType(Enum):
    """Type of an event, named by the GEDCOM tag that introduces it."""

    BIRTH = "BIRT"
    DEATH = "DEAT"
    BURIAL = "BURI"
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
    # TYPE, what an `EVEN` actually was: "Engagement", "Census", …
    custom_type: str | None = None
    date: GedcomDate | None = None
    place: str | None = None  # PLAC
    cause: str | None = None  # CAUS, why the event happened
    age: str | None = None  # AGE, as written: "72y", "0", "< 8m"
    email: str | None = None  # EMAIL
    address: Address | None = None  # ADDR
    notes: list[str] = attrs.field(factory=list)  # NOTE, continuations joined
    # SOUR citations are kept verbatim until there is a citation parser.
    citations: list[GedcomLine] = attrs.field(factory=list)
