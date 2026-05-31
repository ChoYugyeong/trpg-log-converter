"""Tests for the version comparison logic used by the updater."""

from __future__ import annotations

import pytest

from core.version import __version__, is_newer_than, version_tuple


def test_current_version_string_is_semver():
    parts = __version__.split(".")
    assert len(parts) == 3
    for p in parts:
        assert p.isdigit(), f"non-numeric semver part: {p}"


def test_version_tuple_matches_string():
    tup = version_tuple()
    assert ".".join(str(p) for p in tup) == __version__


@pytest.mark.parametrize(
    "remote, expected",
    [
        ("v99.0.0", True),
        ("v1.0.0", False),
        (__version__, False),
        (f"v{__version__}", False),
        ("garbage", False),
        ("", False),
        ("v2", False),  # Malformed - missing minor
    ],
)
def test_is_newer_than(remote: str, expected: bool):
    assert is_newer_than(remote) is expected


def test_is_newer_than_strips_v_prefix():
    # Both with and without leading 'v' should give same result.
    bare = is_newer_than("99.0.0")
    prefixed = is_newer_than("v99.0.0")
    assert bare == prefixed is True
