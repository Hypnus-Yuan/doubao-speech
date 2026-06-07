"""ASR endpoint selection tests (#1) — no network.

Covers:
- ``_ws_client.resolve_asr_url`` alias / URL / error resolution.
- ``api.transcribe`` forwarding ``endpoint`` to the low-level client as
  ``api_url`` (and *not* forwarding when left as the default).
- The ``--endpoint`` CLI option.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from doubao_speech import _ws_client
from doubao_speech._ws_client import ASR_ENDPOINTS, VolcengineParamError, resolve_asr_url
from doubao_speech.cli import main


# ---------------------------------------------------------------------------
# resolve_asr_url
# ---------------------------------------------------------------------------
def test_resolve_default_is_bigmodel() -> None:
    assert resolve_asr_url(None) == ASR_ENDPOINTS["bigmodel"]
    assert resolve_asr_url(None).endswith("/sauc/bigmodel")


@pytest.mark.parametrize("alias", sorted(ASR_ENDPOINTS))
def test_resolve_known_aliases(alias: str) -> None:
    assert resolve_asr_url(alias) == ASR_ENDPOINTS[alias]


def test_resolve_async_endpoint_url() -> None:
    assert resolve_asr_url("bigmodel_async").endswith("/sauc/bigmodel_async")


def test_resolve_explicit_url_passthrough() -> None:
    url = "wss://example.com/api/v3/sauc/custom"
    assert resolve_asr_url(url) == url
    assert resolve_asr_url("ws://localhost:8080/x") == "ws://localhost:8080/x"


def test_resolve_unknown_raises() -> None:
    with pytest.raises(VolcengineParamError, match="unknown ASR endpoint"):
        resolve_asr_url("not-a-real-endpoint")


# ---------------------------------------------------------------------------
# api.transcribe forwarding
# ---------------------------------------------------------------------------
class _RecordingFakeASR:
    def __init__(self) -> None:
        self.last_kwargs: dict = {}

    def asr_stream(self, source, **kwargs):
        self.last_kwargs = kwargs

        async def _gen() -> AsyncIterator[dict]:
            yield {"text": "结果", "is_final": True, "utterances": []}

        return _gen()


@pytest.fixture
def fake_asr(monkeypatch: pytest.MonkeyPatch) -> _RecordingFakeASR:
    fake = _RecordingFakeASR()
    monkeypatch.setattr(_ws_client, "asr_stream", fake.asr_stream)
    return fake


@pytest.fixture(autouse=True)
def _creds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLCENGINE_APP_ID", "app_test_id")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "tok_test_value_long")


def test_transcribe_default_endpoint_is_none(fake_asr: _RecordingFakeASR, tmp_path: Path) -> None:
    """Leaving endpoint unset forwards endpoint=None (client picks bigmodel)."""
    from doubao_speech import transcribe

    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    transcribe(audio)
    assert fake_asr.last_kwargs["endpoint"] is None


def test_transcribe_forwards_endpoint_alias(fake_asr: _RecordingFakeASR, tmp_path: Path) -> None:
    from doubao_speech import transcribe

    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    transcribe(audio, endpoint="bigmodel_async")
    assert fake_asr.last_kwargs["endpoint"] == "bigmodel_async"


def test_transcribe_forwards_explicit_url(fake_asr: _RecordingFakeASR, tmp_path: Path) -> None:
    from doubao_speech import transcribe

    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    transcribe(audio, endpoint="wss://example.com/custom")
    assert fake_asr.last_kwargs["endpoint"] == "wss://example.com/custom"


# ---------------------------------------------------------------------------
# CLI --endpoint
# ---------------------------------------------------------------------------
def test_cli_endpoint_option_forwarded(tmp_path: Path) -> None:
    runner = CliRunner()
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")

    captured: dict = {}

    def fake(audio_path, **kw):
        captured.update(kw)
        return "ok"

    from unittest.mock import patch

    with patch("doubao_speech.api.transcribe", fake):
        result = runner.invoke(main, ["transcribe", str(audio), "--endpoint", "bigmodel_async"])
    assert result.exit_code == 0, result.output
    assert captured["endpoint"] == "bigmodel_async"


def test_cli_endpoint_rejects_unknown(tmp_path: Path) -> None:
    runner = CliRunner()
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    result = runner.invoke(main, ["transcribe", str(audio), "--endpoint", "garbage"])
    assert result.exit_code != 0
    assert "garbage" in result.output or "invalid" in result.output.lower()


def test_cli_endpoint_in_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["transcribe", "--help"])
    assert result.exit_code == 0
    assert "bigmodel_async" in result.output
