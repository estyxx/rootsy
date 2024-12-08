import pytest

from rootsy.parser import GedcomParser
from rootsy.models import EventType


def test_gedcom_parser_basic_parsing(tmp_path):
    # Create a simple GEDCOM test file
    test_gedcom_content = """0 HEAD
1 GEDC
2 VERS 5.5.1
0 @I1@ INDI
1 NAME John /Doe/
1 SEX M
1 BIRT
2 DATE 1 JAN 1970
0 @F1@ FAM
1 HUSB @I1@
0 TRLR"""

    # Write test file
    test_file = tmp_path / "test.ged"
    test_file.write_text(test_gedcom_content)

    # Parse the file
    parsed_structure = GedcomParser.parse(str(test_file))

    # Assertions
    assert len(parsed_structure.individuals) == 1
    assert len(parsed_structure.families) == 1

    individual = list(parsed_structure.individuals.values())[0]
    assert individual.name == "John /Doe/"
    assert individual.given_name == "John"
    assert individual.surname == "Doe"
    assert individual.sex == "M"

    # Check events
    assert len(individual.events) == 1
    birth_event = individual.events[0]
    assert birth_event.type == EventType.BIRTH


def test_invalid_gedcom_version(tmp_path):
    # Create a GEDCOM file with unsupported version
    invalid_gedcom_content = """0 HEAD
1 GEDC
2 VERS 5.5.0
0 TRLR"""

    # Write test file
    test_file = tmp_path / "invalid.ged"
    test_file.write_text(invalid_gedcom_content)

    # Ensure validation fails
    with pytest.raises(Exception):
        GedcomParser.parse(str(test_file))
