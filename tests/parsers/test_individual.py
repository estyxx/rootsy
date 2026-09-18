import datetime

import pytest

from rootsy.models import EventType
from rootsy.parsers import IndividualParser
from rootsy.types import ParsingContext
from tests.helpers import gedcom_lines


@pytest.fixture
def parser() -> IndividualParser:
    """Return a fresh individual parser instance."""
    return IndividualParser()


class TestIndividual:
    def test_full_record(self, parser: IndividualParser) -> None:
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 NAME Giovanni /Rossi/
            2 GIVN Giovanni
            2 SURN Rossi
            1 SEX M
            1 BIRT
            2 DATE 14 MAR 1890
            2 PLAC Verona, Veneto, Italy
            1 DEAT
            2 DATE 3 FEB 1954
            1 FAMS @F1@
            1 FAMC @F2@
            1 EMAIL giovanni@example.com
            """,
        )

        individual, lines_consumed = parser.parse(lines, ParsingContext())

        assert individual.id == "@I1@"
        assert individual.name == "Giovanni /Rossi/"
        assert individual.given_name == "Giovanni"
        assert individual.surname == "Rossi"
        assert individual.sex == "M"
        assert individual.email == "giovanni@example.com"
        assert individual.spouse_in_families == ["@F1@"]
        assert individual.child_of_families == ["@F2@"]
        assert lines_consumed == len(lines)

    def test_birth_and_death_properties(self, parser: IndividualParser) -> None:
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 BIRT
            2 DATE 14 MAR 1890
            2 PLAC Verona
            1 DEAT
            2 DATE 3 FEB 1954
            2 PLAC Milano
            """,
        )

        individual, _ = parser.parse(lines, ParsingContext())

        assert [event.type for event in individual.events] == [
            EventType.BIRTH,
            EventType.DEATH,
        ]
        assert individual.birth is not None
        assert individual.birth.place == "Verona"
        assert individual.birth.date is not None
        assert individual.birth.date.to_date() == datetime.date(1890, 3, 14)
        assert individual.death is not None
        assert individual.death.place == "Milano"

    def test_missing_events(self, parser: IndividualParser) -> None:
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 NAME Giovanni /Rossi/
            """,
        )

        individual, _ = parser.parse(lines, ParsingContext())

        assert individual.events == []
        assert individual.birth is None
        assert individual.death is None

    def test_residence_is_an_event_too(self, parser: IndividualParser) -> None:
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 RESI
            2 DATE 1920
            2 PLAC Verona
            """,
        )

        individual, lines_consumed = parser.parse(lines, ParsingContext())

        assert [event.type for event in individual.events] == [EventType.RESIDENCE]
        assert lines_consumed == len(lines)

    def test_several_family_links(self, parser: IndividualParser) -> None:
        """FAMC and FAMS may both appear more than once, and never mix."""
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 FAMS @F1@
            1 FAMS @F2@
            1 FAMC @F3@
            """,
        )

        individual, _ = parser.parse(lines, ParsingContext())

        assert individual.spouse_in_families == ["@F1@", "@F2@"]
        assert individual.child_of_families == ["@F3@"]

    def test_unknown_tags_are_kept(self, parser: IndividualParser) -> None:
        """Nothing the spec defines here, or a vendor added, may be dropped."""
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 NAME Giovanni /Rossi/
            1 _UID 4E2F0B9C
            1 RIN 42
            1 OCCU Farmer
            1 SEX M
            """,
        )

        individual, lines_consumed = parser.parse(lines, ParsingContext())

        assert individual.sex == "M"
        assert [line.tag for line in individual.unparsed] == [
            "_UID",
            "RIN",
            "OCCU",
        ]
        assert lines_consumed == len(lines)

    def test_the_indi_line_itself_is_not_unparsed(
        self,
        parser: IndividualParser,
    ) -> None:
        individual, _ = parser.parse(gedcom_lines("0 @I1@ INDI"), ParsingContext())

        assert individual.id == "@I1@"
        assert individual.unparsed == []

    def test_stops_at_the_next_record(self, parser: IndividualParser) -> None:
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 NAME Giovanni /Rossi/
            0 @I2@ INDI
            1 NAME Maria /Bianchi/
            """,
        )

        individual, lines_consumed = parser.parse(lines, ParsingContext())

        assert individual.id == "@I1@"
        assert lines_consumed == 2


class TestNameParts:
    @pytest.mark.parametrize(
        ("name", "given_name", "surname"),
        [
            ("Giovanni /Rossi/", "Giovanni", "Rossi"),
            ("Giovanni Battista /Rossi/", "Giovanni Battista", "Rossi"),
            ("Giovanni /Rossi/ Jr", "Giovanni", "Rossi"),
            ("/Rossi/", None, "Rossi"),
            ("Giovanni //", "Giovanni", None),
            ("Giovanni", "Giovanni", None),
            ("", None, None),
        ],
    )
    def test_derived_from_the_slashed_form(
        self,
        parser: IndividualParser,
        name: str,
        given_name: str | None,
        surname: str | None,
    ) -> None:
        """Without GIVN/SURN the parts come from the NAME value itself."""
        individual, _ = parser.parse(
            gedcom_lines(f"0 @I1@ INDI\n1 NAME {name}"),
            ParsingContext(),
        )

        assert individual.name == (name or "")
        assert individual.given_name == given_name
        assert individual.surname == surname

    def test_substructures_win_over_the_slashed_form(
        self,
        parser: IndividualParser,
    ) -> None:
        """GIVN/SURN are authoritative; NAME keeps the raw value."""
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 NAME Giovanni /Rossi/
            2 GIVN Gianni
            2 SURN Rossi-Bianchi
            """,
        )

        individual, _ = parser.parse(lines, ParsingContext())

        assert individual.name == "Giovanni /Rossi/"
        assert individual.given_name == "Gianni"
        assert individual.surname == "Rossi-Bianchi"
