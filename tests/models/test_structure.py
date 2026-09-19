"""`GedcomStructure`: what a parsed file collects, and how it serialises."""

import json

from rootsy.models import Family, GedcomStructure, Individual, SourceRecord
from rootsy.types import GedcomLine


class TestCollecting:
    def test_records_are_keyed_by_their_xref(self) -> None:
        structure = GedcomStructure()
        structure.add_individual(Individual(id="@I1@", surname="Rossi"))
        structure.add_family(Family(id="@F1@", husband="@I1@"))
        structure.add_source(SourceRecord(id="@S1@", title="Birth register"))

        assert structure.individuals["@I1@"].surname == "Rossi"
        assert structure.families["@F1@"].husband == "@I1@"
        assert structure.sources["@S1@"].title == "Birth register"

    def test_a_source_without_an_xref_cannot_be_cited_so_is_left_out(self) -> None:
        structure = GedcomStructure()
        structure.add_source(SourceRecord(title="Nameless"))

        assert structure.sources == {}

    def test_a_structure_starts_empty_and_without_a_header(self) -> None:
        structure = GedcomStructure()

        assert structure.header is None
        assert (structure.individuals, structure.families, structure.sources) == (
            {},
            {},
            {},
        )


class TestToDict:
    def test_unparsed_lines_survive_the_round_trip_to_json(self) -> None:
        line = GedcomLine(level=1, tag="_UID", value="1234", line_number=7)
        structure = GedcomStructure()
        structure.add_individual(Individual(id="@I1@", unparsed=[line]))

        as_dict = structure.to_dict()

        assert as_dict["individuals"]["@I1@"]["unparsed"] == [
            {
                "level": 1,
                "tag": "_UID",
                "value": "1234",
                "xref": None,
                "line_number": 7,
            },
        ]
        assert json.loads(json.dumps(as_dict)) == as_dict
