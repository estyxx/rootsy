from typing import TYPE_CHECKING, ClassVar

import attrs

from rootsy.adapters import GedcomRecord

if TYPE_CHECKING:
    from rootsy.models.date import GedcomDate


@attrs.frozen(slots=True, kw_only=True)
class Multimedia(GedcomRecord):
    """An OBJE record: a file attached to a record."""

    tag: ClassVar[str] = "OBJE"

    # The object's xref, `@M1@`: the one a level-0 record carries, or the one
    # an `OBJE` inline on a record points at.
    id: str | None = None
    file: str | None = None  # FILE
    format: str | None = None  # FORM
    title: str | None = None  # TITL
    # MyHeritage writes when and where a photo was taken on the OBJE itself,
    # under tags of its own rather than the event the photo belongs to.
    date: GedcomDate | None = None  # _DATE
    place: str | None = None  # _PLACE
    primary: bool = False  # _PRIM Y: the picture to show for the record
    # Every other vendor tag, as written: `_CUTOUT`, `_PERSONALPHOTO`,
    # `_PARENTPHOTO`, `_POSITION`, … Their meaning is the exporter's own.
    vendor: dict[str, str] = attrs.field(factory=dict)
