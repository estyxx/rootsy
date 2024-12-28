from typing import ClassVar

import attrs

from rootsy.adapters import GedcomRecord


@attrs.frozen(slots=True, kw_only=True)
class Address(GedcomRecord):
    tag: ClassVar[str] = "ADDR"

    full: str
    line1: str | None = attrs.field(default=None)
    line2: str | None = attrs.field(default=None)
    line3: str | None = attrs.field(default=None)
    city: str | None = attrs.field(default=None)
    state: str | None = attrs.field(default=None)
    postal_code: str | None = attrs.field(default=None)
    country: str | None = attrs.field(default=None)
    phone: list[str] | None = attrs.field(factory=list)
    email: list[str] | None = attrs.field(factory=list)
    fax: list[str] | None = attrs.field(factory=list)
    web: str | None = attrs.field(default=None)
