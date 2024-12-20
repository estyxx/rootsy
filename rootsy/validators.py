from typing import TextIO


class GedcomValidationError(Exception):
    """Custom exception for GEDCOM validation errors."""

    def __init__(self) -> None:
        message = "Unsupported GEDCOM version. This parser supports version 5.5.1"
        super().__init__(message)


def validate_gedcom_version(file: TextIO) -> None:
    """Validate GEDCOM file version."""
    # Reset file pointer to beginning
    file.seek(0)

    # Look for header with version information
    version_found = False
    for line in file:
        if "HEAD" in line:
            continue

        # Check for version line
        if "5.5.1" in line:
            version_found = True
            break

        # If we've passed header sections, stop searching
        if len(line.split()) > 2:
            break

    if not version_found:
        raise GedcomValidationError
