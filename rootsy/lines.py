"""Helpers for reading a structure out of a flat sequence of `GedcomLine`."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rootsy.types import GedcomLine


def substructure_length(lines: Sequence[GedcomLine], start: int) -> int:
    """Count the line at `start` and every line nested under it."""
    length = 1
    while (
        start + length < len(lines) and lines[start + length].level > lines[start].level
    ):
        length += 1
    return length


def joined_text(lines: Sequence[GedcomLine]) -> str:
    """Join a value with its CONT (new line) and CONC (same line) continuations."""
    text = lines[0].value
    for line in lines[1:]:
        match line.tag:
            case "CONT":
                text = f"{text}\n{line.value}"
            case "CONC":
                text = f"{text}{line.value}"
    return text


def non_continuation_lines(lines: Sequence[GedcomLine]) -> list[GedcomLine]:
    """Take the substructure of `lines[0]`, minus the continuations of its value."""
    return [line for line in lines[1:] if line.tag not in {"CONC", "CONT"}]
