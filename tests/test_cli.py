"""The `rootsy` command line, run as a user runs it."""

import json
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

# Wide enough that rich never wraps a line of output mid-word.
WIDE_TERMINAL = {"COLUMNS": "200"}


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
