"""Test version information."""

from sage import __version__


def test_version_exists() -> None:
    """Test that version is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_version_format() -> None:
    """Test that version follows semantic versioning."""
    parts = __version__.split(".")
    assert len(parts) >= 2  # At least major.minor
    assert parts[0].isdigit()
    assert parts[1].isdigit()
