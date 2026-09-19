from typing import TYPE_CHECKING, Any, ClassVar

import attrs

from rootsy.adapters import GedcomParser
from rootsy.lines import joined_text, non_continuation_lines, substructure_length
from rootsy.models import SourceRecord
from rootsy.parsers.vendor import RECORD_TAGS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rootsy.types import GedcomLine, ParsingContext

# SOUR substructures held as text, by the field of `SourceRecord` they fill.
TEXT_FIELDS = {
    "TITL": "title",
    "AUTH": "author",
    "PUBL": "publication",
    "TEXT": "text",
}


@attrs.frozen
class SourceRecordParser(GedcomParser[SourceRecord]):
    """Parser for the level-0 SOUR record.

    Only the fields a citation needs to name a source are modelled so far; DATA,
    REPO and the rest of the record are kept in `unparsed`.
    """

    handles_tag: ClassVar[str] = SourceRecord.tag

    def parse(
        self,
        lines: Sequence[GedcomLine],
        context: ParsingContext,
    ) -> tuple[SourceRecord, int]:
        """Parse a source record from its first line."""
        data: dict[str, Any] = {"id": lines[0].xref, "vendor": {}, "unparsed": []}
        level = lines[0].level
        context.enter_level(lines[0])

        i = 1
        while i < len(lines) and lines[i].level > level:
            line = lines[i]
            context.enter_level(line)
            # The line plus every line nested under it.
            span = lines[i : i + substructure_length(lines, i)]

            match line.tag:
                case "_UID":
                    data["uid"] = line.value
                case tag if tag in RECORD_TAGS:
                    data["vendor"][tag] = line.value
                case tag if (field := TEXT_FIELDS.get(tag)) is not None:
                    data[field] = joined_text(span) or None
                    # DATE and PLAC under PUBL, SOUR under TEXT, …
                    data["unparsed"].extend(non_continuation_lines(span))
                case _:
                    data["unparsed"].extend(span)

            i += len(span)

        return SourceRecord(**data), i
