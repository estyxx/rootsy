import datetime
from typing import Any

import attrs

from rootsy.models import Family, Header, Individual


@attrs.define(slots=True, kw_only=True)
class GedcomStructure:
    """A class to represent the structure of a GEDCOM file."""

    header: Header
    individuals: dict[str, Individual] = attrs.field(factory=dict)
    families: dict[str, Family] = attrs.field(factory=dict)

    def add_individual(self, individual: Individual) -> None:
        """Add an individual to the GedcomStructure."""
        self.individuals[individual.id] = individual

    def add_family(self, family: Family) -> None:
        """Add a family to the GedcomStructure."""
        self.families[family.id] = family

    def to_dict(self) -> dict[str, Any]:
        """Convert the GedcomStructure to a dictionary."""
        return attrs.asdict(
            self,
            value_serializer=lambda _, __, value: value.isoformat()
            if isinstance(value, datetime.datetime)
            else value,
        )
