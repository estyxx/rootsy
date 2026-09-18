"""End-to-end parsing of the sample files in `tests/fixtures`."""

import datetime
import json
import logging
from pathlib import Path

import pytest

from rootsy.models import EventType
from rootsy.parser import parse_gedcom


class TestSample551:
    def test_parses_end_to_end(self, sample_551_file: Path) -> None:
        structure = parse_gedcom(sample_551_file)

        assert structure.header.version == "5.5.1"
        assert structure.header.encoding == "UTF-8"
        assert structure.header.transmission_date is not None
        assert structure.header.transmission_date.to_date() == datetime.date(
            2024,
            12,
            22,
        )
        assert sorted(structure.individuals) == ["@I1@", "@I2@", "@I3@"]
        assert sorted(structure.families) == ["@F1@"]

    def test_individuals_keep_their_events_and_links(
        self,
        sample_551_file: Path,
    ) -> None:
        structure = parse_gedcom(sample_551_file)

        giovanni = structure.individuals["@I1@"]
        assert (giovanni.given_name, giovanni.surname) == ("Giovanni", "Rossi")
        assert giovanni.birth is not None
        assert giovanni.birth.date is not None
        assert giovanni.birth.date.year == 1890
        assert giovanni.birth.date.to_date() is None  # ABT 1890 is not exact
        assert giovanni.death is not None
        assert giovanni.death.date is not None
        assert giovanni.death.date.to_date() == datetime.date(1954, 2, 3)
        assert giovanni.spouse_in_families == ["@F1@"]
        assert giovanni.child_of_families == []

        luigi = structure.individuals["@I3@"]
        assert luigi.child_of_families == ["@F1@"]
        assert luigi.spouse_in_families == []
        assert luigi.birth is not None
        assert luigi.birth.notes == ["Registered three days later."]

    def test_family_keeps_its_marriage(self, sample_551_file: Path) -> None:
        family = parse_gedcom(sample_551_file).families["@F1@"]

        assert (family.husband, family.wife) == ("@I1@", "@I2@")
        assert family.children == ["@I3@"]
        assert family.marriage_event is not None
        assert family.marriage_event.type is EventType.MARRIAGE
        assert family.marriage_event.date is not None
        assert family.marriage_event.date.to_date() == datetime.date(1919, 6, 14)

    def test_to_dict_serialises_dates_as_their_raw_string(
        self,
        sample_551_file: Path,
    ) -> None:
        as_dict = parse_gedcom(sample_551_file).to_dict()

        assert as_dict["header"]["transmission_date"] == "22 DEC 2024"

        birth = as_dict["individuals"]["@I1@"]["events"][0]
        assert birth["type"] == "BIRT"
        assert birth["date"] == "ABT 1890"
        assert as_dict["families"]["@F1@"]["marriage_event"]["date"] == "14 JUN 1919"

    def test_to_dict_is_plain_json(self, sample_551_file: Path) -> None:
        """Everything a consumer gets must survive `json.dumps` untouched."""
        as_dict = parse_gedcom(sample_551_file).to_dict()

        assert json.loads(json.dumps(as_dict)) == as_dict


class TestSample70:
    """A 7.0 file carries SUBM and REPO records rootsy has no parser for."""

    def test_parses_end_to_end(self, sample_70_file: Path) -> None:
        structure = parse_gedcom(sample_70_file)

        assert structure.header is not None
        assert structure.header.version == "7.0"
        assert sorted(structure.individuals) == ["@I1@", "@I2@", "@I3@"]
        assert sorted(structure.families) == ["@F1@"]

    def test_the_source_record_is_not_the_headers_source(
        self,
        sample_70_file: Path,
    ) -> None:
        structure = parse_gedcom(sample_70_file)

        assert structure.header is not None
        assert structure.header.source is not None
        assert structure.header.source.system_id == "MyGenealogySoftware"
        assert structure.sources["@S1@"].title == "Birth Certificate of Jane Smith"

    def test_records_without_a_parser_are_skipped(
        self,
        sample_70_file: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="rootsy.parser"):
            parse_gedcom(sample_70_file)

        assert "SUBM" in caplog.text
        assert "REPO" in caplog.text

    def test_nothing_is_dropped_on_the_way(self, sample_70_file: Path) -> None:
        """What rootsy cannot place yet is kept on the record it came from."""
        structure = parse_gedcom(sample_70_file)

        jane = structure.individuals["@I1@"]
        assert jane.birth is not None
        assert [line.tag for line in jane.birth.unparsed] == ["MAP", "LATI", "LONG"]
        assert [line.tag for line in structure.sources["@S1@"].unparsed] == [
            "DATE",
            "PLAC",
            "REPO",
        ]

    def test_to_dict_is_plain_json(self, sample_70_file: Path) -> None:
        as_dict = parse_gedcom(sample_70_file).to_dict()

        assert json.loads(json.dumps(as_dict)) == as_dict
