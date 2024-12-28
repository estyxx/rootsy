from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rootsy.types import GedcomLine

if TYPE_CHECKING:
    from collections.abc import Iterator


class GedcomReader:
    """Reads and groups GEDCOM lines maintaining hierarchical structure."""

    def __init__(self, file_path: str | Path) -> None:
        """Initialize the reader with a file path."""
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            msg = f"GEDCOM file not found: {file_path}"
            raise FileNotFoundError(msg)
        if not self.file_path.is_file():
            msg = f"Path is not a file: {file_path}"
            raise ValueError(msg)

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
            for line in f:
                if (line := line.strip()) and (parsed := GedcomLine.from_string(line)):
                    yield parsed
