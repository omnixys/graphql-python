"""Smoke test - verifies omnixys-graphql can be imported."""

from __future__ import annotations

import importlib



def test_package_importable() -> None:
    mod = importlib.import_module("omnixys_graphql")
    assert hasattr(mod, "__version__")
    assert mod.__version__ == "1.0.0"


def test_public_api() -> None:
    from omnixys_graphql import errors, pagination, utils

    assert errors is not None
    assert pagination is not None
    assert utils is not None
