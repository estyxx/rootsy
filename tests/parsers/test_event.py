import datetime

import pytest

from rootsy.models import EventType
from rootsy.parsers import EventParser
from rootsy.types import ParsingContext
from tests.helpers import gedcom_lines


@pytest.fixture
def parser() -> EventParser:
    """Return a fresh event parser instance."""
    return EventParser()


class TestEventDetail:
    def test_type_comes_from_the_tag(self, parser: EventParser) -> None:
        lines = gedcom_lines("1 MARR")

        event, lines_consumed = parser.parse(lines, ParsingContext())

        assert event.type is EventType.MARRIAGE
        assert event.date is None
        assert event.place is None
        assert lines_consumed == 1

    def test_date_and_place(self, parser: EventParser) -> None:
        lines = gedcom_lines(
            """
            1 BIRT
            2 DATE 14 MAR 1890
            2 PLAC Verona, Veneto, Italy
            """,
        )

        event, lines_consumed = parser.parse(lines, ParsingContext())

        assert event.type is EventType.BIRTH
        assert event.date is not None
        assert event.date.raw == "14 MAR 1890"
        assert event.date.to_date() == datetime.date(1890, 3, 14)
        assert event.place == "Verona, Veneto, Italy"
        assert lines_consumed == 3

    def test_qualified_date(self, parser: EventParser) -> None:
        lines = gedcom_lines(
            """
            1 DEAT
            2 DATE ABT 1954
            """,
        )

        event, _ = parser.parse(lines, ParsingContext())

        assert event.date is not None
        assert event.date.year == 1954
        assert event.date.to_date() is None

    def test_notes_join_their_continuations(self, parser: EventParser) -> None:
        lines = gedcom_lines(
            """
            1 BIRT
            2 NOTE Born at ho
            3 CONC me,
            3 CONT on a Sunday morning.
            2 NOTE A second note.
            """,
        )

        event, lines_consumed = parser.parse(lines, ParsingContext())

        assert event.notes == ["Born at home,\non a Sunday morning.", "A second note."]
        assert lines_consumed == 5

    def test_source_citations_are_kept_as_raw_lines(self, parser: EventParser) -> None:
        lines = gedcom_lines(
            """
            1 BIRT
            2 SOUR @S1@
            3 PAGE Register 4, page 12
            3 QUAY 3
            """,
        )

        event, lines_consumed = parser.parse(lines, ParsingContext())

        assert [line.tag for line in event.citations] == ["SOUR", "PAGE", "QUAY"]
        assert event.citations[1].value == "Register 4, page 12"
        assert lines_consumed == 4

    def test_cause_and_age(self, parser: EventParser) -> None:
        lines = gedcom_lines(
            """
            1 DEAT
            2 DATE 3 FEB 1954
            2 CAUS Polmo
            3 CONC nite
            2 AGE 64y
            """,
        )

        event, lines_consumed = parser.parse(lines, ParsingContext())

        assert event.cause == "Polmonite"
        assert event.age == "64y"
        assert event.unparsed == []
        assert lines_consumed == len(lines)

    def test_an_address_is_parsed_by_the_address_parser(
        self,
        parser: EventParser,
    ) -> None:
        lines = gedcom_lines(
            """
            1 RESI
            2 DATE 1920
            2 ADDR Via Mazzini 12
            3 CITY Verona
            3 POST 37121
            3 CTRY Italia
            2 EMAIL giovanni@example.com
            """,
        )

        event, lines_consumed = parser.parse(lines, ParsingContext())

        assert event.address is not None
        assert event.address.full == "Via Mazzini 12"
        assert event.address.city == "Verona"
        assert event.address.postal_code == "37121"
        assert event.address.country == "Italia"
        assert event.email == "giovanni@example.com"
        assert event.unparsed == []
        assert lines_consumed == len(lines)

    def test_a_generic_event_says_what_it_was(self, parser: EventParser) -> None:
        """`EVEN` has no meaning of its own; TYPE gives it one."""
        lines = gedcom_lines(
            """
            1 EVEN
            2 TYPE Engagement
            2 DATE 2 MAY 1918
            2 PLAC Verona
            """,
        )

        event, lines_consumed = parser.parse(lines, ParsingContext())

        assert event.type is EventType.OTHER
        assert event.custom_type == "Engagement"
        assert event.place == "Verona"
        assert lines_consumed == len(lines)

    def test_unknown_tags_are_kept(self, parser: EventParser) -> None:
        """Nothing the spec defines here, or a vendor added, may be dropped."""
        lines = gedcom_lines(
            """
            1 BIRT
            2 DATE 14 MAR 1890
            3 TIME 08:30
            2 PLAC Verona
            3 MAP
            4 LATI N45.438
            2 RELI Catholic
            2 _UID 1234
            """,
        )

        event, lines_consumed = parser.parse(lines, ParsingContext())

        assert event.date is not None
        assert event.place == "Verona"
        assert [line.tag for line in event.unparsed] == [
            "TIME",
            "MAP",
            "LATI",
            "RELI",
            "_UID",
        ]
        assert lines_consumed == 8

    def test_stops_at_the_end_of_its_own_structure(self, parser: EventParser) -> None:
        """An event owns its lines only, never the ones after them."""
        lines = gedcom_lines(
            """
            1 BIRT
            2 DATE 14 MAR 1890
            1 DEAT
            2 DATE 3 FEB 1954
            0 TRLR
            """,
        )

        event, lines_consumed = parser.parse(lines, ParsingContext())

        assert event.type is EventType.BIRTH
        assert lines_consumed == 2
