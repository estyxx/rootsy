import pytest

from rootsy.adapters import ParsingContext
from rootsy.parsers import AddressParser
from rootsy.types import GedcomLine


@pytest.fixture
def parser() -> AddressParser:
    """Return a fresh header parser instance."""
    return AddressParser()


class TestAddress:
    def test_complete_address_551(self, parser: AddressParser) -> None:
        """Test parsing a complete address in GEDCOM 5.5.1 format."""
        lines = [
            "1 ADDR 123 Genealogy St.",
            "2 CONT Springfield, IL 62701",
            "2 CONT USA",
            "2 ADR1 123 Genealogy St.",
            "2 ADR2 Suite 100",
            "2 ADR3 Floor 3",
            "2 CITY Springfield",
            "2 STAE IL",
            "2 POST 62701",
            "2 CTRY USA",
            "2 PHON +1-800-555-1234",
            "2 PHON +1-800-555-5678",
            "2 EMAIL support@example.com",
            "2 EMAIL contact@example.com",
            "2 FAX +1-800-555-9012",
            "2 WWW www.example.com",
        ]

        gedcom_lines = [GedcomLine.from_string(line) for line in lines]
        address, lines_consumed = parser.parse(gedcom_lines, ParsingContext())

        # Verify all fields are parsed correctly
        assert address.full == "123 Genealogy St.\nSpringfield, IL 62701\nUSA"
        assert address.line1 == "123 Genealogy St."
        assert address.line2 == "Suite 100"
        assert address.line3 == "Floor 3"
        assert address.city == "Springfield"
        assert address.state == "IL"
        assert address.postal_code == "62701"
        assert address.country == "USA"
        assert address.phone == ["+1-800-555-1234", "+1-800-555-5678"]
        assert address.email == ["support@example.com", "contact@example.com"]
        assert address.fax == ["+1-800-555-9012"]
        assert address.web == "www.example.com"
        assert lines_consumed == len(lines)

    def test_complete_address_70(self, parser: AddressParser) -> None:
        """Test parsing a complete address in GEDCOM 7.0 format."""
        lines = [
            "2 ADR1 123 Genealogy St.",
            # 7.0 uses comma-separated format
            "1 ADDR 123 Genealogy St., Springfield, IL 62701, USA",
            "2 CITY Springfield",
            "2 STAE IL",
            "2 POST 62701",
            "2 CTRY USA",
            "2 PHON +1-800-555-1234",
            "2 EMAIL support@example.com",
            "2 WWW https://www.example.com",  # 7.0 tends to use full URLs
        ]

        gedcom_lines = [GedcomLine.from_string(line) for line in lines]
        address, lines_consumed = parser.parse(gedcom_lines, ParsingContext())

        assert address.full == "123 Genealogy St., Springfield, IL 62701, USA"
        assert address.line1 == "123 Genealogy St."
        assert address.city == "Springfield"
        assert address.state == "IL"
        assert address.postal_code == "62701"
        assert address.country == "USA"
        assert address.phone == ["+1-800-555-1234"]
        assert address.email == ["support@example.com"]
        assert address.web == "https://www.example.com"
        assert lines_consumed == len(lines)

    def test_minimal_address(self, parser: AddressParser) -> None:
        """Test parsing an address with only the required full address line."""
        lines = [
            "1 ADDR 123 Genealogy St, Springfield IL",
        ]

        gedcom_lines = [GedcomLine.from_string(line) for line in lines]
        address, lines_consumed = parser.parse(gedcom_lines, ParsingContext())

        assert address.full == "123 Genealogy St, Springfield IL"
        assert address.line1 is None
        assert address.line2 is None
        assert address.line3 is None
        assert address.city is None
        assert address.state is None
        assert address.postal_code is None
        assert address.country is None
        assert address.phone == []
        assert address.email == []
        assert address.fax == []
        assert address.web is None
        assert lines_consumed == 1

    def test_address_with_continuations(self, parser: AddressParser) -> None:
        """Test parsing an address with multiple continuation lines."""
        lines = [
            "1 ADDR The Tall Building",
            "2 CONT 123 Long Street",
            "2 CONT Floor 45, Suite 4502",
            "2 CONT Springfield, IL 62701",
            "2 CONT United States of America",
        ]

        gedcom_lines = [GedcomLine.from_string(line) for line in lines]
        address, lines_consumed = parser.parse(gedcom_lines, ParsingContext())

        expected_full = (
            "The Tall Building\n"
            "123 Long Street\n"
            "Floor 45, Suite 4502\n"
            "Springfield, IL 62701\n"
            "United States of America"
        )

        assert address.full == expected_full
        assert lines_consumed == len(lines)

    def test_empty_fields(self, parser: AddressParser) -> None:
        """Test parsing an address with empty field values."""
        lines = [
            "1 ADDR",  # Empty main address
            "2 ADR1 ",  # Empty line1
            "2 CITY   ",  # Just whitespace
            "2 EMAIL",  # Empty email
        ]

        gedcom_lines = [GedcomLine.from_string(line) for line in lines]
        address, lines_consumed = parser.parse(gedcom_lines, ParsingContext())

        assert address.full == ""
        assert address.line1 == ""
        assert address.city == ""
        assert address.email == [""]
        assert lines_consumed == len(lines)
