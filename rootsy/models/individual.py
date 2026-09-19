from typing import TYPE_CHECKING, ClassVar

import attrs

from rootsy.adapters import GedcomRecord
from rootsy.models.event import Event, EventType

if TYPE_CHECKING:
    from rootsy.models.multimedia import Multimedia
    from rootsy.types import GedcomLine


@attrs.frozen(slots=True, kw_only=True)
class Individual(GedcomRecord):
    """An INDI record: who the person is and which families they belong to."""

    tag: ClassVar[str] = "INDI"

    id: str
    name: str | None = None  # NAME, as written: "Given /Surname/ Suffix"
    given_name: str | None = None  # GIVN, or derived from NAME
    surname: str | None = None  # SURN, or derived from NAME
    name_prefix: str | None = None  # NPFX, a title such as "Dr"
    married_name: str | None = None  # _MARNM, the name taken on marrying
    sex: str | None = None
    events: list[Event] = attrs.field(factory=list)
    # FAMC: families this person is a child of. FAMS: families they are a spouse in.
    child_of_families: list[str] = attrs.field(factory=list)
    spouse_in_families: list[str] = attrs.field(factory=list)
    email: str | None = None
    occupations: list[str] = attrs.field(factory=list)  # OCCU
    notes: list[str] = attrs.field(factory=list)  # NOTE, continuations joined
    media: list[Multimedia] = attrs.field(factory=list)  # OBJE
    # _UID: the identity an exporter gives a person, stable across exports.
    uid: str | None = None
    # RIN and _UPD: an exporter's own record number and last-changed stamp.
    vendor: dict[str, str] = attrs.field(factory=dict)
    # SOUR citations are kept verbatim until there is a citation parser.
    citations: list[GedcomLine] = attrs.field(factory=list)

    @property
    def birth(self) -> Event | None:
        """The first BIRT event, if the record has one."""
        return self._first_event(EventType.BIRTH)

    @property
    def death(self) -> Event | None:
        """The first DEAT event, if the record has one."""
        return self._first_event(EventType.DEATH)

    @property
    def primary_photo(self) -> Multimedia | None:
        """The picture to show for this person: the one marked `_PRIM Y`.

        A file that marks none falls back to the first, which is the order
        MyHeritage writes them in.
        """
        if not self.media:
            return None
        return next((item for item in self.media if item.primary), self.media[0])

    def _first_event(self, event_type: EventType) -> Event | None:
        return next(
            (event for event in self.events if event.type == event_type),
            None,
        )
