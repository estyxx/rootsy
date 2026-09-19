"""`GedcomLine.from_string`: `level [xref] tag [value]`, in every shape."""

from rootsy.types import GedcomLine, ParsingContext
from tests.helpers import gedcom_lines


class TestFromString:
    def test_xref_and_value(self) -> None:
        """The value follows the xref and runs to the end of the line."""
        line = GedcomLine.from_string("0 @N1@ NOTE some text")

        assert line is not None
        assert line.level == 0
        assert line.xref == "@N1@"
        assert line.tag == "NOTE"
        assert line.value == "some text"

    def test_xref_without_value(self) -> None:
        line = GedcomLine.from_string("0 @I1@ INDI")

        assert line is not None
        assert (line.level, line.xref, line.tag, line.value) == (0, "@I1@", "INDI", "")

    def test_tag_without_value(self) -> None:
        line = GedcomLine.from_string("1 BIRT")

        assert line is not None
        assert (line.level, line.xref, line.tag, line.value) == (1, None, "BIRT", "")

    def test_tag_with_value(self) -> None:
        line = GedcomLine.from_string("1 NAME Giovanni /Rossi/ Jr")

        assert line is not None
        assert (line.xref, line.tag, line.value) == (
            None,
            "NAME",
            "Giovanni /Rossi/ Jr",
        )

    def test_pointer_value_is_not_an_xref(self) -> None:
        """`@F1@` after a tag points at a record; it does not identify this one."""
        line = GedcomLine.from_string("1 FAMS @F1@")

        assert line is not None
        assert (line.xref, line.tag, line.value) == (None, "FAMS", "@F1@")

    def test_continuation_lines(self) -> None:
        conc = GedcomLine.from_string("3 CONC me, on a Sunday")
        cont = GedcomLine.from_string("3 CONT on a Sunday morning.")

        assert conc is not None
        assert (conc.level, conc.tag, conc.value) == (3, "CONC", "me, on a Sunday")
        assert cont is not None
        assert (cont.level, cont.tag, cont.value) == (
            3,
            "CONT",
            "on a Sunday morning.",
        )

    def test_empty_continuation_is_a_blank_line(self) -> None:
        line = GedcomLine.from_string("2 CONT")

        assert line is not None
        assert (line.tag, line.value) == ("CONT", "")

    def test_value_may_contain_at_signs(self) -> None:
        line = GedcomLine.from_string("1 EMAIL giovanni@example.com")

        assert line is not None
        assert (line.tag, line.value) == ("EMAIL", "giovanni@example.com")

    def test_surrounding_whitespace_is_ignored(self) -> None:
        line = GedcomLine.from_string("  1 SEX M\n")

        assert line is not None
        assert (line.level, line.tag, line.value) == (1, "SEX", "M")

    def test_a_line_without_a_level_is_not_a_gedcom_line(self) -> None:
        assert GedcomLine.from_string("HEAD") is None
        assert GedcomLine.from_string("") is None
        assert GedcomLine.from_string("   ") is None
        assert GedcomLine.from_string("1") is None

    def test_line_number_is_kept_but_left_out_of_equality(self) -> None:
        """A line means the same thing wherever in the file it was read."""
        first = GedcomLine.from_string("1 SEX M", line_number=7)
        second = GedcomLine.from_string("1 SEX M", line_number=99)

        assert first is not None
        assert first.line_number == 7
        assert first == second


def walked(*raw_lines: str) -> ParsingContext:
    """Return a context that has entered each of the given lines in turn."""
    context = ParsingContext()
    for line in gedcom_lines("\n".join(raw_lines)):
        context.enter_level(line)
    return context


class TestParsingContext:
    def test_path_follows_the_levels(self) -> None:
        context = walked("0 HEAD", "1 SOUR Rootsy", "2 CORP Rootsy")

        assert context.path == ("HEAD", "SOUR", "CORP")

    def test_path_pops_back_up_for_a_sibling(self) -> None:
        context = walked("0 HEAD", "1 SOUR Rootsy", "2 CORP Rootsy", "1 DEST ANY")

        assert context.path == ("HEAD", "DEST")
