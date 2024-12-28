from datetime import datetime

import pytest

from rootsy.adapters import ParsingContext
from rootsy.parsers import HeaderParser
from rootsy.types import GedcomLine


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
        assert header.transmission_date == datetime(2024, 12, 22, 0, 0)
        assert header.copyright is None
        assert header.source
        assert header.source.system_id == "MyGenealogySoftware"
        assert header.source.version == "1.0"
        assert header.source.name == "My Family History Software"
        assert header.source.corporation == "MyGenealogyCompany"
        assert header.source.data_name is None
