import datetime

import pytest

from rootsy.adapters import ParsingContext
from rootsy.models import HeaderSource
from rootsy.parsers import HeaderParser
from rootsy.types import GedcomLine
from tests.helpers import gedcom_lines


@pytest.fixture
def parser() -> HeaderParser:
    """Return a fresh header parser instance."""
    return HeaderParser()


class TestHeaderValidation:
    """Test header validation and error cases."""

    def test_invalid_version_raises_error(self, parser: HeaderParser) -> None:
        """Test that invalid version number raises appropriate error."""
        lines = [
            "0 HEAD",
            "1 GEDC",
            "2 VERS 6.0",  # Invalid version
        ]
        gedcom_lines = [GedcomLine.from_string(line) for line in lines]
        expected_error = (
            "Unsupported GEDCOM version '6.0'. Supported versions are 5.5.1 and 7.0"
        )
        with pytest.raises(
            ValueError,
            match=expected_error,
        ):
            parser.parse(gedcom_lines, ParsingContext())


class TestHeaderIntegration:
    """Integration tests using real GEDCOM files."""

    def test_real_v7_header(self, parser: HeaderParser, sample_header_70: str) -> None:
        """Test parsing a real 7.0 header file."""
        lines = [
            GedcomLine.from_string(line)
            for line in sample_header_70.splitlines()
            if line.strip()
        ]

        header, _ = parser.parse(lines, ParsingContext())

        assert header.version == "7.0"
        assert header.encoding == "UTF-8"
        # Add more specific assertions based on your sample file

    def test_real_v551_header(
        self,
        parser: HeaderParser,
        sample_header_551: str,
    ) -> None:
        """Test parsing a real 5.5.1 header file."""
        lines = [
            GedcomLine.from_string(line)
            for line in sample_header_551.splitlines()
            if line.strip()
        ]

        header, _ = parser.parse(lines, ParsingContext())

        assert header.version == "5.5.1"
        assert header.encoding == "UTF-8"
        assert header.destination == "AnotherGenealogySoftware"
        assert header.transmission_date is not None
        assert header.transmission_date.raw == "22 DEC 2024"
        assert header.transmission_date.to_date() == datetime.date(2024, 12, 22)
        assert header.copyright is None
        assert header.source
        assert header.source.system_id == "MyGenealogySoftware"
        assert header.source.version == "1.0"
        assert header.source.name == "My Family History Software"
        assert header.source.corporation == "MyGenealogyCompany"
        assert header.source.data_name is None


class TestHeaderUnparsed:
    """Nothing the spec defines under HEAD, or a vendor added, may be dropped."""

    def test_unknown_tags_are_kept(self, parser: HeaderParser) -> None:
        lines = gedcom_lines(
            """
            0 HEAD
            1 GEDC
            2 VERS 5.5.1
            2 FORM LINEAGE-LINKED
            1 CHAR UTF-8
            1 FILE myfamily.ged
            1 SUBM @U1@
            1 _MH_CUSTOM Y
            """,
        )

        header, lines_consumed = parser.parse(lines, ParsingContext())

        assert header.version == "5.5.1"
        assert header.encoding == "UTF-8"
        assert [line.tag for line in header.unparsed] == [
            "GEDC",
            "FORM",
            "FILE",
            "SUBM",
            "_MH_CUSTOM",
        ]
        assert lines_consumed == len(lines)

    def test_the_head_line_itself_is_not_unparsed(self, parser: HeaderParser) -> None:
        header, _ = parser.parse(
            gedcom_lines("0 HEAD\n1 GEDC\n2 VERS 7.0"),
            ParsingContext(),
        )

        assert [line.tag for line in header.unparsed] == ["GEDC"]

    def test_the_source_substructure_keeps_what_it_cannot_place(
        self,
        parser: HeaderParser,
    ) -> None:
        lines = gedcom_lines(
            """
            0 HEAD
            1 SOUR MyGenealogySoftware
            2 VERS 1.0
            2 CORP MyGenealogyCompany
            3 PHON +1-800-555-1234
            1 GEDC
            2 VERS 5.5.1
            """,
        )

        header, lines_consumed = parser.parse(lines, ParsingContext())

        assert isinstance(header.source, HeaderSource)
        assert header.source.corporation == "MyGenealogyCompany"
        assert [line.tag for line in header.source.unparsed] == ["PHON"]
        assert [line.tag for line in header.unparsed] == ["GEDC"]
        assert lines_consumed == len(lines)
