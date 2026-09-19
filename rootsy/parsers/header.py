from collections.abc import Sequence
from typing import Any, ClassVar

import attrs

from rootsy.adapters import GedcomParser
from rootsy.models import GedcomDate, Header, HeaderSource
from rootsy.registry import get_parser_for_path
from rootsy.types import GedcomLine, ParsingContext


@attrs.frozen
class HeaderParser(GedcomParser[Header]):
    """Parser for the GEDCOM header record."""

    handles_tag: ClassVar[str] = Header.tag

    def parse(
        self,
        lines: Sequence[GedcomLine],
        context: ParsingContext,
    ) -> tuple[Header, int]:
        """Parse the header record and all its substructures."""
        data: dict[str, Any] = {
            "encoding": "UTF-8",  # default value
            "unparsed": [],
        }
        lines_consumed = 0

        # Process each line
        i = 0
        while i < len(lines):
            line = lines[i]

            # If we've hit another top-level record, we're done
            if i > 0 and line.level == 0:
                break

            # Update context
            context.enter_level(line)
            lines_consumed += 1

            match line.tag:
                case "HEAD":
                    pass  # the record's own line, nothing to read off it

                case "VERS" if context.path[-2:-1] == ("GEDC",):
                    data["version"] = line.value

                case "SOUR":
                    # Delegate to the header's source parser, reached by path
                    # because a level-0 SOUR is a source record instead.
                    if source_parser := get_parser_for_path(context.path):
                        source_result, source_lines = source_parser.parse(
                            lines[i:],
                            context,
                        )
                        data["source"] = source_result
                        lines_consumed += source_lines - 1
                        i += source_lines - 1

                case "CHAR":
                    data["encoding"] = line.value
                case "LANG":
                    data["language"] = line.value
                case "DEST":
                    data["destination"] = line.value
                case "DATE":
                    data["transmission_date"] = GedcomDate.from_string(line.value)
                case "COPR":
                    data["copyright"] = line.value
                # GEDC, FILE, SUBM, PLAC, NOTE, SCHMA, … and vendor extensions.
                case _:
                    data["unparsed"].append(line)

            i += 1

        return Header(**data), lines_consumed


@attrs.frozen
class HeaderSourceParser(GedcomParser[HeaderSource]):
    """Parser for header source information."""

    handles_tag: ClassVar[str] = HeaderSource.tag
    handles_path: ClassVar[tuple[str, ...]] = HeaderSource.tag_path

    def parse(
        self,
        lines: Sequence[GedcomLine],
        context: ParsingContext,
    ) -> tuple[HeaderSource, int]:
        data: dict[str, Any] = {
            "system_id": lines[0].value,  # SOUR line value
            "unparsed": [],
        }
        lines_consumed = 0

        i = 0
        while i < len(lines):
            line = lines[i]

            # If we've returned to source's level or higher, we're done
            if i > 0 and line.level <= lines[0].level:
                break

            context.enter_level(line)
            lines_consumed += 1

            match line.tag:
                case "SOUR":
                    pass  # the structure's own line, read as `system_id` above
                case "VERS":
                    data["version"] = line.value
                case "NAME":
                    data["name"] = line.value
                case "CORP":
                    data["corporation"] = line.value
                case "DATA":
                    data["data_name"] = line.value
                case "ADDR":
                    # Delegate to address parser
                    if addr_parser := get_parser_for_path(context.path):
                        addr_result, addr_lines = addr_parser.parse(
                            lines[i:],
                            context,
                        )
                        data["address"] = addr_result
                        lines_consumed += addr_lines - 1
                        i += addr_lines - 1
                # PHON, EMAIL, WWW next to CORP, DATE and COPR under DATA, …
                case _:
                    data["unparsed"].append(line)

            i += 1

        return HeaderSource(**data), lines_consumed
