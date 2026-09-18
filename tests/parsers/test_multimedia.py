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
            1 _PRIM Y
            1 CHAN
            2 DATE 22 DEC 2024
            """,
        )

        multimedia, lines_consumed = parser.parse(lines, ParsingContext())

        assert multimedia.file == "photos/giovanni.jpg"
        assert [line.tag for line in multimedia.unparsed] == ["_PRIM", "CHAN", "DATE"]
        assert lines_consumed == len(lines)

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
