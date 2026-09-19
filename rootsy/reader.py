from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rootsy.exceptions import GedcomFileNotFoundError, NotAGedcomFileError
from rootsy.types import GedcomLine

if TYPE_CHECKING:
    from collections.abc import Iterator


class GedcomReader:
    """Reads and groups GEDCOM lines maintaining hierarchical structure."""

    def __init__(self, file_path: str | Path) -> None:
        """Initialize the reader with a file path."""
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise GedcomFileNotFoundError(file_path)
        if not self.file_path.is_file():
            raise NotAGedcomFileError(file_path)

    def line_groups(self) -> Iterator[list[GedcomLine]]:
        """Yield groups of related lines that form a complete record.

        Each group starts with a level 0 line and includes all its children.
        """
        current_group: list[GedcomLine] = []

        for line in self._read_lines():
            if line.level == 0 and current_group:
                yield current_group
                current_group = []
            current_group.append(line)

        if current_group:
            yield current_group

    def _read_lines(self) -> Iterator[GedcomLine]:
        """Read and parse individual GEDCOM lines."""
        with self.file_path.open(encoding="utf-8-sig") as f:
            for number, line in enumerate(f, start=1):
                if parsed := GedcomLine.from_string(line, line_number=number):
                    yield parsed
