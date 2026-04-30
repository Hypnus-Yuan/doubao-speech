"""api.transcribe / transcribe_async tests (no network).

Monkey-patches the low-level `asr_stream` so we don't touch websockets.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest


class _RecordingFakeASR:
    def __init__(self) -> None:
        self.last_source = None
        self.last_kwargs: dict = {}

    def asr_stream(self, source, **kwargs):
        """Return an async generator — matches the real asr_stream contract."""
        self.last_source = source
        self.last_kwargs = kwargs

        async def _gen() -> AsyncIterator[dict]:
            # Emit one partial and then a final chunk, like the real server would.
            yield {"text": "你好", "is_final": False}
            yield {"text": "你好，测试。", "is_final": True, "utterances": []}

        return _gen()


@pytest.fixture
def fake_asr(monkeypatch: pytest.MonkeyPatch) -> _RecordingFakeASR:
    fake = _RecordingFakeASR()
    from doubao_speech import _ws_client

    monkeypatch.setattr(_ws_client, "asr_stream", fake.asr_stream)
    return fake


@pytest.fixture(autouse=True)
def _creds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLCENGINE_APP_ID", "app_test_id")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "tok_test_value_long")


def test_sync_transcribe_returns_text(
    fake_asr: _RecordingFakeASR,
    tmp_path: Path,
) -> None:
    from doubao_speech import transcribe

    audio = tmp_path / "in.wav"
    audio.write_bytes(b"fake-wav-bytes")

    text = transcribe(audio)
    assert text == "你好，测试。"


def test_transcribe_credentials_propagate(
    fake_asr: _RecordingFakeASR,
    tmp_path: Path,
) -> None:
    from doubao_speech import transcribe

    audio = tmp_path / "in.wav"
    audio.write_bytes(b"x")
    transcribe(audio)
    assert fake_asr.last_kwargs["app_id"] == "app_test_id"
    assert fake_asr.last_kwargs["access_token"] == "tok_test_value_long"


def test_transcribe_infers_format_from_extension(
    fake_asr: _RecordingFakeASR,
    tmp_path: Path,
) -> None:
    from doubao_speech import transcribe

    for ext, expected in (
        (".wav", "wav"),
        (".mp3", "mp3"),
        (".ogg", "ogg"),
        (".flac", "flac"),
        (".raw", "raw"),
    ):
        audio = tmp_path / f"t{ext}"
        audio.write_bytes(b"x")
        transcribe(audio)
        assert fake_asr.last_kwargs["audio_format"] == expected, f"ext {ext}"


def test_transcribe_explicit_format_overrides_extension(
    fake_asr: _RecordingFakeASR,
    tmp_path: Path,
) -> None:
    from doubao_speech import transcribe

    audio = tmp_path / "weird.xyz"
    audio.write_bytes(b"x")
    transcribe(audio, audio_format="mp3")
    assert fake_asr.last_kwargs["audio_format"] == "mp3"


def test_transcribe_accepts_bytes(
    fake_asr: _RecordingFakeASR,
    tmp_path: Path,
) -> None:
    from doubao_speech import transcribe

    raw = b"\x00\x01\x02\x03" * 100
    text = transcribe(raw, audio_format="raw")
    assert text == "你好，测试。"
    assert fake_asr.last_source == raw


def test_transcribe_flags_enabled_by_default(
    fake_asr: _RecordingFakeASR,
    tmp_path: Path,
) -> None:
    from doubao_speech import transcribe

    audio = tmp_path / "t.wav"
    audio.write_bytes(b"x")
    transcribe(audio)
    kw = fake_asr.last_kwargs
    assert kw["enable_itn"] is True
    assert kw["enable_punc"] is True
    assert kw["enable_ddc"] is True


def test_transcribe_flags_can_be_disabled(
    fake_asr: _RecordingFakeASR,
    tmp_path: Path,
) -> None:
    from doubao_speech import transcribe

    audio = tmp_path / "t.wav"
    audio.write_bytes(b"x")
    transcribe(audio, enable_itn=False, enable_punc=False, enable_ddc=False)
    kw = fake_asr.last_kwargs
    assert kw["enable_itn"] is False
    assert kw["enable_punc"] is False
    assert kw["enable_ddc"] is False


def test_transcribe_language_hint_accepted(
    fake_asr: _RecordingFakeASR,
    tmp_path: Path,
) -> None:
    """``language`` kwarg is accepted but does not end up in the wire request.

    Volcengine bigmodel auto-detects language; the parameter is kept in the
    public API for symmetry with other STT libraries but silently ignored.
    """
    from doubao_speech import transcribe

    audio = tmp_path / "t.wav"
    audio.write_bytes(b"x")
    transcribe(audio, language="zh-CN")
    assert "language" not in fake_asr.last_kwargs


def test_transcribe_sync_refuses_running_loop(
    fake_asr: _RecordingFakeASR,
    tmp_path: Path,
) -> None:
    from doubao_speech import transcribe

    async def run() -> None:
        audio = tmp_path / "t.wav"
        audio.write_bytes(b"x")
        with pytest.raises(RuntimeError, match="running event loop"):
            transcribe(audio)

    asyncio.run(run())


def test_transcribe_async_works_inside_loop(
    fake_asr: _RecordingFakeASR,
    tmp_path: Path,
) -> None:
    from doubao_speech import transcribe_async

    async def run() -> str:
        audio = tmp_path / "t.wav"
        audio.write_bytes(b"x")
        return await transcribe_async(audio)

    result = asyncio.run(run())
    assert result == "你好，测试。"


def test_transcribe_default_resource_id(
    fake_asr: _RecordingFakeASR,
    tmp_path: Path,
) -> None:
    from doubao_speech import transcribe

    audio = tmp_path / "t.wav"
    audio.write_bytes(b"x")
    transcribe(audio)
    assert fake_asr.last_kwargs["resource_id"] == "volc.bigasr.sauc.duration"


def test_transcribe_custom_resource_id(
    fake_asr: _RecordingFakeASR,
    tmp_path: Path,
) -> None:
    from doubao_speech import transcribe

    audio = tmp_path / "t.wav"
    audio.write_bytes(b"x")
    transcribe(audio, resource_id="volc.bigasr.custom")
    assert fake_asr.last_kwargs["resource_id"] == "volc.bigasr.custom"
