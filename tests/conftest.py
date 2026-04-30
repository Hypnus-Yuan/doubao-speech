"""Shared pytest fixtures for doubao-speech tests.

Keep this file minimal — individual tests should be self-contained so a
reader can grok one ``test_*.py`` without having to chase fixtures.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> Iterator[None]:
    """Strip Volcengine/Doubao env vars so unit tests start clean.

    Integration tests are exempt: they need real credentials from the
    ambient environment or CI secrets.
    """
    if "integration" in request.keywords:
        yield
        return

    for key in list(os.environ):
        if key.startswith(("VOLCENGINE_", "DOUBAO_")):
            monkeypatch.delenv(key, raising=False)
    yield
