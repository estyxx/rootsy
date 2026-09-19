import pytest

from rootsy.parsers import MultimediaParser
from rootsy.types import ParsingContext
from tests.helpers import gedcom_lines


@pytest.fixture
def parser() -> MultimediaParser:
    """Return a fresh multimedia parser instance."""
    return MultimediaParser()


class TestMultimedia:
    def test_551_record_nests_form_under_file(self, parser: MultimediaParser) -> None:
        lines = gedcom_lines(
            """
            0 @M1@ OBJE
            1 FILE photos/giovanni.jpg
            2 FORM jpeg
            2 TITL Giovanni in 1912
            """,
        )

        multimedia, lines_consumed = parser.parse(lines, ParsingContext())

        assert multimedia.id == "@M1@"
        assert multimedia.file == "photos/giovanni.jpg"
        assert multimedia.format == "jpeg"
        assert multimedia.title == "Giovanni in 1912"
        assert lines_consumed == len(lines)

    def test_unknown_tags_are_kept(self, parser: MultimediaParser) -> None:
        lines = gedcom_lines(
            """
            0 @M1@ OBJE
            1 FILE photos/giovanni.jpg
            1 REFN 12
            1 CHAN
            2 DATE 22 DEC 2024
            """,
        )

        multimedia, lines_consumed = parser.parse(lines, ParsingContext())

        assert multimedia.file == "photos/giovanni.jpg"
        assert [line.tag for line in multimedia.unparsed] == ["REFN", "CHAN", "DATE"]
        assert lines_consumed == len(lines)

    def test_myheritage_photo_metadata(self, parser: MultimediaParser) -> None:
        """MyHeritage records when and where a photo was taken on the OBJE."""
        lines = gedcom_lines(
            """
            0 @I1@ INDI
            1 OBJE
            2 FILE photos/giovanni.jpg
            3 FORM jpg
            2 TITL Giovanni in uniform
            2 _DATE ABT 1915
            2 _PLACE Verona, Veneto, Italia
            2 _PRIM Y
            """,
        )

        multimedia, lines_consumed = parser.parse(lines[1:], ParsingContext())

        assert multimedia.title == "Giovanni in uniform"
        assert multimedia.date is not None
        assert multimedia.date.raw == "ABT 1915"
        assert multimedia.date.year == 1915
        assert multimedia.place == "Verona, Veneto, Italia"
        assert multimedia.primary is True
        assert lines_consumed == len(lines) - 1

    def test_a_photo_is_not_primary_unless_it_says_so(
        self,
        parser: MultimediaParser,
    ) -> None:
        lines = gedcom_lines("1 OBJE\n2 FILE photos/maria.jpg")

        multimedia, _ = parser.parse(lines, ParsingContext())

        assert multimedia.primary is False

    def test_the_remaining_vendor_tags_are_kept_by_name(
        self,
        parser: MultimediaParser,
    ) -> None:
        """A vendor tag means whatever its exporter says, so it stays a string."""
        lines = gedcom_lines(
            """
            1 OBJE
            2 FILE photos/giovanni.jpg
            2 _CUTOUT Y
            2 _PERSONALPHOTO Y
            2 _PARENTPHOTO @M9@
            2 _POSITION 0.12 0.30 0.44 0.61
            """,
        )

        multimedia, lines_consumed = parser.parse(lines, ParsingContext())

        assert multimedia.vendor == {
            "_CUTOUT": "Y",
            "_PERSONALPHOTO": "Y",
            "_PARENTPHOTO": "@M9@",
            "_POSITION": "0.12 0.30 0.44 0.61",
        }
        assert multimedia.unparsed == []
        assert lines_consumed == len(lines)

    def test_a_pointer_to_a_record_keeps_the_xref_it_points_at(
        self,
        parser: MultimediaParser,
    ) -> None:
        """`1 OBJE @M1@` says which object, without repeating what it holds."""
        lines = gedcom_lines("1 OBJE @M1@")

        multimedia, lines_consumed = parser.parse(lines, ParsingContext())

        assert multimedia.id == "@M1@"
        assert multimedia.file is None
        assert lines_consumed == 1

    def test_stops_at_the_next_record(self, parser: MultimediaParser) -> None:
        lines = gedcom_lines(
            """
            0 @M1@ OBJE
            1 FILE photos/giovanni.jpg
            0 @M2@ OBJE
            1 FILE photos/maria.jpg
            """,
        )

        multimedia, lines_consumed = parser.parse(lines, ParsingContext())

        assert multimedia.id == "@M1@"
        assert multimedia.file == "photos/giovanni.jpg"
        assert lines_consumed == 2
