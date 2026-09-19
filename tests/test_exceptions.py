"""Every error rootsy raises hangs off `RootsyError`."""

import pytest

from rootsy.adapters import ParserNotFoundError
from rootsy.exceptions import (
    GedcomFileNotFoundError,
    NotAGedcomFileError,
    RootsyError,
    UnsupportedGedcomVersionError,
)

ERRORS = [
    ParserNotFoundError("INDI"),
    UnsupportedGedcomVersionError("6.0", ("5.5.1", "7.0")),
    GedcomFileNotFoundError("family.ged"),
    NotAGedcomFileError("/tmp"),  # noqa: S108
]


@pytest.mark.parametrize("error", ERRORS, ids=lambda error: type(error).__name__)
def test_every_error_is_a_rootsy_error(error: RootsyError) -> None:
    assert isinstance(error, RootsyError)


@pytest.mark.parametrize("error", ERRORS, ids=lambda error: type(error).__name__)
def test_every_error_says_what_went_wrong(error: RootsyError) -> None:
    assert str(error)


class TestUnsupportedGedcomVersionError:
    def test_names_the_version_and_the_supported_ones(self) -> None:
        error = UnsupportedGedcomVersionError("6.0", ("5.5.1", "7.0"))

        assert str(error) == (
            "Unsupported GEDCOM version '6.0'. Supported versions are 5.5.1 and 7.0"
        )
        assert error.version == "6.0"
        assert error.supported == ("5.5.1", "7.0")

    def test_stays_a_value_error(self) -> None:
        """It is raised from an attrs validator, where a ValueError is expected."""
        assert isinstance(UnsupportedGedcomVersionError("6.0", ()), ValueError)

    def test_lists_three_supported_versions_readably(self) -> None:
        error = UnsupportedGedcomVersionError("6.0", ("5.5", "5.5.1", "7.0"))

        assert str(error).endswith("Supported versions are 5.5, 5.5.1 and 7.0")
