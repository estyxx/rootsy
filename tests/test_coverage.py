"""`rootsy.coverage`: counting the tags a parsed file kept but does not model."""

from typing import TYPE_CHECKING

from rootsy.coverage import TagCount, coverage
from rootsy.models import (
    Family,
    GedcomStructure,
    Header,
    Individual,
    SourceRecord,
)
from rootsy.parser import parse_gedcom
from rootsy.parsers import (
    FamilyParser,
    HeaderParser,
    IndividualParser,
    SourceRecordParser,
)
from rootsy.types import ParsingContext
from tests.helpers import gedcom_lines

if TYPE_CHECKING:
    from pathlib import Path


def individual(snippet: str) -> Individual:
    """Parse an INDI record from an inline snippet."""
    record, _ = IndividualParser().parse(gedcom_lines(snippet), ParsingContext())
    return record


def family(snippet: str) -> Family:
    """Parse a FAM record from an inline snippet."""
    record, _ = FamilyParser().parse(gedcom_lines(snippet), ParsingContext())
    return record


def header(snippet: str) -> Header:
    """Parse a HEAD record from an inline snippet."""
    record, _ = HeaderParser().parse(gedcom_lines(snippet), ParsingContext())
    return record


def source(snippet: str) -> SourceRecord:
    """Parse a level-0 SOUR record from an inline snippet."""
    record, _ = SourceRecordParser().parse(gedcom_lines(snippet), ParsingContext())
    return record


def structure_of(*individuals: Individual) -> GedcomStructure:
    """Collect individuals into a structure, as `parse_gedcom` would."""
    structure = GedcomStructure()
    for record in individuals:
        structure.add_individual(record)
    return structure


def paths_of(structure: GedcomStructure, tag: str) -> list[tuple[str, int]]:
    """Name every counted path of one record type, with how often it came up."""
    return [
        (str(path), path.count)
        for group in coverage(structure).records
        if group.tag == tag
        for path in group.paths
    ]


class TestTagPaths:
    def test_a_tag_no_field_holds_is_counted_under_its_record(self) -> None:
        structure = structure_of(
            individual(
                """
                0 @I1@ INDI
                1 NAME Ada /Lovelace/
                1 CHAN
                """,
            ),
        )

        assert paths_of(structure, "INDI") == [("INDI > CHAN", 1)]

    def test_a_line_nested_under_an_unparsed_line_keeps_it_as_its_parent(self) -> None:
        structure = structure_of(
            individual(
                """
                0 @I1@ INDI
                1 CHAN
                2 DATE 22 DEC 2024
                3 TIME 09:30
                """,
            ),
        )

        assert paths_of(structure, "INDI") == [
            ("INDI > CHAN", 1),
            ("INDI > CHAN > DATE", 1),
            ("INDI > CHAN > DATE > TIME", 1),
        ]

    def test_a_sibling_does_not_inherit_the_line_before_it(self) -> None:
        structure = structure_of(
            individual(
                """
                0 @I1@ INDI
                1 CHAN
                2 DATE 22 DEC 2024
                1 REFN 8F6A
                """,
            ),
        )

        assert paths_of(structure, "INDI") == [
            ("INDI > CHAN", 1),
            ("INDI > CHAN > DATE", 1),
            ("INDI > REFN", 1),
        ]

    def test_an_event_is_named_by_the_tag_it_was_read_from(self) -> None:
        structure = structure_of(
            individual(
                """
                0 @I1@ INDI
                1 BIRT
                2 PLAC Verona
                3 MAP
                4 LATI N45.4
                1 DEAT
                2 RELI Catholic
                """,
            ),
        )

        assert paths_of(structure, "INDI") == [
            ("INDI > BIRT > MAP", 1),
            ("INDI > BIRT > MAP > LATI", 1),
            ("INDI > DEAT > RELI", 1),
        ]

    def test_a_parent_the_parser_read_itself_is_not_in_the_path(self) -> None:
        """`DATE` fills a field, so its `TIME` hangs off the event instead."""
        structure = structure_of(
            individual(
                """
                0 @I1@ INDI
                1 BIRT
                2 DATE 14 MAR 1890
                3 TIME 09:30
                """,
            ),
        )

        assert paths_of(structure, "INDI") == [("INDI > BIRT > TIME", 1)]

    def test_a_substructure_of_the_header_is_walked_too(self) -> None:
        structure = GedcomStructure(
            header=header(
                """
                0 HEAD
                1 GEDC
                2 VERS 5.5.1
                1 SOUR MYHERITAGE
                2 CORP MyHeritage
                3 ADDR 3 Ariel Sharon
                4 _CUSTOM yes
                """,
            ),
        )

        assert paths_of(structure, "HEAD") == [
            ("HEAD > GEDC", 1),
            ("HEAD > SOUR > ADDR > _CUSTOM", 1),
        ]

    def test_families_and_sources_are_counted_as_well(self) -> None:
        structure = GedcomStructure()
        structure.add_family(
            family(
                """
                0 @F1@ FAM
                1 HUSB @I1@
                1 SLGS
                """,
            ),
        )
        structure.add_source(
            source(
                """
                0 @S1@ SOUR
                1 TITL Birth register
                1 REPO @R1@
                """,
            ),
        )

        assert paths_of(structure, "FAM") == [("FAM > SLGS", 1)]
        assert paths_of(structure, "SOUR") == [("SOUR > REPO", 1)]


class TestCounting:
    def test_paths_are_sorted_by_frequency(self) -> None:
        structure = structure_of(
            individual("0 @I1@ INDI\n1 ASSO @I9@\n1 CHAN\n1 REFN 7"),
            individual("0 @I2@ INDI\n1 ASSO @I9@\n1 CHAN"),
            individual("0 @I3@ INDI\n1 ASSO @I9@"),
        )

        assert paths_of(structure, "INDI") == [
            ("INDI > ASSO", 3),
            ("INDI > CHAN", 2),
            ("INDI > REFN", 1),
        ]

    def test_a_group_says_how_many_records_held_something_unparsed(self) -> None:
        structure = structure_of(
            individual("0 @I1@ INDI\n1 CHAN"),
            individual("0 @I2@ INDI\n1 CHAN\n1 REFN 7"),
            individual("0 @I3@ INDI\n1 NAME Ada /Lovelace/"),
        )

        group = coverage(structure).records[0]

        assert (group.tag, group.records, group.records_with_unparsed) == ("INDI", 3, 2)
        assert group.lines == 3

    def test_record_types_are_sorted_by_how_much_went_unparsed(self) -> None:
        structure = structure_of(individual("0 @I1@ INDI\n1 CHAN"))
        structure.add_family(family("0 @F1@ FAM\n1 SLGS\n1 CHAN\n1 REFN 7"))

        assert [group.tag for group in coverage(structure).records] == ["FAM", "INDI"]

    def test_a_record_type_with_nothing_unparsed_is_left_out(self) -> None:
        structure = structure_of(individual("0 @I1@ INDI\n1 NAME Ada /Lovelace/"))
        structure.add_family(family("0 @F1@ FAM\n1 SLGS"))

        assert [group.tag for group in coverage(structure).records] == ["FAM"]

    def test_a_file_with_everything_parsed_reports_nothing(self) -> None:
        report = coverage(structure_of(individual("0 @I1@ INDI\n1 SEX F")))

        assert report.records == []
        assert report.skipped == []
        assert report.unparsed_lines == 0
        assert report.skipped_records == 0

    def test_unparsed_lines_counts_every_record_type(self) -> None:
        structure = structure_of(individual("0 @I1@ INDI\n1 CHAN"))
        structure.add_family(family("0 @F1@ FAM\n1 SLGS"))

        assert coverage(structure).unparsed_lines == 2


class TestSkippedRecords:
    def test_level_0_tags_with_no_parser_are_counted(self) -> None:
        structure = GedcomStructure()
        for snippet in ("0 @N1@ NOTE a note", "0 @N2@ NOTE another", "0 @U1@ SUBM"):
            structure.add_skipped(gedcom_lines(snippet)[0])

        report = coverage(structure)

        assert report.skipped == [
            TagCount(path=("NOTE",), count=2),
            TagCount(path=("SUBM",), count=1),
        ]
        assert report.skipped_records == 3


class TestTagCount:
    def test_reads_as_the_path_it_counts(self) -> None:
        assert str(TagCount(path=("INDI", "OBJE", "FILE"), count=3)) == (
            "INDI > OBJE > FILE"
        )


class TestParsedFile:
    def test_counts_what_a_whole_file_left_behind(self, sample_70_file: Path) -> None:
        """The 7.0 sample leaves tags unparsed in three kinds of record."""
        report = coverage(parse_gedcom(sample_70_file))

        assert [group.tag for group in report.records] == ["HEAD", "INDI", "SOUR"]
        assert ("INDI > BIRT > MAP > LATI", 1) in paths_of(
            parse_gedcom(sample_70_file),
            "INDI",
        )
        assert [str(tag) for tag in report.skipped] == ["REPO", "SUBM"]
