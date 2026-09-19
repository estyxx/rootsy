"""`GedcomReader`: the file on disk turned into lines and records."""

from typing import TYPE_CHECKING

import pytest

from rootsy.exceptions import GedcomFileNotFoundError, NotAGedcomFileError, RootsyError
from rootsy.reader import GedcomReader

if TYPE_CHECKING:
    from pathlib import Path

SNIPPET = """0 HEAD
1 GEDC
2 VERS 5.5.1
0 @N1@ NOTE some text
1 CONC  that continues
0 TRLR
"""


@pytest.fixture
def gedcom_file(tmp_path: Path) -> Path:
    """Write the snippet above to a file and return its path."""
    path = tmp_path / "sample.ged"
    path.write_text(SNIPPET, encoding="utf-8")
    return path


class TestLineGroups:
    def test_groups_start_at_each_level_zero_line(self, gedcom_file: Path) -> None:
        groups = list(GedcomReader(gedcom_file).line_groups())

        assert [[line.tag for line in group] for group in groups] == [
            ["HEAD", "GEDC", "VERS"],
            ["NOTE", "CONC"],
            ["TRLR"],
        ]

    def test_lines_know_which_line_of_the_file_they_are(
        self,
        gedcom_file: Path,
    ) -> None:
        groups = list(GedcomReader(gedcom_file).line_groups())

        assert [line.line_number for group in groups for line in group] == [
            1,
            2,
            3,
            4,
            5,
            6,
        ]

    def test_a_record_keeps_its_xref_and_value(self, gedcom_file: Path) -> None:
        note = next(
            group
            for group in GedcomReader(gedcom_file).line_groups()
            if group[0].tag == "NOTE"
        )[0]

        assert note.xref == "@N1@"
        assert note.value == "some text"

    def test_blank_lines_are_skipped_without_shifting_line_numbers(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "blanks.ged"
        path.write_text("0 HEAD\n\n1 CHAR UTF-8\n", encoding="utf-8")

        lines = [line for group in GedcomReader(path).line_groups() for line in group]

        assert [(line.tag, line.line_number) for line in lines] == [
            ("HEAD", 1),
            ("CHAR", 3),
        ]


class TestReaderErrors:
    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(GedcomFileNotFoundError):
            GedcomReader(tmp_path / "nope.ged")

    def test_missing_file_is_still_a_file_not_found_error(self, tmp_path: Path) -> None:
        """Callers catching the builtin keep working."""
        with pytest.raises(FileNotFoundError):
            GedcomReader(tmp_path / "nope.ged")

    def test_directory(self, tmp_path: Path) -> None:
        with pytest.raises(NotAGedcomFileError):
            GedcomReader(tmp_path)

    def test_every_reader_error_is_a_rootsy_error(self, tmp_path: Path) -> None:
        with pytest.raises(RootsyError):
            GedcomReader(tmp_path)
