"""Public exception hierarchy tests."""

from __future__ import annotations

from doubao_speech.exceptions import (
    DoubaoAPIError,
    DoubaoAuthError,
    DoubaoConfigError,
    DoubaoTimeoutError,
    DoubaoTTSError,
)


def test_base_class() -> None:
    assert issubclass(DoubaoTTSError, Exception)


def test_all_subclass_base() -> None:
    for subcls in (
        DoubaoConfigError,
        DoubaoAuthError,
        DoubaoAPIError,
        DoubaoTimeoutError,
    ):
        assert issubclass(subcls, DoubaoTTSError), f"{subcls} must inherit DoubaoTTSError"


def test_api_error_carries_code() -> None:
    err = DoubaoAPIError("upstream said no", code=429)
    assert err.code == 429
    assert "upstream said no" in str(err)


def test_api_error_default_code_none() -> None:
    err = DoubaoAPIError("oops")
    assert err.code is None
