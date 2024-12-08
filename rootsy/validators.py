from typing import TextIO


class GedcomValidationError(Exception):
    """Custom exception for GEDCOM validation errors"""

    pass


def validate_gedcom_version(file: TextIO) -> None:
    """
    Validate GEDCOM file version

    Args:
        file (TextIO): File object to validate

    Raises:
        GedcomValidationError: If version is unsupported
    """
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
        raise GedcomValidationError(
            "Unsupported GEDCOM version. This parser supports version 5.5.1"
        )
