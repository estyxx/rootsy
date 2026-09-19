"""End-to-end parsing of the sample files in `tests/fixtures`."""

import datetime
import json
import logging
from typing import TYPE_CHECKING

from rootsy.coverage import coverage
from rootsy.models import EventType
from rootsy.parser import parse_gedcom

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class TestSample551:
    def test_parses_end_to_end(self, sample_551_file: Path) -> None:
        structure = parse_gedcom(sample_551_file)

        assert structure.header is not None
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


class TestMyHeritage551:
    """A MyHeritage export: the tags that drive what rootsy models next."""

    def test_parses_end_to_end(self, myheritage_551_file: Path) -> None:
        structure = parse_gedcom(myheritage_551_file)

        assert structure.header is not None
        assert structure.header.version == "5.5.1"
        assert sorted(structure.individuals) == ["@I1@", "@I2@", "@I3@"]
        assert sorted(structure.families) == ["@F1@"]
        assert sorted(structure.sources) == ["@S1@"]
        assert structure.skipped == []

    def test_a_person_keeps_their_photos_and_attributes(
        self,
        myheritage_551_file: Path,
    ) -> None:
        giovanni = parse_gedcom(myheritage_551_file).individuals["@I1@"]

        assert giovanni.uid == "4F2C1AE7B90000000000000000000001"
        assert giovanni.vendor["RIN"] == "501"
        assert giovanni.name_prefix == "Cav."
        assert giovanni.occupations == ["Contadino"]
        assert giovanni.notes == [
            "Emigrated to Argentina in 1913 and came back\nfour years later.",
        ]
        assert giovanni.primary_photo is not None
        assert giovanni.primary_photo.file == "photos/giovanni.jpg"
        assert giovanni.primary_photo.place == "Verona, Veneto, Italia"
        assert giovanni.primary_photo.vendor["_CUTOUT"] == "Y"
        assert [line.tag for line in giovanni.citations] == []

    def test_a_married_name_and_a_photo_that_is_not_the_first(
        self,
        myheritage_551_file: Path,
    ) -> None:
        maria = parse_gedcom(myheritage_551_file).individuals["@I2@"]

        assert maria.married_name == "Maria /Rossi/"
        assert len(maria.media) == 2
        assert maria.primary_photo is not None
        assert maria.primary_photo.file == "photos/maria.jpg"

    def test_an_events_detail_is_read_down_to_its_address(
        self,
        myheritage_551_file: Path,
    ) -> None:
        giovanni = parse_gedcom(myheritage_551_file).individuals["@I1@"]
        residence = next(
            event for event in giovanni.events if event.type is EventType.RESIDENCE
        )

        assert residence.address is not None
        assert residence.address.city == "Verona"
        assert residence.email == "giovanni.rossi@example.com"
        assert giovanni.death is not None
        assert giovanni.death.cause == "Polmonite"
        assert giovanni.death.age == "64y"
        assert [event.type for event in giovanni.events] == [
            EventType.BIRTH,
            EventType.RESIDENCE,
            EventType.DEATH,
            EventType.BURIAL,
        ]

    def test_a_birth_keeps_the_source_it_was_taken_from(
        self,
        myheritage_551_file: Path,
    ) -> None:
        birth = parse_gedcom(myheritage_551_file).individuals["@I1@"].birth

        assert birth is not None
        assert [line.tag for line in birth.citations] == ["SOUR", "PAGE"]

    def test_a_family_event_with_no_tag_of_its_own(
        self,
        myheritage_551_file: Path,
    ) -> None:
        family = parse_gedcom(myheritage_551_file).families["@F1@"]

        assert family.uid == "9B3E7C0000000000000000000000000F"
        assert [event.custom_type for event in family.events] == ["Engagement"]
        assert family.events[0].type is EventType.OTHER
        assert family.marriage_event is not None

    def test_the_source_record_carries_its_stable_id(
        self,
        myheritage_551_file: Path,
    ) -> None:
        source = parse_gedcom(myheritage_551_file).sources["@S1@"]

        assert source.uid == "7C4A200000000000000000000000000A"
        assert source.vendor["RIN"] == "3"
        assert source.publication == "Archivio di Stato di Verona, 1988"

    def test_only_the_header_leaves_anything_unparsed(
        self,
        myheritage_551_file: Path,
    ) -> None:
        """INDI, FAM and SOUR are read whole; the header is the next job."""
        report = coverage(parse_gedcom(myheritage_551_file))

        assert [group.tag for group in report.records] == ["HEAD"]
        assert report.skipped == []

    def test_what_the_header_still_holds_is_its_vendor_tags(
        self,
        myheritage_551_file: Path,
    ) -> None:
        report = coverage(parse_gedcom(myheritage_551_file))

        assert [str(path) for path in report.records[0].paths] == [
            "HEAD > GEDC",
            "HEAD > _EXPORTED_FROM_SITE_ID",
            "HEAD > _PROJECT_GUID",
            "HEAD > _SM_MERGES",
        ]

    def test_to_dict_is_plain_json(self, myheritage_551_file: Path) -> None:
        as_dict = parse_gedcom(myheritage_551_file).to_dict()

        assert json.loads(json.dumps(as_dict)) == as_dict
