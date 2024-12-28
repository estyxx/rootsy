from typing import ClassVar

import attrs

from rootsy.adapters import GedcomRecord
from rootsy.models import Event


@attrs.frozen(slots=True, kw_only=True)
class Individual(GedcomRecord):
    """Enhanced Individual record model."""

    tag: ClassVar[str] = "INDI"

    id: str
    record_type: str
    level: int = 0
    notes: list[str] = attrs.field(factory=list)
    source_citations: list[str] = attrs.field(factory=list)
    name: str | None = None
    given_name: str | None = None
    surname: str | None = None
    sex: str | None = None
    events: list[Event] = attrs.field(factory=list)
    families: list[str] = attrs.field(factory=list)  # Family references
    parents: list[str] = attrs.field(factory=list)
