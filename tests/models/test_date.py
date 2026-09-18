import datetime

import pytest

from rootsy.models import DateQualifier, GedcomDate


class TestExactDates:
    def test_full_date(self) -> None:
        """A day, month and year is the one shape that converts to a date."""
        date = GedcomDate.from_string("14 MAR 1890")

        assert date.raw == "14 MAR 1890"
        assert (date.year, date.month, date.day) == (1890, 3, 14)
        assert date.qualifier is None
        assert date.is_exact
        assert date.to_date() == datetime.date(1890, 3, 14)

    def test_lowercase_month(self) -> None:
        """Exporters are not consistent about case."""
        assert GedcomDate.from_string("14 mar 1890").to_date() == datetime.date(
            1890,
            3,
            14,
        )

    def test_impossible_day_is_not_a_date(self) -> None:
        """A date that does not exist keeps its parts but converts to nothing."""
        date = GedcomDate.from_string("31 FEB 1890")

        assert (date.year, date.month, date.day) == (1890, 2, 31)
        assert date.to_date() is None
        assert not date.is_exact


class TestPartialDates:
    def test_year_only(self) -> None:
        date = GedcomDate.from_string("1890")

        assert (date.year, date.month, date.day) == (1890, None, None)
        assert date.to_date() is None

    def test_month_and_year(self) -> None:
        date = GedcomDate.from_string("MAR 1890")

        assert (date.year, date.month, date.day) == (1890, 3, None)
        assert date.to_date() is None

    def test_dual_year(self) -> None:
        """5.5.1 allows `1890/91` for the Julian/Gregorian new year overlap."""
        date = GedcomDate.from_string("11 FEB 1890/91")

        assert (date.year, date.month, date.day) == (1890, 2, 11)


class TestQualifiers:
    @pytest.mark.parametrize(
        ("raw", "qualifier"),
        [
            ("ABT 1890", DateQualifier.ABOUT),
            ("CAL 1890", DateQualifier.CALCULATED),
            ("EST 1890", DateQualifier.ESTIMATED),
            ("BEF 1890", DateQualifier.BEFORE),
            ("AFT 1890", DateQualifier.AFTER),
            ("TO 1890", DateQualifier.TO),
        ],
    )
    def test_single_date_qualifiers(
        self,
        raw: str,
        qualifier: DateQualifier,
    ) -> None:
        date = GedcomDate.from_string(raw)

        assert date.qualifier is qualifier
        assert date.year == 1890
        assert date.to_date() is None

    def test_qualifier_keeps_full_precision(self) -> None:
        """An approximated date is still parsed, it just is not exact."""
        date = GedcomDate.from_string("ABT 14 MAR 1890")

        assert date.qualifier is DateQualifier.ABOUT
        assert (date.year, date.month, date.day) == (1890, 3, 14)
        assert date.to_date() is None

    def test_between_and(self) -> None:
        date = GedcomDate.from_string("BET 1890 AND MAR 1892")

        assert date.qualifier is DateQualifier.BETWEEN
        assert (date.year, date.month, date.day) == (1890, None, None)
        assert (date.end_year, date.end_month, date.end_day) == (1892, 3, None)

    def test_from_to(self) -> None:
        date = GedcomDate.from_string("FROM 1 JAN 1890 TO 31 DEC 1892")

        assert date.qualifier is DateQualifier.FROM
        assert (date.year, date.month, date.day) == (1890, 1, 1)
        assert (date.end_year, date.end_month, date.end_day) == (1892, 12, 31)

    def test_from_without_to(self) -> None:
        date = GedcomDate.from_string("FROM 1890")

        assert date.qualifier is DateQualifier.FROM
        assert date.year == 1890
        assert date.end_year is None

    def test_interpreted(self) -> None:
        date = GedcomDate.from_string("INT 14 MAR 1890 (as written in the register)")

        assert date.qualifier is DateQualifier.INTERPRETED
        assert (date.year, date.month, date.day) == (1890, 3, 14)
        assert date.phrase == "as written in the register"
        assert date.to_date() is None


class TestOddities:
    def test_calendar_escape(self) -> None:
        date = GedcomDate.from_string("@#DJULIAN@ 14 MAR 1890")

        assert date.calendar == "JULIAN"
        assert (date.year, date.month, date.day) == (1890, 3, 14)
        # Only Gregorian days convert.
        assert date.to_date() is None

    def test_gregorian_escape_still_converts(self) -> None:
        date = GedcomDate.from_string("@#DGREGORIAN@ 14 MAR 1890")

        assert date.calendar == "GREGORIAN"
        assert date.to_date() == datetime.date(1890, 3, 14)

    def test_phrase_only(self) -> None:
        date = GedcomDate.from_string("(sometime after the war)")

        assert date.phrase == "sometime after the war"
        assert date.year is None
        assert date.to_date() is None

    @pytest.mark.parametrize(
        "raw",
        ["", "not a date at all", "32 FLO 1890", "MAR", "ABT sometime"],
    )
    def test_unparseable_input_keeps_raw(self, raw: str) -> None:
        """Nothing about a date value may raise."""
        date = GedcomDate.from_string(raw)

        assert date.raw == raw
        assert date.year is None
        assert date.month is None
        assert date.day is None
        assert date.to_date() is None

    def test_str_is_the_raw_value(self) -> None:
        assert str(GedcomDate.from_string("ABT 1890")) == "ABT 1890"

    def test_surrounding_whitespace_is_stripped(self) -> None:
        assert GedcomDate.from_string("  14 MAR 1890  ").raw == "14 MAR 1890"
