from typing import Any, ClassVar

import attrs

from rootsy.adapters import GedcomRecord
from rootsy.exceptions import UnsupportedGedcomVersionError
from rootsy.models.address import Address
from rootsy.models.date import GedcomDate

SUPPORTED_VERSIONS = ("5.5.1", "7.0")


# attrs hands a validator the instance, the attribute and the value; only the
# value says anything here, and `Any` is what attrs types the other two as.
def _validate_version(_: Any, __: Any, value: str) -> None:  # noqa: ANN401
    """Reject a header declaring a GEDCOM version rootsy does not implement."""
    if value not in SUPPORTED_VERSIONS:
        raise UnsupportedGedcomVersionError(value, SUPPORTED_VERSIONS)


@attrs.frozen(slots=True, kw_only=True)
class HeaderSource(GedcomRecord):
    """Information about the system/software that generated this file."""

    tag: ClassVar[str] = "SOUR"
    # A level-0 SOUR is a source record, not the header's source system.
    tag_path: ClassVar[tuple[str, ...]] = ("HEAD", "SOUR")

    system_id: str
    version: str | None = None
    name: str | None = None
    corporation: str | None = None
    data_name: str | None = None
    data_date: GedcomDate | None = None
    data_copyright: str | None = None
    address: Address | None = None


@attrs.frozen(slots=True, kw_only=True)
class Header(GedcomRecord):
    """Structured representation of GEDCOM file header information."""

    tag: ClassVar[str] = "HEAD"
    encoding: str = "UTF-8"
    source: HeaderSource | None = None
    destination: str | None = None
    transmission_date: GedcomDate | None = None
    language: str | None = None
    copyright: str | None = None

    version: str = attrs.field(validator=_validate_version)
