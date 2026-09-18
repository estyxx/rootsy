from typing import ClassVar

import attrs

from rootsy.adapters import GedcomRecord


@attrs.frozen(slots=True, kw_only=True)
class Multimedia(GedcomRecord):
    """An OBJE record: a file attached to a record."""

    tag: ClassVar[str] = "OBJE"

    id: str | None = None  # the record's xref, `@M1@`
    file: str | None = None  # FILE
    format: str | None = None  # FORM
    title: str | None = None  # TITL
