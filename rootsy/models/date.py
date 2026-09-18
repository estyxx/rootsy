"""The GEDCOM ``DATE_VALUE``: a string that is only sometimes a calendar date."""

from __future__ import annotations

import datetime
import re
from enum import Enum
from typing import Self

import attrs

_MONTHS: dict[str, int] = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

# `@#DGREGORIAN@`, `@#DJULIAN@`, … prefixing a date (5.5.1 DATE_CALENDAR_ESCAPE).
_CALENDAR_ESCAPE = re.compile(r"^@#D(?P<calendar>[A-Z_ ]+)@\s*")
# A trailing `(date phrase)`, the whole value for a date that is only a phrase.
_PHRASE = re.compile(r"\((?P<text>[^()]*)\)\s*$")
_GREGORIAN = "GREGORIAN"

type _YearMonthDay = tuple[int | None, int | None, int | None]
_UNKNOWN: _YearMonthDay = (None, None, None)


class DateQualifier(Enum):
    """Keyword a GEDCOM date value may start with, as written in the file."""

    ABOUT = "ABT"
    CALCULATED = "CAL"
    ESTIMATED = "EST"
    BEFORE = "BEF"
    AFTER = "AFT"
    BETWEEN = "BET"  # BET <date> AND <date>
    FROM = "FROM"  # FROM <date> [TO <date>]
    TO = "TO"
    INTERPRETED = "INT"  # INT <date> (<phrase>)


# Keyword separating the two dates of a range (BET) or a period (FROM).
_RANGE_SEPARATOR: dict[DateQualifier, str] = {
    DateQualifier.BETWEEN: "AND",
    DateQualifier.FROM: "TO",
}


@attrs.frozen(slots=True, kw_only=True)
class GedcomDate:
    """A GEDCOM date value, keeping the original string and whatever parsed out of it.

    GEDCOM dates carry qualifiers, calendars and partial precision, so most of
    them are not a `datetime.date`. Anything that cannot be understood is kept
    in `raw` with every other field left as `None`.
    """

    raw: str
    qualifier: DateQualifier | None = None
    calendar: str | None = None  # DATE_CALENDAR_ESCAPE, without the `@#D…@`
    year: int | None = None
    month: int | None = None
    day: int | None = None
    # Second date of a range (`BET … AND …`) or a period (`FROM … TO …`).
    end_year: int | None = None
    end_month: int | None = None
    end_day: int | None = None
    phrase: str | None = None  # the `(…)` of `INT <date> (<phrase>)`

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Parse a DATE_VALUE. Never raises: unparseable input only keeps `raw`."""
        raw = value.strip()
        text = raw
        phrase = None

        if match := _PHRASE.search(text):
            phrase = match["text"]
            text = text[: match.start()].strip()

        qualifier, text = _split_qualifier(text)
        start, end = _split_range(qualifier, text)
        calendar, (year, month, day) = _parse_date(start)
        end_year, end_month, end_day = _parse_date(end)[1] if end else _UNKNOWN

        return cls(
            raw=raw,
            qualifier=qualifier,
            calendar=calendar,
            year=year,
            month=month,
            day=day,
            end_year=end_year,
            end_month=end_month,
            end_day=end_day,
            phrase=phrase,
        )

    @property
    def is_exact(self) -> bool:
        """Whether the value names one specific Gregorian day."""
        return self.to_date() is not None

    def to_date(self) -> datetime.date | None:
        """Return a `datetime.date`, or `None` unless the value is an exact day."""
        if self.qualifier is not None or self.end_year is not None:
            return None
        if self.calendar is not None and self.calendar != _GREGORIAN:
            return None
        if self.year is None or self.month is None or self.day is None:
            return None
        try:
            return datetime.date(self.year, self.month, self.day)
        except ValueError:  # e.g. 31 FEB 1890
            return None

    def __str__(self) -> str:
        return self.raw


def _split_qualifier(text: str) -> tuple[DateQualifier | None, str]:
    """Take the leading ABT/BEF/BET/… keyword off a date value, if there is one."""
    keyword, _, rest = text.partition(" ")
    try:
        qualifier = DateQualifier(keyword.upper())
    except ValueError:
        return None, text
    return qualifier, rest.strip()


def _split_range(qualifier: DateQualifier | None, text: str) -> tuple[str, str | None]:
    """Split `BET x AND y` and `FROM x TO y` into their two dates."""
    if qualifier is None or (separator := _RANGE_SEPARATOR.get(qualifier)) is None:
        return text, None

    match re.split(rf"\s{separator}\s", text, maxsplit=1, flags=re.IGNORECASE):
        case [start, end]:
            return start.strip(), end.strip()
        case _:
            return text, None


def _parse_date(text: str) -> tuple[str | None, _YearMonthDay]:
    """Split a single date into its calendar escape and its year/month/day."""
    calendar = None
    if match := _CALENDAR_ESCAPE.match(text):
        calendar = match["calendar"].strip()
        text = text[match.end() :]
    return calendar, _parse_gregorian(text)


def _parse_gregorian(text: str) -> _YearMonthDay:
    """Parse `1890`, `MAR 1890` or `14 MAR 1890`; anything else is unknown."""
    match text.upper().split():
        case [year] if (parsed_year := _parse_year(year)) is not None:
            return parsed_year, None, None
        case [month, year] if (
            (parsed_year := _parse_year(year)) is not None
            and (parsed_month := _MONTHS.get(month)) is not None
        ):
            return parsed_year, parsed_month, None
        case [day, month, year] if (
            day.isdigit()
            and (parsed_year := _parse_year(year)) is not None
            and (parsed_month := _MONTHS.get(month)) is not None
        ):
            return parsed_year, parsed_month, int(day)
        case _:
            return _UNKNOWN


def _parse_year(text: str) -> int | None:
    """Parse a year, keeping the first half of a dual year such as `1890/91`."""
    year, _, _ = text.partition("/")
    return int(year) if year.isdigit() else None
