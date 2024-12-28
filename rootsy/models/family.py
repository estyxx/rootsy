from typing import ClassVar

import attrs

from rootsy.adapters import GedcomRecord
from rootsy.models import Event


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
