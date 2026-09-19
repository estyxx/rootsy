import logging
from typing import TYPE_CHECKING

import pytest

from rootsy.models import (
    EventType,
    HeaderSource,
    SourceRecord,
    UnsupportedGedcomVersionError,
)
from rootsy.parser import parse_gedcom

if TYPE_CHECKING:
    from pathlib import Path


def write_gedcom(tmp_path: Path, content: str) -> Path:
    """Write a GEDCOM snippet to a file and return its path."""
    path = tmp_path / "test.ged"
    path.write_text(content, encoding="utf-8")
    return path


def test_gedcom_parser_basic_parsing(tmp_path: Path) -> None:
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
    parsed_structure = parse_gedcom(str(test_file))

    # Assertions
    assert len(parsed_structure.individuals) == 1
    assert len(parsed_structure.families) == 1

    individual = next(iter(parsed_structure.individuals.values()))
    assert individual.name == "John /Doe/"
    assert individual.given_name == "John"
    assert individual.surname == "Doe"
    assert individual.sex == "M"

    # Check events
    assert len(individual.events) == 1
    birth_event = individual.events[0]
    assert birth_event.type == EventType.BIRTH


def test_invalid_gedcom_version(tmp_path: Path) -> None:
    # Create a GEDCOM file with unsupported version
    invalid_gedcom_content = """0 HEAD
1 GEDC
2 VERS 5.5.0
0 TRLR"""

    # Write test file
    test_file = tmp_path / "invalid.ged"
    test_file.write_text(invalid_gedcom_content)

    # Ensure validation fails
    with pytest.raises(UnsupportedGedcomVersionError):
        parse_gedcom(str(test_file))


class TestUnknownRecords:
    """An unhandled level-0 tag costs its own record and nothing else."""

    def test_unknown_tag_is_skipped(self, tmp_path: Path) -> None:
        path = write_gedcom(
            tmp_path,
            """0 HEAD
1 GEDC
2 VERS 5.5.1
0 @U1@ SUBM
1 NAME John Doe
0 @I1@ INDI
1 NAME Giovanni /Rossi/
0 TRLR
""",
        )

        structure = parse_gedcom(path)

        assert sorted(structure.individuals) == ["@I1@"]
        assert structure.header is not None

    def test_a_skipped_record_is_named_on_the_structure(
        self,
        tmp_path: Path,
    ) -> None:
        path = write_gedcom(
            tmp_path,
            """0 HEAD
1 GEDC
2 VERS 5.5.1
0 @U1@ SUBM
1 NAME John Doe
0 @N1@ NOTE a note record
0 TRLR
""",
        )

        structure = parse_gedcom(path)

        assert [(record.tag, record.line_number) for record in structure.skipped] == [
            ("SUBM", 4),
            ("NOTE", 6),
        ]
        assert structure.skipped[0].xref == "@U1@"

    def test_unknown_tag_is_logged_with_its_line_number(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        path = write_gedcom(
            tmp_path,
            """0 HEAD
1 GEDC
2 VERS 5.5.1
0 @U1@ SUBM
1 NAME John Doe
0 TRLR
""",
        )

        with caplog.at_level(logging.WARNING, logger="rootsy.parser"):
            parse_gedcom(path)

        assert "SUBM" in caplog.text
        assert "line 4" in caplog.text

    def test_a_vendor_record_does_not_crash_the_file(self, tmp_path: Path) -> None:
        """MyHeritage writes level-0 tags no specification defines."""
        path = write_gedcom(
            tmp_path,
            """0 HEAD
1 GEDC
2 VERS 5.5.1
0 @X1@ _MH_EXTRA
1 _WHAT ever
0 @F1@ FAM
1 HUSB @I1@
0 TRLR
""",
        )

        structure = parse_gedcom(path)

        assert sorted(structure.families) == ["@F1@"]


class TestMissingHeader:
    def test_a_file_without_a_header_still_parses(self, tmp_path: Path) -> None:
        path = write_gedcom(
            tmp_path,
            """0 @I1@ INDI
1 NAME Giovanni /Rossi/
0 TRLR
""",
        )

        structure = parse_gedcom(path)

        assert structure.header is None
        assert structure.individuals["@I1@"].given_name == "Giovanni"

    def test_records_before_the_header_are_kept(self, tmp_path: Path) -> None:
        """A truncated export may put the header late, or not first."""
        path = write_gedcom(
            tmp_path,
            """0 @I1@ INDI
1 NAME Giovanni /Rossi/
0 HEAD
1 GEDC
2 VERS 5.5.1
0 TRLR
""",
        )

        structure = parse_gedcom(path)

        assert structure.header is not None
        assert structure.header.version == "5.5.1"
        assert sorted(structure.individuals) == ["@I1@"]

    def test_an_empty_file_gives_an_empty_structure(self, tmp_path: Path) -> None:
        structure = parse_gedcom(write_gedcom(tmp_path, ""))

        assert structure.header is None
        assert structure.individuals == {}
        assert structure.families == {}
        assert structure.sources == {}


class TestSourceRecords:
    def test_level_zero_sour_is_a_source_record(self, tmp_path: Path) -> None:
        """Not the header's source system, which `HeaderSourceParser` handles."""
        path = write_gedcom(
            tmp_path,
            """0 HEAD
1 SOUR Rootsy
2 VERS 0.1.0
1 GEDC
2 VERS 5.5.1
0 @S1@ SOUR
1 TITL Birth Certificate of Jane Smith
1 AUTH Registrar of Births
1 PUBL London, 1985
1 TEXT Jane Smith, born 15 March 1985.
0 TRLR
""",
        )

        structure = parse_gedcom(path)

        assert structure.header is not None
        assert isinstance(structure.header.source, HeaderSource)
        assert structure.header.source.system_id == "Rootsy"
        assert structure.header.source.version == "0.1.0"

        source = structure.sources["@S1@"]
        assert isinstance(source, SourceRecord)
        assert source.title == "Birth Certificate of Jane Smith"
        assert source.author == "Registrar of Births"
        assert source.publication == "London, 1985"
        assert source.text == "Jane Smith, born 15 March 1985."
