"""Helpers shared by the test suite."""

from rootsy.types import GedcomLine


def gedcom_lines(snippet: str) -> list[GedcomLine]:
    """Turn an inline GEDCOM snippet into the lines a parser expects."""
    return [
        line
        for raw in snippet.strip().splitlines()
        if (line := GedcomLine.from_string(raw.strip())) is not None
    ]
