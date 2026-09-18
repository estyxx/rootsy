from typing import ClassVar

import attrs

from rootsy.adapters import GedcomRecord
from rootsy.models.event import Event, EventType


@attrs.frozen(slots=True, kw_only=True)
class Individual(GedcomRecord):
    """An INDI record: who the person is and which families they belong to."""

    tag: ClassVar[str] = "INDI"

    id: str
    name: str | None = None  # NAME, as written: "Given /Surname/ Suffix"
    given_name: str | None = None  # GIVN, or derived from NAME
    surname: str | None = None  # SURN, or derived from NAME
    sex: str | None = None
    events: list[Event] = attrs.field(factory=list)
    # FAMC: families this person is a child of. FAMS: families they are a spouse in.
    child_of_families: list[str] = attrs.field(factory=list)
    spouse_in_families: list[str] = attrs.field(factory=list)
    email: str | None = None

    @property
    def birth(self) -> Event | None:
        """The first BIRT event, if the record has one."""
        return self._first_event(EventType.BIRTH)

    @property
    def death(self) -> Event | None:
        """The first DEAT event, if the record has one."""
        return self._first_event(EventType.DEATH)

    def _first_event(self, event_type: EventType) -> Event | None:
        return next(
            (event for event in self.events if event.type == event_type),
            None,
        )
