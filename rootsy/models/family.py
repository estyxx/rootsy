from typing import TYPE_CHECKING, ClassVar

import attrs

from rootsy.adapters import GedcomRecord

if TYPE_CHECKING:
    from rootsy.models.event import Event


@attrs.frozen(slots=True, kw_only=True)
class Family(GedcomRecord):
    """Represents a family record extracted from GEDCOM files.

    This class models a family structure, including partners (husband and wife),
    children, and significant events such as marriage and divorce. It supports
    various family configurations and relationships, reflecting the diversity of
    human family structures.
    """

    tag: ClassVar[str] = "FAM"

    id: str
    husband: str | None = None
    wife: str | None = None
    children: list[str] = attrs.field(factory=list)
    marriage_event: Event | None = None
    divorce_event: Event | None = None
    # EVEN: anything the family recorded that has no tag of its own, such as an
    # engagement. Each one says what it was in `Event.custom_type`.
    events: list[Event] = attrs.field(factory=list)
    # _UID: the identity an exporter gives a family, stable across exports.
    uid: str | None = None
    # RIN and _UPD: an exporter's own record number and last-changed stamp.
    vendor: dict[str, str] = attrs.field(factory=dict)
