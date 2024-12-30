from typing import ClassVar

import attrs

from rootsy.adapters import GedcomRecord
from rootsy.models import Event, EventDetail


@attrs.frozen(slots=True, kw_only=True)
class Individual(GedcomRecord):
    """Enhanced Individual record model."""

    tag: ClassVar[str] = "INDI"

    id: str
    name: str | None = None
    given_name: str | None = None
    surname: str | None = None
    sex: str | None = None
    events: list[Event] = attrs.field(factory=list)
    families: list[str] = attrs.field(factory=list)  # Family references
    parents: list[str] = attrs.field(factory=list)
    email: str | None = None


class IndividualEventDetail(EventDetail):
    """Details of an event for an individual."""

    age: int | None = None


class IndividualEventStructure(GedcomRecord):
    pass
