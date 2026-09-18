"""Routing a tag to its parser, by tag and by the path it sits at."""

from rootsy.models import HeaderSource, SourceRecord
from rootsy.parsers import (
    AddressParser,
    HeaderParser,
    HeaderSourceParser,
    SourceRecordParser,
)
from rootsy.registry import get_parser_for_path, get_parser_for_tag
from tests.helpers import gedcom_lines


class TestPathRouting:
    def test_sour_under_head_is_the_files_source_system(self) -> None:
        assert isinstance(get_parser_for_path(("HEAD", "SOUR")), HeaderSourceParser)

    def test_sour_at_level_zero_is_a_source_record(self) -> None:
        assert isinstance(get_parser_for_path(("SOUR",)), SourceRecordParser)

    def test_a_tag_without_a_path_of_its_own_falls_back_to_the_tag(self) -> None:
        path = ("HEAD", "SOUR", "CORP", "ADDR")

        assert isinstance(get_parser_for_path(path), AddressParser)

    def test_an_unknown_path_has_no_parser(self) -> None:
        assert get_parser_for_path(("HEAD", "_MH_CUSTOM")) is None

    def test_an_empty_path_has_no_parser(self) -> None:
        assert get_parser_for_path(()) is None


class TestTagRouting:
    def test_an_unambiguous_tag(self) -> None:
        assert isinstance(get_parser_for_tag("HEAD"), HeaderParser)

    def test_an_unknown_tag(self) -> None:
        assert get_parser_for_tag("REPO") is None

    def test_a_path_only_parser_is_not_reachable_by_its_tag_alone(self) -> None:
        """`SOUR` alone means the record, so the header's source needs its path."""
        assert isinstance(get_parser_for_tag("SOUR"), SourceRecordParser)


class TestFromLines:
    def test_a_record_finds_its_own_parser(self) -> None:
        source = SourceRecord.from_lines(
            gedcom_lines("0 @S1@ SOUR\n1 TITL Birth register"),
        )

        assert source.title == "Birth register"

    def test_a_record_with_a_tag_path_finds_the_parser_for_that_path(self) -> None:
        header_source = HeaderSource.from_lines(
            gedcom_lines("1 SOUR MyGenealogySoftware\n2 VERS 1.0"),
        )

        assert header_source.system_id == "MyGenealogySoftware"
        assert header_source.version == "1.0"
