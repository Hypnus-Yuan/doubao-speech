"""Tests for public-API correctness on edge paths that used to be broken.

These are the unit tests that the final-audit review flagged as missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doubao_speech import (
    DoubaoAPIError,
    DoubaoAuthError,
    DoubaoConfigError,
    DoubaoSpeechError,
    DoubaoTimeoutError,
    synthesize,
)
from doubao_speech.api import _translate_ws_error


class _FakeWS:
    """Minimal recorder that emits a tiny MP3 placeholder."""

    def __init__(self) -> None:
        self.last_kwargs: dict = {}

    async def tts_to_file(self, text, output_path, **kwargs):
        self.last_kwargs = kwargs
        p = Path(output_path)
        p.write_bytes(b"FAKEMP3")
        return p


@pytest.fixture
def fake_ws(monkeypatch: pytest.MonkeyPatch) -> _FakeWS:
    fake = _FakeWS()
    from doubao_speech import _ws_client

    monkeypatch.setattr(_ws_client, "tts_to_file", fake.tts_to_file)
    return fake


@pytest.fixture(autouse=True)
def _creds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLCENGINE_APP_ID", "a")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "tok_abcdefgh12345678")


# -------------------------------------------------------------------
# P0.1 — speed/emotion_scale/loudness contract
# -------------------------------------------------------------------
def test_speed_maps_to_speed_ratio(fake_ws: _FakeWS, tmp_path: Path) -> None:
    synthesize("hi", tmp_path / "o.mp3", speed=1.2)
    assert fake_ws.last_kwargs.get("speed_ratio") == 1.2
    assert "speed" not in fake_ws.last_kwargs, "public 'speed' must not leak to the wire"


def test_emotion_scale_coerced_to_int(fake_ws: _FakeWS, tmp_path: Path) -> None:
    synthesize("hi", tmp_path / "o.mp3", emotion="excited", emotion_scale=3.7)
    assert fake_ws.last_kwargs["emotion_scale"] == 3  # coerced
    assert isinstance(fake_ws.last_kwargs["emotion_scale"], int)


def test_loudness_is_rejected_not_silently_dropped(
    fake_ws: _FakeWS,
    tmp_path: Path,
) -> None:
    """loudness is unsupported; must raise DoubaoConfigError, not silently vanish."""
    with pytest.raises(DoubaoConfigError, match="loudness"):
        synthesize("hi", tmp_path / "o.mp3", loudness=1.5)


# -------------------------------------------------------------------
# P0.2 — internal Volcengine* exceptions → public DoubaoSpeechError subclasses
# -------------------------------------------------------------------
def test_translate_auth_error() -> None:
    from doubao_speech._ws_client import VolcengineAuthError

    result = _translate_ws_error(VolcengineAuthError("bad token"))
    assert isinstance(result, DoubaoAuthError)
    assert isinstance(result, DoubaoSpeechError)
    assert "bad token" in str(result)


def test_translate_timeout_error() -> None:
    from doubao_speech._ws_client import VolcengineTimeoutError

    result = _translate_ws_error(VolcengineTimeoutError("stalled"))
    assert isinstance(result, DoubaoTimeoutError)


def test_translate_server_error_preserves_code() -> None:
    from doubao_speech._ws_client import VolcengineServerError

    result = _translate_ws_error(VolcengineServerError("boom", code=55000000))
    assert isinstance(result, DoubaoAPIError)
    assert result.code == 55000000


def test_translate_bare_timeout_error() -> None:
    """asyncio.TimeoutError / builtin TimeoutError (3.11+) should map too."""
    result = _translate_ws_error(TimeoutError("slow"))
    assert isinstance(result, DoubaoTimeoutError)


def test_translate_ffmpeg_missing_has_actionable_message() -> None:
    err = FileNotFoundError(2, "No such file or directory", "ffmpeg")
    result = _translate_ws_error(err)
    assert isinstance(result, DoubaoAPIError)
    assert "ffmpeg" in str(result).lower()
    assert "install" in str(result).lower()


def test_translate_unknown_exception_is_wrapped() -> None:
    class SomeRandomThing(Exception):
        pass

    result = _translate_ws_error(SomeRandomThing("mystery"))
    assert isinstance(result, DoubaoAPIError)
    assert "mystery" in str(result)
    assert "SomeRandomThing" in str(result)


def test_synthesize_translates_auth_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """End-to-end: a low-level auth failure surfaces as DoubaoAuthError."""
    from doubao_speech import _ws_client

    async def broken(text, output_path, **_kw):
        raise _ws_client.VolcengineAuthError("401 Unauthorized")

    monkeypatch.setattr(_ws_client, "tts_to_file", broken)

    with pytest.raises(DoubaoAuthError, match="Unauthorized"):
        synthesize("hi", tmp_path / "o.mp3")


def test_synthesize_preserves_cancellation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CancelledError must not be wrapped into DoubaoAPIError."""
    import asyncio

    from doubao_speech import _ws_client, synthesize_async

    async def cancelled(text, output_path, **_kw):
        raise asyncio.CancelledError()

    monkeypatch.setattr(_ws_client, "tts_to_file", cancelled)

    async def run() -> None:
        with pytest.raises(asyncio.CancelledError):
            await synthesize_async("hi", tmp_path / "o.mp3")

    asyncio.run(run())
