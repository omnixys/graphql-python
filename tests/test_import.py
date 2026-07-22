"""Smoke test - verifies omnixys-graphql can be imported."""

from __future__ import annotations

import importlib
from importlib.metadata import version as pkg_version


def test_package_importable() -> None:
    mod = importlib.import_module("graphql")
    assert hasattr(mod, "__version__")
    assert mod.__version__ == pkg_version("omnixys-graphql")


def test_public_api() -> None:
    from graphql import errors, pagination, utils

    assert errors is not None
    assert pagination is not None
    assert utils is not None
