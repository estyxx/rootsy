from __future__ import annotations

from pathlib import Path

from rootsy.models import GedcomStructure
from rootsy.reader import GedcomReader
from rootsy.registry import get_parser_for_tag
from rootsy.types import ParsingContext


def parse_gedcom(file_path: Path | str) -> GedcomStructure:
    """Parse a complete GEDCOM file."""
    reader = GedcomReader(Path(file_path))
    structure = None

    for line_group in reader.line_groups():
        first_line = line_group[0]

        if first_line.tag == "TRLR":
            break

        parser = get_parser_for_tag(first_line.tag)

        result, line_ = parser.parse(line_group, ParsingContext())

        match first_line.tag:
            case "HEAD":
                structure = GedcomStructure(header=result)
            case "INDI":
                structure.add_individual(result)
            case "FAM":
                structure.add_family(result)

    return structure
