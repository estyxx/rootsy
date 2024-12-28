from typing import ClassVar

from rootsy.adapters import GedcomRecord


class Multimedia(GedcomRecord):
    tag: ClassVar[str] = "OBJE"
