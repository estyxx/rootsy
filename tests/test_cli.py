"""The `rootsy` command line, run as a user runs it."""

import json
import re
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from rootsy.cli import app

if TYPE_CHECKING:
    from pathlib import Path

# A file with one person, one family and three level-0 records rootsy skips.
SAMPLE = """0 HEAD
1 GEDC
2 VERS 5.5.1
0 @I1@ INDI
1 NAME Ada /Lovelace/
1 FAMS @F1@
0 @F1@ FAM
1 HUSB @I2@
1 WIFE @I1@
0 @N1@ NOTE a note record
0 @SUBM1@ SUBM
1 NAME Someone
0 @R1@ REPO
1 NAME An archive
0 TRLR
"""

# A file whose records carry tags rootsy reads but has no field for.
UNPARSED_SAMPLE = """0 HEAD
1 GEDC
2 VERS 5.5.1
0 @I1@ INDI
1 NAME Ada /Lovelace/
1 OBJE
2 FILE ada.jpg
1 CHAN
0 @I2@ INDI
1 NAME Grace /Hopper/
1 OBJE
2 FILE grace.jpg
1 _UID 8F6A
0 @F1@ FAM
1 SLGS
0 @N1@ NOTE a note record
0 @N2@ NOTE another note
0 @R1@ REPO
0 TRLR
"""

# Wide enough that rich never wraps a line of output mid-word.
WIDE_TERMINAL = {"COLUMNS": "200"}

# A row of one of the tables `rootsy coverage` prints: a label, then its count.
TABLE_ROW = re.compile(r"│ (?P<label>\S[^│]*?) +│ +(?P<count>\d+) │")


def table_rows(output: str) -> list[tuple[str, int]]:
    """Read back the rows of every table in a command's output."""
    return [(row["label"], int(row["count"])) for row in TABLE_ROW.finditer(output)]


@pytest.fixture
def runner() -> CliRunner:
    """Return a runner that keeps stdout and stderr apart."""
    return CliRunner(env=WIDE_TERMINAL)


@pytest.fixture
def gedcom_file(tmp_path: Path) -> Path:
    """Write the sample GEDCOM to a file and return its path."""
    path = tmp_path / "sample.ged"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


@pytest.fixture
def unparsed_file(tmp_path: Path) -> Path:
    """Write the GEDCOM full of unmodelled tags and return its path."""
    path = tmp_path / "unparsed.ged"
    path.write_text(UNPARSED_SAMPLE, encoding="utf-8")
    return path


class TestExport:
    def test_writes_the_structure_as_json(
        self,
        runner: CliRunner,
        gedcom_file: Path,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "sample.json"

        result = runner.invoke(app, ["export", str(gedcom_file), "--out", str(out)])

        assert result.exit_code == 0
        exported = json.loads(out.read_text(encoding="utf-8"))
        assert exported["individuals"]["@I1@"]["surname"] == "Lovelace"
        assert list(exported["families"]) == ["@F1@"]

    def test_indent_controls_the_layout(
        self,
        runner: CliRunner,
        gedcom_file: Path,
        tmp_path: Path,
    ) -> None:
        indented = tmp_path / "indented.json"
        flat = tmp_path / "flat.json"

        runner.invoke(
            app,
            ["export", str(gedcom_file), "--out", str(indented), "--indent", "4"],
        )
        runner.invoke(
            app,
            ["export", str(gedcom_file), "--out", str(flat), "--indent", "0"],
        )

        assert '\n    "header"' in indented.read_text(encoding="utf-8")
        assert flat.read_text(encoding="utf-8").count("\n") == 1

    def test_reports_what_it_wrote(
        self,
        runner: CliRunner,
        gedcom_file: Path,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "sample.json"

        result = runner.invoke(app, ["export", str(gedcom_file), "--out", str(out)])

        assert "1 individual, 1 family, 3 records skipped" in result.stdout

    def test_unwritable_destination_exits_non_zero(
        self,
        runner: CliRunner,
        gedcom_file: Path,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "no-such-directory" / "sample.json"

        result = runner.invoke(app, ["export", str(gedcom_file), "--out", str(out)])

        assert result.exit_code == 1
        assert "error:" in result.stderr


class TestAnonymisedExport:
    def test_replaces_the_people_in_the_file(
        self,
        runner: CliRunner,
        gedcom_file: Path,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "anonymous.json"

        result = runner.invoke(
            app,
            ["export", str(gedcom_file), "--out", str(out), "--anonymise"],
        )

        assert result.exit_code == 0
        text = out.read_text(encoding="utf-8")
        assert "Lovelace" not in text
        assert json.loads(text)["individuals"]["@I1@"]["surname"] == "Surname1"

    def test_the_american_spelling_works_too(
        self,
        runner: CliRunner,
        gedcom_file: Path,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "anonymous.json"

        result = runner.invoke(
            app,
            ["export", str(gedcom_file), "--out", str(out), "--anonymize"],
        )

        assert result.exit_code == 0
        assert "Lovelace" not in out.read_text(encoding="utf-8")

    def test_dates_says_how_much_of_each_date_to_keep(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        source = tmp_path / "dated.ged"
        source.write_text(
            "0 HEAD\n1 GEDC\n2 VERS 5.5.1\n"
            "0 @I1@ INDI\n1 BIRT\n2 DATE 12 JUL 1920\n0 TRLR\n",
            encoding="utf-8",
        )
        out = tmp_path / "anonymous.json"

        runner.invoke(
            app,
            [
                "export",
                str(source),
                "--out",
                str(out),
                "--anonymise",
                "--dates",
                "remove",
            ],
        )

        birth = json.loads(out.read_text(encoding="utf-8"))
        assert birth["individuals"]["@I1@"]["events"][0]["date"] is None

    def test_the_file_is_written_as_it_was_without_the_flag(
        self,
        runner: CliRunner,
        gedcom_file: Path,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "plain.json"

        runner.invoke(app, ["export", str(gedcom_file), "--out", str(out)])

        assert "Lovelace" in out.read_text(encoding="utf-8")


class TestStats:
    def test_counts_records(self, runner: CliRunner, gedcom_file: Path) -> None:
        result = runner.invoke(app, ["stats", str(gedcom_file)])

        assert result.exit_code == 0
        assert "Individuals │     1" in result.stdout
        assert "Families    │     1" in result.stdout
        assert "Skipped     │     3" in result.stdout

    def test_names_the_tags_it_skipped(
        self,
        runner: CliRunner,
        gedcom_file: Path,
    ) -> None:
        result = runner.invoke(app, ["stats", str(gedcom_file)])

        assert "Skipped: NOTE x1, REPO x1, SUBM x1" in result.stdout


class TestCoverage:
    def test_counts_the_unparsed_tags_of_each_record_type(
        self,
        runner: CliRunner,
        unparsed_file: Path,
    ) -> None:
        result = runner.invoke(app, ["coverage", str(unparsed_file)])

        assert result.exit_code == 0
        rows = table_rows(result.stdout)
        assert ("INDI > OBJE", 2) in rows
        assert ("INDI > OBJE > FILE", 2) in rows
        assert ("FAM > SLGS", 1) in rows
        assert ("HEAD > GEDC", 1) in rows

    def test_orders_the_tags_of_a_record_type_by_frequency(
        self,
        runner: CliRunner,
        unparsed_file: Path,
    ) -> None:
        result = runner.invoke(app, ["coverage", str(unparsed_file)])

        individuals = [
            row for row in table_rows(result.stdout) if row[0].startswith("INDI")
        ]
        assert individuals == [
            ("INDI > OBJE", 2),
            ("INDI > OBJE > FILE", 2),
            ("INDI > CHAN", 1),
            ("INDI > _UID", 1),
        ]

    def test_says_how_many_records_of_a_type_held_something_unparsed(
        self,
        runner: CliRunner,
        unparsed_file: Path,
    ) -> None:
        result = runner.invoke(app, ["coverage", str(unparsed_file)])

        assert "INDI: 6 unparsed lines in 2 of 2 records" in result.stdout

    def test_counts_the_level_0_records_no_parser_claimed(
        self,
        runner: CliRunner,
        unparsed_file: Path,
    ) -> None:
        result = runner.invoke(app, ["coverage", str(unparsed_file)])

        rows = table_rows(result.stdout)
        assert ("NOTE", 2) in rows
        assert ("REPO", 1) in rows

    def test_reports_the_totals(
        self,
        runner: CliRunner,
        unparsed_file: Path,
    ) -> None:
        result = runner.invoke(app, ["coverage", str(unparsed_file)])

        assert "8 unparsed lines, 3 records skipped" in result.stdout

    def test_draws_a_bar_per_tag(
        self,
        runner: CliRunner,
        unparsed_file: Path,
    ) -> None:
        result = runner.invoke(app, ["coverage", str(unparsed_file)])

        assert "█" in result.stdout

    def test_a_file_with_nothing_unparsed_prints_no_table(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "parsed.ged"
        path.write_text("0 @I1@ INDI\n1 SEX F\n0 TRLR\n", encoding="utf-8")

        result = runner.invoke(app, ["coverage", str(path)])

        assert result.exit_code == 0
        assert "0 unparsed lines, 0 records skipped" in result.stdout
        assert table_rows(result.stdout) == []

    def test_missing_file_exits_non_zero(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        result = runner.invoke(app, ["coverage", str(tmp_path / "nowhere.ged")])

        assert result.exit_code != 0


class TestErrors:
    def test_unsupported_version_exits_non_zero(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "old.ged"
        path.write_text("0 HEAD\n1 GEDC\n2 VERS 4.0\n0 TRLR\n", encoding="utf-8")

        result = runner.invoke(app, ["stats", str(path)])

        assert result.exit_code == 1
        assert "Unsupported GEDCOM version '4.0'" in result.stderr

    def test_missing_file_exits_non_zero(
        self,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        result = runner.invoke(app, ["stats", str(tmp_path / "nowhere.ged")])

        assert result.exit_code != 0
