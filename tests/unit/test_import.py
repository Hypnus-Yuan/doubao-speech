"""Import-time hygiene tests.

The point of `import doubao_speech` being *cheap* is that users can embed
the package in latency-sensitive agent startups without paying the
~20 ms `websockets` import tax until they actually call `synthesize()`.

These tests are the contract that enforces the promise.
"""

from __future__ import annotations

import subprocess
import sys

import pytest


def test_import_does_not_pull_websockets() -> None:
    """`import doubao_speech` must not transitively import websockets."""
    # Must run in a fresh interpreter — the test process itself may have
    # imported websockets for other tests.
    code = (
        "import sys; import doubao_speech; "
        "assert 'websockets' not in sys.modules, "
        "f'websockets leaked: {sorted(k for k in sys.modules if k.startswith(\"websockets\"))}'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_import_does_not_pull_yaml() -> None:
    """Config file support is lazy — yaml only loads when the file exists."""
    code = (
        "import sys; import doubao_speech; "
        "assert 'yaml' not in sys.modules, "
        "f'yaml leaked: {[k for k in sys.modules if \"yaml\" in k]}'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_lazy_attributes_resolve() -> None:
    """Touching a public name triggers the lazy import and caches it."""
    import doubao_speech

    assert callable(doubao_speech.synthesize)
    assert callable(doubao_speech.synthesize_async)
    assert doubao_speech.DoubaoConfig is not None
    assert issubclass(doubao_speech.DoubaoAPIError, doubao_speech.DoubaoTTSError)


def test_unknown_attribute_raises() -> None:
    import doubao_speech

    with pytest.raises(AttributeError, match="no attribute 'not_a_thing'"):
        _ = doubao_speech.not_a_thing


def test_version_is_string() -> None:
    import doubao_speech

    assert isinstance(doubao_speech.__version__, str)
    assert len(doubao_speech.__version__) > 0


def test_dir_lists_public_api() -> None:
    import doubao_speech

    listed = dir(doubao_speech)
    for name in ("synthesize", "synthesize_async", "DoubaoConfig", "DoubaoTTSError"):
        assert name in listed, f"{name} missing from dir(doubao_speech)"
