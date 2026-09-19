"""`anonymise`: what a file keeps of its shape, and what it loses of its people."""

import json
from typing import TYPE_CHECKING

import pytest

from rootsy.anonymise import AnonymisationPolicy, DatePolicy, anonymise
from rootsy.models import (
    Address,
    Event,
    EventType,
    Family,
    GedcomDate,
    GedcomStructure,
    Header,
    HeaderSource,
    Individual,
    SourceRecord,
)
from rootsy.parser import parse_gedcom
from rootsy.types import GedcomLine

if TYPE_CHECKING:
    from pathlib import Path

# A MyHeritage-shaped file: a father, a mother and their son, a source record,
# contact details in the header and a level-0 record rootsy skips.
SAMPLE = """0 HEAD
1 SOUR MYHERITAGE
2 VERS 1.0
2 NAME MyHeritage Family Tree Builder
2 CORP MyHeritage
3 ADDR 3 Ariel Sharon Street
4 CITY Or Yehuda
4 CTRY Israel
3 PHON +972 3 000 0000
3 EMAIL support@myheritage.invalid
3 WWW https://www.myheritage.invalid
2 DATA Beltrami Family Tree
3 DATE 12 MAR 2024
3 COPR Copyright Ester Beltrami
1 DEST ANY
1 DATE 12 MAR 2024
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
1 COPR Copyright Ester Beltrami
0 @I500001@ INDI
1 NAME Giovanni /Rossi/
1 SEX M
1 EMAIL giovanni.rossi@posta.invalid
1 _UID 4F2C1A
1 BIRT
2 DATE ABT 1890
2 PLAC Verona, Veneto, Italia
2 NOTE Born at home in via Mazzini.
2 SOUR @S1@
1 FAMS @F1@
0 @I500002@ INDI
1 NAME Maria /Bianchi/
1 SEX F
1 FAMS @F1@
0 @I500003@ INDI
1 NAME Luigi /Rossi/
1 SEX M
1 BIRT
2 DATE 12 JUL 1920
2 PLAC Verona, Veneto, Italia
1 FAMC @F1@
0 @F1@ FAM
1 HUSB @I500001@
1 WIFE @I500002@
1 CHIL @I500003@
1 MARR
2 DATE 14 JUN 1919
2 PLAC Verona, Veneto, Italia
0 @S1@ SOUR
1 TITL Registro dei nati di Verona
1 AUTH Comune di Verona
1 TEXT Giovanni Rossi, son of Pietro Rossi.
0 @N1@ NOTE A note about the Rossi family
0 TRLR
"""


@pytest.fixture
def original(tmp_path: Path) -> GedcomStructure:
    """Parse the sample file the way a caller would."""
    path = tmp_path / "family.ged"
    path.write_text(SAMPLE, encoding="utf-8")
    return parse_gedcom(path)


@pytest.fixture
def anonymised(original: GedcomStructure) -> GedcomStructure:
    """Anonymise the sample file with the default policy."""
    return anonymise(original)


class TestNames:
    def test_a_person_is_renamed_in_every_form_the_record_holds(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        giovanni = anonymised.individuals["@I1@"]

        assert giovanni.given_name == "Given1"
        assert giovanni.surname == "Surname1"
        assert giovanni.name == "Given1 /Surname1/"

    def test_a_family_keeps_sharing_one_surname(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        """Father and son were both Rossi, so they are both Surname1."""
        father = anonymised.individuals["@I1@"]
        mother = anonymised.individuals["@I2@"]
        son = anonymised.individuals["@I3@"]

        assert son.surname == father.surname
        assert mother.surname != father.surname

    def test_a_record_without_a_name_is_given_none(self) -> None:
        structure = GedcomStructure()
        structure.add_individual(Individual(id="@I1@"))

        nameless = anonymise(structure).individuals["@I1@"]

        assert (nameless.name, nameless.given_name, nameless.surname) == (
            None,
            None,
            None,
        )


class TestCrossReferences:
    def test_records_are_renumbered_and_every_pointer_follows(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        assert sorted(anonymised.individuals) == ["@I1@", "@I2@", "@I3@"]
        assert sorted(anonymised.families) == ["@F1@"]
        assert sorted(anonymised.sources) == ["@S1@"]

        family = anonymised.families["@F1@"]
        assert (family.husband, family.wife) == ("@I1@", "@I2@")
        assert family.children == ["@I3@"]
        assert anonymised.individuals["@I3@"].child_of_families == ["@F1@"]
        assert anonymised.individuals["@I1@"].spouse_in_families == ["@F1@"]

    def test_the_id_a_record_is_keyed_by_is_the_one_it_carries(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        for xref, individual in anonymised.individuals.items():
            assert individual.id == xref

    def test_keep_xrefs_leaves_the_numbering_alone(
        self,
        original: GedcomStructure,
    ) -> None:
        kept = anonymise(original, AnonymisationPolicy(keep_xrefs=True))

        assert sorted(kept.individuals) == ["@I500001@", "@I500002@", "@I500003@"]
        assert kept.families["@F1@"].husband == "@I500001@"

    def test_a_pointer_to_a_record_the_file_does_not_hold_is_still_replaced(
        self,
    ) -> None:
        structure = GedcomStructure()
        structure.add_family(Family(id="@F1@", husband="@I9000@"))

        family = anonymise(structure).families["@F1@"]

        assert family.husband is not None
        assert family.husband != "@I9000@"

    def test_a_citation_still_points_at_the_source_it_cited(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        birth = anonymised.individuals["@I1@"].birth

        assert birth is not None
        assert [(line.tag, line.value) for line in birth.citations] == [
            ("SOUR", "@S1@"),
        ]


class TestDates:
    def test_a_date_keeps_only_its_year_by_default(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        birth = anonymised.individuals["@I1@"].birth

        assert birth is not None
        assert birth.date is not None
        assert birth.date.raw == "1890"  # was "ABT 1890"
        assert birth.date.year == 1890

    def test_remove_drops_every_date(self, original: GedcomStructure) -> None:
        structure = anonymise(original, AnonymisationPolicy(dates=DatePolicy.REMOVE))

        birth = structure.individuals["@I1@"].birth
        assert birth is not None
        assert birth.date is None
        assert structure.header is not None
        assert structure.header.transmission_date is None

    def test_keep_leaves_dates_as_they_were_written(
        self,
        original: GedcomStructure,
    ) -> None:
        structure = anonymise(original, AnonymisationPolicy(dates=DatePolicy.KEEP))

        birth = structure.individuals["@I1@"].birth
        assert birth is not None
        assert birth.date is not None
        assert birth.date.raw == "ABT 1890"

    def test_a_date_with_no_year_to_keep_is_dropped(self) -> None:
        """A date phrase can say as much as a date: "the summer she left"."""
        structure = GedcomStructure()
        structure.add_individual(
            Individual(
                id="@I1@",
                events=[
                    Event(
                        type=EventType.BIRTH,
                        date=GedcomDate.from_string("(the summer she left)"),
                    ),
                ],
            ),
        )

        birth = anonymise(structure).individuals["@I1@"].birth

        assert birth is not None
        assert birth.date is None


class TestPlacesAndContact:
    def test_a_place_is_replaced_by_the_same_stand_in_everywhere(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        """Both were born in Verona, so both are born in the same stand-in."""
        father_birth = anonymised.individuals["@I1@"].birth
        son_birth = anonymised.individuals["@I3@"].birth

        assert father_birth is not None
        assert son_birth is not None
        assert father_birth.place is not None
        assert father_birth.place.startswith("Place")
        assert son_birth.place == father_birth.place

    def test_keep_places_leaves_them_alone(self, original: GedcomStructure) -> None:
        structure = anonymise(original, AnonymisationPolicy(keep_places=True))

        birth = structure.individuals["@I1@"].birth
        assert birth is not None
        assert birth.place == "Verona, Veneto, Italia"

    def test_an_email_becomes_an_address_that_cannot_reach_anyone(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        assert anonymised.individuals["@I1@"].email == "person1@example.com"

    def test_one_address_shared_by_two_people_stays_one_address(self) -> None:
        structure = GedcomStructure()
        structure.add_individual(Individual(id="@I1@", email="us@posta.invalid"))
        structure.add_individual(Individual(id="@I2@", email="us@posta.invalid"))

        people = anonymise(structure).individuals

        assert people["@I1@"].email == people["@I2@"].email

    def test_a_note_is_replaced_by_a_stand_in(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        birth = anonymised.individuals["@I1@"].birth

        assert birth is not None
        assert birth.notes == ["Note 1"]


class TestSex:
    def test_sex_is_kept_by_default(self, anonymised: GedcomStructure) -> None:
        assert anonymised.individuals["@I1@"].sex == "M"
        assert anonymised.individuals["@I2@"].sex == "F"

    def test_sex_is_dropped_when_the_policy_says_so(
        self,
        original: GedcomStructure,
    ) -> None:
        structure = anonymise(original, AnonymisationPolicy(keep_sex=False))

        assert structure.individuals["@I1@"].sex is None


class TestUnparsedLines:
    def test_a_value_no_model_field_holds_is_dropped(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        """`_UID 4F2C1A` identifies the person as surely as their name does."""
        unparsed = anonymised.individuals["@I1@"].unparsed

        assert [(line.level, line.tag, line.value) for line in unparsed] == [
            (1, "_UID", ""),
        ]

    def test_a_line_keeps_where_it_came_from(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        line = anonymised.individuals["@I1@"].unparsed[0]

        assert line.line_number == 25

    def test_a_pointer_value_is_mapped_rather_than_dropped(self) -> None:
        structure = GedcomStructure()
        structure.add_individual(Individual(id="@I1@"))
        structure.add_individual(
            Individual(
                id="@I2@",
                unparsed=[GedcomLine(level=1, tag="ASSO", value="@I1@")],
            ),
        )

        associate = anonymise(structure).individuals["@I2@"].unparsed[0]

        assert (associate.tag, associate.value) == ("ASSO", "@I1@")


class TestHeader:
    def test_the_software_that_wrote_the_file_is_kept(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        """An exporter's quirks are the reason to keep an anonymised file."""
        assert anonymised.header is not None
        assert anonymised.header.version == "5.5.1"
        assert anonymised.header.encoding == "UTF-8"

        source = anonymised.header.source
        assert source is not None
        assert source.system_id == "MYHERITAGE"
        assert source.corporation == "MyHeritage"

    def test_what_names_the_person_who_exported_it_is_not(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        assert anonymised.header is not None
        assert anonymised.header.copyright is None

        source = anonymised.header.source
        assert source is not None
        assert source.data_copyright is None
        assert source.data_name == "Database1"  # was "Beltrami Family Tree"

    def test_the_address_in_the_header_is_replaced(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        assert anonymised.header is not None
        assert anonymised.header.source is not None
        address = anonymised.header.source.address
        assert address is not None

        assert address.full == "Address1"  # was "3 Ariel Sharon Street"
        assert address.city == "Place1"  # was "Or Yehuda"
        assert address.country is None

    def test_the_contact_details_beside_it_are_replaced_too(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        """PHON, EMAIL and WWW sit next to ADDR, not under it, so they land here."""
        assert anonymised.header is not None
        assert anonymised.header.source is not None
        unparsed = anonymised.header.source.unparsed

        assert [line.tag for line in unparsed] == [
            "PHON",
            "EMAIL",
            "WWW",
            "DATE",
            "COPR",  # "Copyright Ester Beltrami", under DATA
        ]
        assert {line.value for line in unparsed} == {""}

    def test_every_part_of_an_address_is_replaced(self) -> None:
        structure = GedcomStructure(
            header=Header(
                version="5.5.1",
                source=HeaderSource(
                    system_id="MYHERITAGE",
                    address=Address(
                        full="3 Ariel Sharon Street",
                        line1="3 Ariel Sharon Street",
                        city="Or Yehuda",
                        state="Tel Aviv",
                        postal_code="6037604",
                        country="Israel",
                        phone=["+972 3 000 0000"],
                        email=["support@myheritage.invalid"],
                        fax=["+972 3 000 0001"],
                        web="https://www.myheritage.invalid",
                    ),
                ),
            ),
        )

        anonymous = anonymise(structure)

        assert anonymous.header is not None
        assert anonymous.header.source is not None
        address = anonymous.header.source.address
        assert address is not None
        assert (address.line1, address.state, address.postal_code) == (None, None, None)
        assert address.phone == ["Phone1"]
        assert address.email == ["person1@example.com"]
        assert address.fax == ["Fax1"]
        assert address.web == "https://example.com"

    def test_an_address_that_was_not_there_is_not_invented(self) -> None:
        anonymous = anonymise(GedcomStructure())

        assert anonymous.header is None


class TestSources:
    def test_a_source_record_says_only_that_it_was_a_source(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        source = anonymised.sources["@S1@"]

        assert source.title == "Source 1"
        assert source.author == "Author 1"
        assert source.text == "Text 1"

    def test_a_field_the_record_did_not_have_stays_empty(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        assert anonymised.sources["@S1@"].publication is None


class TestSkippedRecords:
    def test_a_skipped_record_keeps_its_tag_and_loses_its_xref(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        skipped = anonymised.skipped

        assert [(record.tag, record.line_number) for record in skipped] == [
            ("NOTE", 54),
        ]
        assert skipped[0].xref is not None
        assert skipped[0].xref != "@N1@"


class TestGuarantees:
    def test_the_structure_it_was_given_is_left_untouched(
        self,
        original: GedcomStructure,
    ) -> None:
        before = json.dumps(original.to_dict())

        anonymise(original)

        assert json.dumps(original.to_dict()) == before

    def test_the_same_file_always_anonymises_the_same_way(
        self,
        original: GedcomStructure,
    ) -> None:
        assert anonymise(original) == anonymise(original)

    def test_the_result_is_still_plain_json(
        self,
        anonymised: GedcomStructure,
    ) -> None:
        as_dict = anonymised.to_dict()

        assert json.loads(json.dumps(as_dict)) == as_dict

    def test_an_empty_structure_survives(self) -> None:
        assert anonymise(GedcomStructure()) == GedcomStructure()


# Every personal detail of `tests/data/headers/header_7.0.ged`: the names, the
# places, the contact details and the words of its source record.
PERSONAL_DETAILS = (
    "Jane",
    "John",
    "Emily",
    "Smith",
    "Doe",
    "London",
    "Springfield",
    "New York",
    "51.5074",
    "-0.1278",
    "456 Family Ln.",
    "555-6789",
    "john.doe@example.com",
    "Birth Certificate of Jane Smith",
    "Registrar of Births",
    "National Archives",
    "1985",
    "2012",
)


class TestNothingPersonalSurvives:
    """The point of the whole exercise, checked against a real sample file."""

    def test_no_personal_detail_is_left_in_the_json(
        self,
        sample_70_file: Path,
    ) -> None:
        """Under the strictest policy, not even a year of a date is left."""
        everything = AnonymisationPolicy(
            dates=DatePolicy.REMOVE,
            keep_sex=False,
            keep_places=False,
        )
        structure = anonymise(parse_gedcom(sample_70_file), everything)
        exported = json.dumps(structure.to_dict())

        left_behind = [detail for detail in PERSONAL_DETAILS if detail in exported]
        assert left_behind == []

    def test_the_file_keeps_its_shape(self, sample_70_file: Path) -> None:
        structure = parse_gedcom(sample_70_file)

        anonymous = anonymise(structure)

        assert len(anonymous.individuals) == len(structure.individuals)
        assert len(anonymous.families) == len(structure.families)
        assert len(anonymous.skipped) == len(structure.skipped)
        assert [event.type for event in anonymous.individuals["@I1@"].events] == [
            EventType.BIRTH,
            EventType.DEATH,
        ]

    def test_an_address_record_keeps_only_its_structure(self) -> None:
        structure = GedcomStructure()
        structure.add_source(
            SourceRecord(id="@S1@", title="Archivio di Stato di Verona"),
        )
        address = Address(full="via Roma 1, Verona", city="Verona", country="Italia")

        anonymous = anonymise(structure)

        assert anonymous.sources["@S1@"].title == "Source 1"
        assert "Verona" not in json.dumps(anonymous.to_dict())
        assert address.city == "Verona"  # the original is untouched
