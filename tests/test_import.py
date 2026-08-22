"""Smoke test - verifies omnixys-graphql can be imported."""

from __future__ import annotations

import importlib
from importlib.metadata import version as pkg_version


def test_package_importable() -> None:
    mod = importlib.import_module("omnixys_graphql")
    assert hasattr(mod, "__version__")
    assert mod.__version__ == pkg_version("omnixys-graphql")


def test_public_api() -> None:
    from omnixys_graphql import contracts, errors, pagination, utils

    assert contracts is not None
    assert errors is not None
    assert pagination is not None
    assert utils is not None


def test_does_not_shadow_graphql_core() -> None:
    import graphql

    import omnixys_graphql

    assert graphql is not omnixys_graphql
    from graphql.version import VersionInfo  # type: ignore[attr-defined]

    assert VersionInfo is not None
