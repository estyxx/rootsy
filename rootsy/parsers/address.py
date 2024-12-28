from collections.abc import Sequence
from typing import ClassVar

import attrs

from rootsy.adapters import GedcomParser
from rootsy.models import Address
from rootsy.types import GedcomLine, ParsingContext


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
