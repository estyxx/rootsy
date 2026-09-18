from __future__ import annotations

import logging
from pathlib import Path

from rootsy.models import GedcomStructure
from rootsy.reader import GedcomReader
from rootsy.registry import get_parser_for_path
from rootsy.types import GedcomLine, ParsingContext

logger = logging.getLogger(__name__)


def parse_gedcom(file_path: Path | str) -> GedcomStructure:
    """Parse a complete GEDCOM file.

    A level-0 record rootsy has no parser for is logged and skipped, so one
    unknown tag never costs the rest of the file.
    """
    reader = GedcomReader(Path(file_path))
    structure = GedcomStructure()

    for line_group in reader.line_groups():
        first_line = line_group[0]

        if first_line.tag == "TRLR":
            break

        parser = get_parser_for_path((first_line.tag,))
        if parser is None:
            logger.warning(
                "No parser for level-0 tag %s%s; skipping the record",
                first_line.tag,
                _at_line(first_line),
            )
            continue

        result, _ = parser.parse(line_group, ParsingContext())

        match first_line.tag:
            case "HEAD":
                structure.header = result
            case "INDI":
                structure.add_individual(result)
            case "FAM":
                structure.add_family(result)
            case "SOUR":
                structure.add_source(result)
            case _:
                logger.debug(
                    "Parsed a %s record%s, which GedcomStructure has no home for yet",
                    first_line.tag,
                    _at_line(first_line),
                )

    return structure


def _at_line(line: GedcomLine) -> str:
    """Name the line a message is about, when the reader knows its number."""
    return "" if line.line_number is None else f" at line {line.line_number}"
