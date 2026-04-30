"""Credential redaction + payload-log opt-in tests."""

from __future__ import annotations

import pytest

from doubao_speech._logging import redact_secret, trace_payloads_enabled


def test_redact_none_returns_empty() -> None:
    assert redact_secret(None) == ""
    assert redact_secret("") == ""


def test_redact_short_token_hidden() -> None:
    assert redact_secret("x") == "***"
    assert redact_secret("12345678") == "***"


def test_redact_long_token_fingerprinted() -> None:
    result = redact_secret("sk_ABCDEFGHIJKLMN")
    assert "sk_A" in result
    assert "KLMN" in result
    assert "CDEFGHIJ" not in result  # middle hidden


def test_full_secret_never_in_redacted() -> None:
    """Fuzzy: pick long random-looking tokens, ensure full value never leaks."""
    secret = "volc_abcdef1234567890_xyz_very_long_token"
    r = redact_secret(secret)
    assert secret not in r
    assert len(r) < len(secret)


def test_trace_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOUBAO_SPEECH_TRACE_PAYLOADS", raising=False)
    assert trace_payloads_enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "yes", "on", "TRUE", "Yes"])
def test_trace_env_truthy(monkeypatch: pytest.MonkeyPatch, val: str) -> None:
    monkeypatch.setenv("DOUBAO_SPEECH_TRACE_PAYLOADS", val)
    assert trace_payloads_enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "no", "off", "", "   "])
def test_trace_env_falsy(monkeypatch: pytest.MonkeyPatch, val: str) -> None:
    monkeypatch.setenv("DOUBAO_SPEECH_TRACE_PAYLOADS", val)
    assert trace_payloads_enabled() is False
