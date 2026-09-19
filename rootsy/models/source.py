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
    # _UID: the identity an exporter gives a source, stable across exports.
    uid: str | None = None
    # RIN and _UPD: an exporter's own record number and last-changed stamp.
    vendor: dict[str, str] = attrs.field(factory=dict)
