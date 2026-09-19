from typing import TYPE_CHECKING, Any, ClassVar

import attrs

from rootsy.adapters import GedcomParser
from rootsy.models import GedcomDate, Multimedia

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rootsy.types import GedcomLine, ParsingContext


@attrs.frozen
class MultimediaParser(GedcomParser[Multimedia]):
    """Parser for the OBJE record, inline on a record or at level 0.

    5.5.1 nests FORM under FILE while 5.5 keeps both under OBJE, so the tags are
    matched wherever they sit in the record.
    """

    handles_tag: ClassVar[str] = Multimedia.tag

    def parse(
        self,
        lines: Sequence[GedcomLine],
        context: ParsingContext,
    ) -> tuple[Multimedia, int]:
        """Parse a multimedia record from its first line."""
        data: dict[str, Any] = {"unparsed": [], "vendor": {}}
        lines_consumed = 0

        i = 0
        while i < len(lines):
            line = lines[i]

            # If we've returned to the record's level or higher, we're done
            if i > 0 and line.level <= lines[0].level:
                break

            context.enter_level(line)
            lines_consumed += 1

            match line.tag:
                case "OBJE":
                    # `0 @M1@ OBJE` names a record and `1 OBJE @M1@` points at
                    # one; either way the xref says which object this is.
                    data["id"] = line.xref or line.value or None
                case "FILE":
                    data["file"] = line.value
                case "FORM":
                    data["format"] = line.value
                case "TITL":
                    data["title"] = line.value
                case "_DATE":
                    data["date"] = GedcomDate.from_string(line.value)
                case "_PLACE":
                    data["place"] = line.value
                case "_PRIM":
                    data["primary"] = line.value.strip().upper() == "Y"
                case tag if tag.startswith("_"):
                    data["vendor"][tag] = line.value
                # REFN, RIN, CHAN, NOTE, … everything the spec defines here.
                case _:
                    data["unparsed"].append(line)

            i += 1

        return Multimedia(**data), lines_consumed
