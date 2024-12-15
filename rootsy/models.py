import datetime
from enum import Enum, auto
from typing import Any

from attrs import field, frozen


class EventType(Enum):
    """Enum representing the types of events in a GEDCOM file."""

    BIRTH = auto()
    DEATH = auto()
    MARRIAGE = auto()
    DIVORCE = auto()
    BAPTISM = auto()


@frozen(slots=True, kw_only=True)
class Event:
    """Represents an event related to an individual or family."""

    type: EventType
    date: datetime.date | None = None
    place: str | None = None
    additional_details: dict[str, Any] = field(default_factory=dict)


@frozen(slots=True, kw_only=True)
class Individual:
    """Represents an individual (INDI tag) extracted from a GEDCOM file.

    The Individual class is a compilation of facts or hypothesized facts about a person.
    """

    id: str
    name: str
    given_name: str | None = None
    surname: str | None = None
    sex: str | None = None
    events: list[Event] = field(default_factory=list)
    parents: list[str] = field(default_factory=list)
    spouse_families: list[str] = field(default_factory=list)


@frozen(slots=True, kw_only=True)
class Family:
    """Represents a family record extracted from GEDCOM files.

    This class models a family structure, including partners (husband and wife),
    children, and significant events such as marriage and divorce. It supports
    various family configurations and relationships, reflecting the diversity of
    human family structures.
    """

    id: str
    husband: str | None = None
    wife: str | None = None
    children: list[str] = field(default_factory=list)
    marriage_event: Event | None = None
    divorce_event: Event | None = None


class GedcomStructure:
    """A class to represent the structure of a GEDCOM file."""

    def __init__(self) -> None:
        """Initialize with empty individuals and families dictionaries."""
        self.individuals: dict[str, Individual] = {}
        self.families: dict[str, Family] = {}

    def add_individual(self, individual: Individual) -> None:
        """Add an individual to the GedcomStructure."""
        self.individuals[individual.id] = individual

    def add_family(self, family: Family) -> None:
        """Add a family to the GedcomStructure."""
        self.families[family.id] = family

    def to_dict(self) -> dict[str, Any]:
        """Convert the GedcomStructure to a dictionary."""
        return {
            "individuals": {k: vars(v) for k, v in self.individuals.items()},
            "families": {k: vars(v) for k, v in self.families.items()},
        }
