"""Every exception rootsy raises, rooted at `RootsyError`."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


class RootsyError(Exception):
    """Base class for every error rootsy raises."""


class ParserNotFoundError(RootsyError):
    """No parser is registered for a tag or tag path."""

    def __init__(self, tag: str) -> None:
        self.tag = tag
        super().__init__(f"No parser found for tag {tag}")


class UnsupportedGedcomVersionError(RootsyError, ValueError):
    """The file declares a GEDCOM version rootsy does not implement."""

    def __init__(self, version: str, supported: Sequence[str]) -> None:
        self.version = version
        self.supported = tuple(supported)
        super().__init__(
            f"Unsupported GEDCOM version {version!r}. "
            f"Supported versions are {_readable_list(self.supported)}",
        )


class GedcomFileNotFoundError(RootsyError, FileNotFoundError):
    """The path handed to the reader does not exist."""

    def __init__(self, file_path: Path | str) -> None:
        self.file_path = file_path
        super().__init__(f"GEDCOM file not found: {file_path}")


class NotAGedcomFileError(RootsyError, ValueError):
    """The path handed to the reader exists but is not a file."""

    def __init__(self, file_path: Path | str) -> None:
        self.file_path = file_path
        super().__init__(f"Path is not a file: {file_path}")


def _readable_list(items: Sequence[str]) -> str:
    """Join items as `a`, `a and b`, `a, b and c`."""
    if len(items) < 2:  # noqa: PLR2004
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"
