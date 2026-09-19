import pytest

from rootsy.parsers import SourceRecordParser
from rootsy.types import ParsingContext
from tests.helpers import gedcom_lines


@pytest.fixture
def parser() -> SourceRecordParser:
    """Return a fresh source record parser instance."""
    return SourceRecordParser()


class TestSourceRecord:
    def test_full_record(self, parser: SourceRecordParser) -> None:
        lines = gedcom_lines(
            """
            0 @S1@ SOUR
            1 TITL Birth Certificate of Jane Smith
            1 AUTH Registrar of Births
            1 PUBL London, 1985
            1 TEXT Jane Smith, born 15 March 1985.
            """,
        )

        source, lines_consumed = parser.parse(lines, ParsingContext())

        assert source.id == "@S1@"
        assert source.title == "Birth Certificate of Jane Smith"
        assert source.author == "Registrar of Births"
        assert source.publication == "London, 1985"
        assert source.text == "Jane Smith, born 15 March 1985."
        assert source.unparsed == []
        assert lines_consumed == len(lines)

    def test_missing_optional_tags(self, parser: SourceRecordParser) -> None:
        lines = gedcom_lines(
            """
            0 @S2@ SOUR
            1 TITL Parish register
            """,
        )

        source, lines_consumed = parser.parse(lines, ParsingContext())

        assert source.id == "@S2@"
        assert source.title == "Parish register"
        assert source.author is None
        assert source.publication is None
        assert source.text is None
        assert lines_consumed == 2

    def test_text_joins_its_continuations(self, parser: SourceRecordParser) -> None:
        lines = gedcom_lines(
            """
            0 @S1@ SOUR
            1 TITL A long ti
            2 CONC tle
            1 TEXT First line.
            2 CONT Second line.
            """,
        )

        source, lines_consumed = parser.parse(lines, ParsingContext())

        assert source.title == "A long title"
        assert source.text == "First line.\nSecond line."
        assert source.unparsed == []
        assert lines_consumed == len(lines)

    def test_unknown_and_nested_tags_are_kept(
        self,
        parser: SourceRecordParser,
    ) -> None:
        """DATA, REPO and vendor extensions have no field yet, so nothing drops."""
        lines = gedcom_lines(
            """
            0 @S1@ SOUR
            1 TITL Birth register
            1 PUBL
            2 DATE 16 MAR 1985
            1 DATA
            2 EVEN BIRT
            3 DATE FROM 1980 TO 1990
            1 REPO @R1@
            1 _CUSTOM 1234
            """,
        )

        source, lines_consumed = parser.parse(lines, ParsingContext())

        assert source.title == "Birth register"
        assert source.publication is None  # `1 PUBL` with no value on the line
        assert [line.tag for line in source.unparsed] == [
            "DATE",
            "DATA",
            "EVEN",
            "DATE",
            "REPO",
            "_CUSTOM",
        ]
        assert lines_consumed == len(lines)

    def test_the_uid_is_read_and_the_other_vendor_tags_are_named(
        self,
        parser: SourceRecordParser,
    ) -> None:
        lines = gedcom_lines(
            """
            0 @S1@ SOUR
            1 TITL Birth register
            1 _UID 7C4A20
            1 RIN 3
            1 _UPD 12 JUN 2020 09:15:00 GMT-5
            """,
        )

        source, lines_consumed = parser.parse(lines, ParsingContext())

        assert source.uid == "7C4A20"
        assert source.vendor == {
            "RIN": "3",
            "_UPD": "12 JUN 2020 09:15:00 GMT-5",
        }
        assert source.unparsed == []
        assert lines_consumed == len(lines)

    def test_stops_at_the_next_record(self, parser: SourceRecordParser) -> None:
        lines = gedcom_lines(
            """
            0 @S1@ SOUR
            1 TITL Birth register
            0 @S2@ SOUR
            1 TITL Marriage register
            """,
        )

        source, lines_consumed = parser.parse(lines, ParsingContext())

        assert source.id == "@S1@"
        assert source.title == "Birth register"
        assert lines_consumed == 2

    def test_a_record_without_an_xref(self, parser: SourceRecordParser) -> None:
        """A malformed export may leave the record unidentified; do not crash."""
        source, _ = parser.parse(
            gedcom_lines("0 SOUR\n1 TITL Nameless"),
            ParsingContext(),
        )

        assert source.id is None
        assert source.title == "Nameless"
