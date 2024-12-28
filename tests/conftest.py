from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return the path to the test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def sample_header_551(test_data_dir: Path) -> str:
    """Return the content of a sample 5.5.1 header."""
    return (test_data_dir / "headers" / "header_5.5.1.ged").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def sample_header_70(test_data_dir: Path) -> str:
    """Return the content of a sample 7.0 header."""
    return (test_data_dir / "headers" / "header_7.0.ged").read_text(encoding="utf-8")
