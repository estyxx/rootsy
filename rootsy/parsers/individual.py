from collections.abc import Sequence
from typing import Any, ClassVar

from rootsy.adapters import GedcomParser
from rootsy.models import Individual
from rootsy.types import GedcomLine, ParsingContext


class IndividualParser(GedcomParser[Individual]):
    handles_tag: ClassVar[str] = "INDI"

    def parse(
        self,
        lines: Sequence[GedcomLine],
        context: ParsingContext,
    ) -> tuple[Individual, int]:
        data: dict[str, Any] = {}
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
                case "NAME":
                    data["name"] = line.value

        return Individual(**data), lines_consumed
