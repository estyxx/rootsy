from typing import ClassVar

import attrs

from rootsy.adapters import GedcomRecord


@attrs.frozen(slots=True, kw_only=True)
class SourceRecord(GedcomRecord):
    """A level-0 SOUR record: the source a citation points at."""

    tag: ClassVar[str] = "SOUR"

    id: str | None = None  # the record's xref, `@S1@`
    title: str | None = None  # TITL
    author: str | None = None  # AUTH
    publication: str | None = None  # PUBL
    text: str | None = None  # TEXT, the source's own words
