from collections.abc import Sequence
from datetime import datetime
from typing import Any, ClassVar

import attrs

from rootsy.adapters import GedcomParser
from rootsy.models import Address, Header, HeaderSource
from rootsy.registry import get_parser_for_tag
from rootsy.types import GedcomLine, ParsingContext


def parse_date(date_str: str) -> datetime:
    """Parse a DATE value into a datetime object."""
    try:
        return datetime.strptime(date_str, "%d %b %Y")
    except ValueError as e:
        msg = f"Invalid date format: {date_str}"
        raise ValueError(msg) from e


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
                case "VERS" if context.path[-2] == "GEDC":
                    data["version"] = line.value

                case "SOUR":
                    # Delegate to source parser
                    if source_parser := get_parser_for_tag("SOUR"):
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
                    data["transmission_date"] = parse_date(line.value)
                case "COPR":
                    data["copyright"] = line.value

            i += 1

        return Header(**data), lines_consumed


@attrs.frozen
class HeaderSourceParser(GedcomParser[HeaderSource]):
    """Parser for header source information."""

    handles_tag: ClassVar[str] = HeaderSource.tag

    def parse(
        self,
        lines: Sequence[GedcomLine],
        context: ParsingContext,
    ) -> tuple[HeaderSource, int]:
        data = {
            "system_id": lines[0].value,  # SOUR line value
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
                    if addr_parser := get_parser_for_tag("ADDR"):
                        addr_result, addr_lines = addr_parser.parse(
                            lines[i:],
                            context,
                        )
                        data["address"] = addr_result
                        lines_consumed += addr_lines - 1
                        i += addr_lines - 1

            i += 1

        return HeaderSource(**data), lines_consumed


@attrs.frozen
class AddressParser(GedcomParser[Address]):
    """Parser for address structures."""

    handles_tag: ClassVar[str] = Address.tag

    def parse(
        self,
        lines: Sequence[GedcomLine],
        context: ParsingContext,
    ) -> tuple[Address, int]:
        data = {
            "full": lines[0].value,
            "phone": [],
            "email": [],
            "fax": [],
        }
        lines_consumed = 0
        current_text: list[str] = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # If we've returned to address's level or higher, we're done
            if i > 0 and line.level <= lines[0].level:
                break

            context.enter_level(line)
            lines_consumed += 1

            match line.tag:
                case "CONT":
                    current_text.append(line.value)
                case "ADR1":
                    data["line1"] = line.value
                case "ADR2":
                    data["line2"] = line.value
                case "ADR3":
                    data["line3"] = line.value
                case "CITY":
                    data["city"] = line.value
                case "STAE":
                    data["state"] = line.value
                case "POST":
                    data["postal_code"] = line.value
                case "CTRY":
                    data["country"] = line.value
                case "PHON":
                    data["phone"].append(line.value)
                case "EMAIL":
                    data["email"].append(line.value)
                case "FAX":
                    data["fax"].append(line.value)
                case "WWW":
                    data["web"] = line.value

            i += 1

        # Join any continuation lines into full address
        if current_text:
            data["full"] = "\n".join([data["full"], *current_text])

        return Address(**data), lines_consumed
