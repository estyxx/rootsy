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

    def test_burial_is_an_event_too(self, parser: IndividualParser) -> None:
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 BURI
            2 DATE 5 FEB 1954
            2 PLAC Cimitero Monumentale, Verona
            """,
        )

        individual, lines_consumed = parser.parse(lines, ParsingContext())

        assert [event.type for event in individual.events] == [EventType.BURIAL]
        assert individual.events[0].place == "Cimitero Monumentale, Verona"
        assert lines_consumed == len(lines)

    def test_unknown_tags_are_kept(self, parser: IndividualParser) -> None:
        """Nothing the spec defines here, or a vendor added, may be dropped."""
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 NAME Giovanni /Rossi/
            1 REFN 4E2F0B9C
            1 CHAN
            2 DATE 22 DEC 2024
            1 SEX M
            """,
        )

        individual, lines_consumed = parser.parse(lines, ParsingContext())

        assert individual.sex == "M"
        assert [line.tag for line in individual.unparsed] == [
            "REFN",
            "CHAN",
            "DATE",
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


class TestAttributes:
    def test_occupations_are_collected_in_the_order_they_are_written(
        self,
        parser: IndividualParser,
    ) -> None:
        """OCCU may be written more than once; a person can change trade."""
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 OCCU Contadino
            1 OCCU Fornaio
            """,
        )

        individual, lines_consumed = parser.parse(lines, ParsingContext())

        assert individual.occupations == ["Contadino", "Fornaio"]
        assert lines_consumed == len(lines)

    def test_notes_join_their_continuations(self, parser: IndividualParser) -> None:
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 NOTE Emigrated to Argenti
            2 CONC na
            2 CONT and never came back.
            1 NOTE A second note.
            """,
        )

        individual, lines_consumed = parser.parse(lines, ParsingContext())

        assert individual.notes == [
            "Emigrated to Argentina\nand never came back.",
            "A second note.",
        ]
        assert individual.unparsed == []
        assert lines_consumed == len(lines)

    def test_the_name_prefix_and_married_name(
        self,
        parser: IndividualParser,
    ) -> None:
        """MyHeritage writes the name taken on marrying as `_MARNM`."""
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 NAME Maria /Bianchi/
            2 GIVN Maria
            2 SURN Bianchi
            2 NPFX Dott.ssa
            2 _MARNM Maria /Rossi/
            """,
        )

        individual, lines_consumed = parser.parse(lines, ParsingContext())

        assert individual.name == "Maria /Bianchi/"
        assert individual.surname == "Bianchi"
        assert individual.name_prefix == "Dott.ssa"
        assert individual.married_name == "Maria /Rossi/"
        assert individual.unparsed == []
        assert lines_consumed == len(lines)

    def test_source_citations_are_kept_as_raw_lines(
        self,
        parser: IndividualParser,
    ) -> None:
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 SOUR @S1@
            2 PAGE Register 4, page 12
            2 QUAY 3
            1 SEX M
            """,
        )

        individual, lines_consumed = parser.parse(lines, ParsingContext())

        assert [line.tag for line in individual.citations] == ["SOUR", "PAGE", "QUAY"]
        assert individual.citations[1].value == "Register 4, page 12"
        assert individual.sex == "M"
        assert lines_consumed == len(lines)


class TestStableIds:
    def test_the_uid_is_read_and_the_other_vendor_tags_are_named(
        self,
        parser: IndividualParser,
    ) -> None:
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 _UID 4F2C1AE7B9
            1 RIN 501
            1 _UPD 12 JUN 2020 09:15:00 GMT-5
            """,
        )

        individual, lines_consumed = parser.parse(lines, ParsingContext())

        assert individual.uid == "4F2C1AE7B9"
        assert individual.vendor == {
            "RIN": "501",
            "_UPD": "12 JUN 2020 09:15:00 GMT-5",
        }
        assert individual.unparsed == []
        assert lines_consumed == len(lines)

    def test_a_record_without_them_says_so(self, parser: IndividualParser) -> None:
        individual, _ = parser.parse(gedcom_lines("0 @I1@ INDI"), ParsingContext())

        assert individual.uid is None
        assert individual.vendor == {}


class TestMedia:
    def test_an_inline_object_becomes_a_multimedia_record(
        self,
        parser: IndividualParser,
    ) -> None:
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 NAME Giovanni /Rossi/
            1 OBJE
            2 FILE photos/giovanni.jpg
            3 FORM jpg
            2 TITL Giovanni in uniform
            2 _DATE ABT 1915
            2 _PLACE Verona
            2 _PRIM Y
            2 _CUTOUT Y
            1 SEX M
            """,
        )

        individual, lines_consumed = parser.parse(lines, ParsingContext())

        assert len(individual.media) == 1
        photo = individual.media[0]
        assert photo.file == "photos/giovanni.jpg"
        assert photo.format == "jpg"
        assert photo.title == "Giovanni in uniform"
        assert photo.date is not None
        assert photo.date.year == 1915
        assert photo.place == "Verona"
        assert photo.vendor == {"_CUTOUT": "Y"}
        # The OBJE owns its own lines and hands the rest back.
        assert individual.sex == "M"
        assert individual.unparsed == []
        assert lines_consumed == len(lines)

    def test_the_primary_photo_is_the_one_marked_prim(
        self,
        parser: IndividualParser,
    ) -> None:
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 OBJE
            2 FILE photos/group.jpg
            1 OBJE
            2 FILE photos/portrait.jpg
            2 _PRIM Y
            """,
        )

        individual, _ = parser.parse(lines, ParsingContext())

        assert [photo.file for photo in individual.media] == [
            "photos/group.jpg",
            "photos/portrait.jpg",
        ]
        assert individual.primary_photo is not None
        assert individual.primary_photo.file == "photos/portrait.jpg"

    def test_without_a_prim_the_first_photo_stands_in(
        self,
        parser: IndividualParser,
    ) -> None:
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 OBJE
            2 FILE photos/group.jpg
            1 OBJE
            2 FILE photos/portrait.jpg
            """,
        )

        individual, _ = parser.parse(lines, ParsingContext())

        assert individual.primary_photo is not None
        assert individual.primary_photo.file == "photos/group.jpg"

    def test_a_record_with_no_photo_has_no_primary_one(
        self,
        parser: IndividualParser,
    ) -> None:
        individual, _ = parser.parse(gedcom_lines("0 @I1@ INDI"), ParsingContext())

        assert individual.media == []
        assert individual.primary_photo is None
