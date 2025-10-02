"""Tests for version management script."""

# Import the version script functions
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from version import (
    format_version,
    get_current_version,
    increment_version,
    parse_version,
)


def test_parse_version():
    """Test version parsing."""
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version("0.1.0") == (0, 1, 0)
    assert parse_version("10.20.30") == (10, 20, 30)

    # Test with prerelease/build metadata (should ignore)
    assert parse_version("1.2.3-alpha") == (1, 2, 3)
    assert parse_version("1.2.3+build") == (1, 2, 3)

    # Test invalid versions
    with pytest.raises(ValueError, match="Invalid semantic version"):
        parse_version("1.2")
    with pytest.raises(ValueError, match="Invalid semantic version"):
        parse_version("1.2.3.4")
    with pytest.raises(ValueError, match="Invalid semantic version"):
        parse_version("v1.2.3")


def test_format_version():
    """Test version formatting."""
    assert format_version(1, 2, 3) == "1.2.3"
    assert format_version(0, 1, 0) == "0.1.0"
    assert format_version(10, 20, 30) == "10.20.30"


def test_increment_version():
    """Test version incrementing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pyproject_path = temp_path / "pyproject.toml"

        # Create a temporary pyproject.toml
        pyproject_content = """[project]
name = "test-project"
version = "1.2.3"
description = "Test project"
"""
        pyproject_path.write_text(pyproject_content)

        # Mock the Path to use our temporary directory
        with patch("version.Path") as mock_path:
            mock_path.return_value = pyproject_path

            # Test patch increment
            result = increment_version("patch")
            assert result == "1.2.4"

            # Reset for next test
            pyproject_path.write_text(pyproject_content)

            # Test minor increment
            result = increment_version("minor")
            assert result == "1.3.0"

            # Reset for next test
            pyproject_path.write_text(pyproject_content)

            # Test major increment
            result = increment_version("major")
            assert result == "2.0.0"

            # Test invalid increment type
            with pytest.raises(ValueError, match="Invalid increment type"):
                increment_version("invalid")


def test_get_current_version():
    """Test getting current version from pyproject.toml."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pyproject_path = temp_path / "pyproject.toml"

        # Test with valid pyproject.toml
        pyproject_content = """[project]
name = "test-project"
version = "1.2.3"
description = "Test project"
"""
        pyproject_path.write_text(pyproject_content)

        with patch("version.Path") as mock_path:
            mock_path.return_value = pyproject_path
            assert get_current_version() == "1.2.3"

        # Test with missing file
        pyproject_path.unlink()
        with patch("version.Path") as mock_path:
            mock_path.return_value = pyproject_path
            with pytest.raises(FileNotFoundError, match=r"pyproject\.toml not found"):
                get_current_version()

        # Test with missing version
        pyproject_content_no_version = """[project]
name = "test-project"
description = "Test project"
"""
        pyproject_path.write_text(pyproject_content_no_version)

        with patch("version.Path") as mock_path:
            mock_path.return_value = pyproject_path
            with pytest.raises(ValueError, match="Version not found"):
                get_current_version()
