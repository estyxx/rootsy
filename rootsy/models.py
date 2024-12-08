from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum, auto
from datetime import date


class EventType(Enum):
    BIRTH = auto()
    DEATH = auto()
    MARRIAGE = auto()
    DIVORCE = auto()
    BAPTISM = auto()


@dataclass
class Event:
    type: EventType
    date: Optional[date] = None
    place: Optional[str] = None
    additional_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Individual:
    id: str
    name: str
    given_name: Optional[str] = None
    surname: Optional[str] = None
    sex: Optional[str] = None
    events: List[Event] = field(default_factory=list)
    parents: List[str] = field(default_factory=list)
    spouse_families: List[str] = field(default_factory=list)


@dataclass
class Family:
    id: str
    husband: Optional[str] = None
    wife: Optional[str] = None
    children: List[str] = field(default_factory=list)
    marriage_event: Optional[Event] = None
    divorce_event: Optional[Event] = None


class GedcomStructure:
    def __init__(self):
        self.individuals: Dict[str, Individual] = {}
        self.families: Dict[str, Family] = {}

    def add_individual(self, individual: Individual):
        self.individuals[individual.id] = individual

    def add_family(self, family: Family):
        self.families[family.id] = family

    def to_dict(self) -> Dict[str, Any]:
        return {
            "individuals": {k: vars(v) for k, v in self.individuals.items()},
            "families": {k: vars(v) for k, v in self.families.items()},
        }
