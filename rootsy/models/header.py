import datetime
from typing import ClassVar

import attrs

from rootsy.adapters import GedcomRecord
from rootsy.models import Address


class UnsupportedGedcomVersionError(ValueError):
    def __init__(self, version: str) -> None:
        message = (
            f"Unsupported GEDCOM version '{version}'. "
            "Supported versions are 5.5.1 and 7.0"
        )

        super().__init__(message)


@attrs.frozen(slots=True, kw_only=True)
class HeaderSource(GedcomRecord):
    """Information about the system/software that generated this file."""

    tag: ClassVar[str] = "SOUR"

    system_id: str
    version: str | None = None
    name: str | None = None
    corporation: str | None = None
    data_name: str | None = None
    data_date: datetime.date | None = None
    data_copyright: str | None = None
    address: Address | None = None


@attrs.frozen(slots=True, kw_only=True)
class Header(GedcomRecord):
    """Structured representation of GEDCOM file header information."""

    tag: ClassVar[str] = "HEAD"
    encoding: str = "UTF-8"
    source: HeaderSource | None = None
    destination: str | None = None
    transmission_date: datetime.date | None = None
    language: str | None = None
    copyright: str | None = None

    def validate_version(self, __: str, value: str) -> None:
        """Validate if this is a supported version."""
        major_minor = value.split(".")[:2]
        if major_minor not in (["5", "5"], ["7", "0"]):
            raise UnsupportedGedcomVersionError(value)

    version: str = attrs.field(validator=validate_version)
