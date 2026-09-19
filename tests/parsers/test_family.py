import datetime

import pytest

from rootsy.models import EventType
from rootsy.parsers import FamilyParser
from rootsy.types import ParsingContext
from tests.helpers import gedcom_lines


@pytest.fixture
def parser() -> FamilyParser:
    """Return a fresh family parser instance."""
    return FamilyParser()


class TestFamily:
    def test_full_record(self, parser: FamilyParser) -> None:
        lines = gedcom_lines(
            """
            0 @F1@ FAM
            1 HUSB @I1@
            1 WIFE @I2@
            1 CHIL @I3@
            1 CHIL @I4@
            1 MARR
            2 DATE 14 JUN 1919
            2 PLAC Verona, Veneto, Italy
            1 DIV
            2 DATE ABT 1930
            """,
        )

        family, lines_consumed = parser.parse(lines, ParsingContext())

        assert family.id == "@F1@"
        assert family.husband == "@I1@"
        assert family.wife == "@I2@"
        assert family.children == ["@I3@", "@I4@"]
        assert lines_consumed == len(lines)

        assert family.marriage_event is not None
        assert family.marriage_event.type is EventType.MARRIAGE
        assert family.marriage_event.place == "Verona, Veneto, Italy"
        assert family.marriage_event.date is not None
        assert family.marriage_event.date.to_date() == datetime.date(1919, 6, 14)

        assert family.divorce_event is not None
        assert family.divorce_event.type is EventType.DIVORCE
        assert family.divorce_event.date is not None
        assert family.divorce_event.date.raw == "ABT 1930"
        assert family.divorce_event.date.to_date() is None

    def test_without_events(self, parser: FamilyParser) -> None:
        lines = gedcom_lines(
            """
            0 @F1@ FAM
            1 HUSB @I1@
            """,
        )

        family, _ = parser.parse(lines, ParsingContext())

        assert family.marriage_event is None
        assert family.divorce_event is None
        assert family.children == []

    def test_marriage_without_detail(self, parser: FamilyParser) -> None:
        """`MARR Y` asserts the marriage happened without giving any detail."""
        lines = gedcom_lines(
            """
            0 @F1@ FAM
            1 MARR Y
            1 CHIL @I3@
            """,
        )

        family, lines_consumed = parser.parse(lines, ParsingContext())

        assert family.marriage_event is not None
        assert family.marriage_event.date is None
        assert family.children == ["@I3@"]
        assert lines_consumed == len(lines)

    def test_stops_at_the_next_record(self, parser: FamilyParser) -> None:
        lines = gedcom_lines(
            """
            0 @F1@ FAM
            1 MARR
            2 DATE 14 JUN 1919
            0 @F2@ FAM
            1 HUSB @I9@
            """,
        )

        family, lines_consumed = parser.parse(lines, ParsingContext())

        assert family.id == "@F1@"
        assert family.husband is None
        assert lines_consumed == 3

    def test_a_generic_event_is_kept_with_its_type(
        self,
        parser: FamilyParser,
    ) -> None:
        """A family event with no tag of its own says what it was in TYPE."""
        lines = gedcom_lines(
            """
            0 @F1@ FAM
            1 EVEN
            2 TYPE Engagement
            2 DATE 2 MAY 1918
            1 EVEN
            2 TYPE Census
            2 DATE 1921
            1 MARR
            2 DATE 14 JUN 1919
            """,
        )

        family, lines_consumed = parser.parse(lines, ParsingContext())

        assert [event.custom_type for event in family.events] == [
            "Engagement",
            "Census",
        ]
        assert all(event.type is EventType.OTHER for event in family.events)
        assert family.marriage_event is not None
        assert family.unparsed == []
        assert lines_consumed == len(lines)

    def test_the_uid_is_read_and_the_other_vendor_tags_are_named(
        self,
        parser: FamilyParser,
    ) -> None:
        lines = gedcom_lines(
            """
            0 @F1@ FAM
            1 _UID 9B3E7C
            1 RIN 12
            1 _UPD 12 JUN 2020 09:15:00 GMT-5
            """,
        )

        family, lines_consumed = parser.parse(lines, ParsingContext())

        assert family.uid == "9B3E7C"
        assert family.vendor == {
            "RIN": "12",
            "_UPD": "12 JUN 2020 09:15:00 GMT-5",
        }
        assert family.unparsed == []
        assert lines_consumed == len(lines)

    def test_unknown_tags_are_kept(self, parser: FamilyParser) -> None:
        """Nothing the spec defines here, or a vendor added, may be dropped."""
        lines = gedcom_lines(
            """
            0 @F1@ FAM
            1 HUSB @I1@
            1 NCHI 2
            1 SLGS
            2 DATE 14 JUN 1919
            1 _CUSTOM 1234
            """,
        )

        family, lines_consumed = parser.parse(lines, ParsingContext())

        assert family.husband == "@I1@"
        assert [line.tag for line in family.unparsed] == [
            "NCHI",
            "SLGS",
            "DATE",
            "_CUSTOM",
        ]
        assert lines_consumed == len(lines)

    def test_the_fam_line_itself_is_not_unparsed(self, parser: FamilyParser) -> None:
        family, _ = parser.parse(gedcom_lines("0 @F1@ FAM"), ParsingContext())

        assert family.id == "@F1@"
        assert family.unparsed == []
