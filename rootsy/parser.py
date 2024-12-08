from typing import TextIO, Generator, Tuple

from .models import GedcomStructure, Individual, Family, Event, EventType
from .validators import validate_gedcom_version


class GedcomParser:
    @classmethod
    def parse(cls, file_path: str) -> GedcomStructure:
        """
        Primary parsing method for GEDCOM files

        Args:
            file_path (str): Path to the GEDCOM file

        Returns:
            GedcomStructure: Parsed genealogical data
        """
        with open(file_path, encoding="utf-8") as gedcom_file:
            # First, validate the GEDCOM version
            validate_gedcom_version(gedcom_file)

            # Reset file pointer
            gedcom_file.seek(0)

            # Create structure to hold parsed data
            structure = GedcomStructure()

            # Process file line by line
            current_individual = None
            current_family = None

            for level, tag, value in cls._parse_lines(gedcom_file):
                # Top-level parsing logic
                if tag == "INDI":
                    if current_individual:
                        structure.add_individual(current_individual)
                    current_individual = Individual(id=value, name="")
                elif tag == "FAM":
                    if current_family:
                        structure.add_family(current_family)
                    current_family = Family(id=value)

                # Individual-level parsing
                if current_individual:
                    current_individual = cls._parse_individual_record(
                        current_individual, level, tag, value
                    )

                # Family-level parsing
                if current_family:
                    current_family = cls._parse_family_record(
                        current_family, level, tag, value
                    )

            # Add final individual and family
            if current_individual:
                structure.add_individual(current_individual)
            if current_family:
                structure.add_family(current_family)

            return structure

    @staticmethod
    def _parse_lines(file: TextIO) -> Generator[Tuple[int, str, str], None, None]:
        """
        Generator to parse GEDCOM file lines

        Args:
            file (TextIO): File object to parse

        Yields:
            Tuple[int, str, str]: Level, tag, and value for each line
        """
        for line in file:
            line = line.strip()
            parts = line.split(maxsplit=2)

            # Handle varying GEDCOM line formats
            if len(parts) < 2:
                continue

            level = int(parts[0])
            tag = parts[1].upper()
            value = parts[2] if len(parts) > 2 else ""

            yield level, tag, value

    @staticmethod
    def _parse_individual_record(
        individual: Individual, level: int, tag: str, value: str
    ) -> Individual:
        """
        Parse individual-specific records
        """
        if tag == "NAME":
            individual.name = value
            # Advanced name parsing
            name_parts = value.split("/")
            if len(name_parts) > 1:
                individual.given_name = name_parts[0].strip()
                individual.surname = name_parts[1].strip()

        elif tag == "SEX":
            individual.sex = value

        # Event parsing (simplified)
        event_mapping = {
            "BIRT": EventType.BIRTH,
            "DEAT": EventType.DEATH,
            "BAPM": EventType.BAPTISM,
        }

        if tag in event_mapping:
            event = Event(type=event_mapping[tag])
            individual.events.append(event)

        return individual

    @staticmethod
    def _parse_family_record(
        family: Family, level: int, tag: str, value: str
    ) -> Family:
        """
        Parse family-specific records
        """
        if tag == "HUSB":
            family.husband = value
        elif tag == "WIFE":
            family.wife = value
        elif tag == "CHIL":
            family.children.append(value)

        return family
