"""Microphone capture & streaming-transcription tests (#2) — no network, no audio HW.

A fake ``pyaudio`` module is injected so the capture path runs without
PortAudio or a real microphone. The streaming-transcription API is exercised
against the same fake ``asr_stream`` used by the file-transcription tests.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator

import pytest

from doubao_speech import _ws_client
from doubao_speech.exceptions import DoubaoConfigError


# ---------------------------------------------------------------------------
# Fake pyaudio
# ---------------------------------------------------------------------------
class _FakeStream:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)
        self.stopped = False
        self.closed = False

    def read(self, frames, exception_on_overflow=True):
        if self._chunks:
            return self._chunks.pop(0)
        return b""  # exhausted → empty (consumer is expected to stop)

    def stop_stream(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


class _FakePyAudio:
    paInt16 = 8

    def __init__(self) -> None:
        self.terminated = False
        self.opened_kwargs: dict = {}
        self.stream = _FakeStream([b"\x01\x00" * 10, b"\x02\x00" * 10, b"\x03\x00" * 10])

    def PyAudio(self):
        return self

    def open(self, **kwargs):
        self.opened_kwargs = kwargs
        return self.stream

    def terminate(self) -> None:
        self.terminated = True


@pytest.fixture
def fake_pyaudio(monkeypatch: pytest.MonkeyPatch) -> _FakePyAudio:
    fake = _FakePyAudio()
    monkeypatch.setitem(sys.modules, "pyaudio", fake)
    return fake


@pytest.fixture(autouse=True)
def _creds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLCENGINE_APP_ID", "app_test_id")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "tok_test_value_long")


# ---------------------------------------------------------------------------
# microphone_chunks
# ---------------------------------------------------------------------------
async def test_microphone_missing_pyaudio_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A clean, actionable error when pyaudio isn't installed."""
    monkeypatch.setitem(sys.modules, "pyaudio", None)  # force ImportError
    from doubao_speech.microphone import microphone_chunks

    with pytest.raises(DoubaoConfigError, match="pyaudio"):
        async for _ in microphone_chunks():
            break


async def test_microphone_yields_chunks(fake_pyaudio: _FakePyAudio) -> None:
    from contextlib import aclosing

    from doubao_speech.microphone import microphone_chunks

    got: list[bytes] = []
    # ``aclosing`` runs the generator's finally-block teardown deterministically
    # on exit (breaking out of ``async for`` alone does not run finally until
    # the generator is GC'd — this is the documented contract for cleanly
    # closing a live capture).
    async with aclosing(microphone_chunks(sample_rate=16000, chunk_ms=200)) as agen:
        async for chunk in agen:
            got.append(chunk)
            if len(got) == 3:
                break

    assert got == [b"\x01\x00" * 10, b"\x02\x00" * 10, b"\x03\x00" * 10]
    # Stream + PortAudio torn down on exit.
    assert fake_pyaudio.stream.stopped is True
    assert fake_pyaudio.stream.closed is True
    assert fake_pyaudio.terminated is True


async def test_microphone_opens_mono_16k(fake_pyaudio: _FakePyAudio) -> None:
    from doubao_speech.microphone import microphone_chunks

    async for _ in microphone_chunks(sample_rate=16000, chunk_ms=200):
        break

    kw = fake_pyaudio.opened_kwargs
    assert kw["channels"] == 1
    assert kw["rate"] == 16000
    assert kw["input"] is True
    assert kw["frames_per_buffer"] == 3200  # 16000 * 200 / 1000


# ---------------------------------------------------------------------------
# transcribe_stream_async / transcribe_microphone_async
# ---------------------------------------------------------------------------
class _RecordingFakeASR:
    def __init__(self) -> None:
        self.last_kwargs: dict = {}
        self.last_source = None

    def asr_stream(self, source, **kwargs):
        self.last_source = source
        self.last_kwargs = kwargs

        async def _gen() -> AsyncIterator[dict]:
            yield {"text": "你", "is_final": False, "utterances": []}
            yield {"text": "你好", "is_final": True, "utterances": []}

        return _gen()


@pytest.fixture
def fake_asr(monkeypatch: pytest.MonkeyPatch) -> _RecordingFakeASR:
    fake = _RecordingFakeASR()
    monkeypatch.setattr(_ws_client, "asr_stream", fake.asr_stream)
    return fake


async def _aiter(chunks: list[bytes]) -> AsyncIterator[bytes]:
    for c in chunks:
        yield c


async def test_transcribe_stream_yields_incremental(fake_asr: _RecordingFakeASR) -> None:
    from doubao_speech import transcribe_stream_async

    results = [r async for r in transcribe_stream_async(_aiter([b"\x00\x00" * 5]))]
    assert [r["text"] for r in results] == ["你", "你好"]
    assert results[-1]["is_final"] is True


async def test_transcribe_stream_forwards_endpoint(fake_asr: _RecordingFakeASR) -> None:
    from doubao_speech import transcribe_stream_async

    async for _ in transcribe_stream_async(_aiter([b"\x00\x00"]), endpoint="bigmodel_async"):
        pass
    assert fake_asr.last_kwargs["endpoint"] == "bigmodel_async"


async def test_transcribe_stream_default_endpoint_is_none(fake_asr: _RecordingFakeASR) -> None:
    from doubao_speech import transcribe_stream_async

    async for _ in transcribe_stream_async(_aiter([b"\x00\x00"])):
        pass
    assert fake_asr.last_kwargs["endpoint"] is None


async def test_transcribe_microphone_defaults_to_async_endpoint(
    fake_asr: _RecordingFakeASR, fake_pyaudio: _FakePyAudio
) -> None:
    from doubao_speech import transcribe_microphone_async

    results = []
    async for r in transcribe_microphone_async():
        results.append(r)
        if r["is_final"]:
            break

    # Mic default endpoint is the optimized async one.
    assert fake_asr.last_kwargs["endpoint"] == "bigmodel_async"
    # PCM16 mono wire format is advertised.
    assert fake_asr.last_kwargs["audio_format"] == "pcm"
    assert fake_asr.last_kwargs["codec"] == "raw"
    assert fake_asr.last_kwargs["sample_rate"] == 16000


async def test_transcribe_microphone_respects_explicit_endpoint(
    fake_asr: _RecordingFakeASR, fake_pyaudio: _FakePyAudio
) -> None:
    from doubao_speech import transcribe_microphone_async

    async for r in transcribe_microphone_async(endpoint="bigmodel"):
        if r["is_final"]:
            break
    assert fake_asr.last_kwargs["endpoint"] == "bigmodel"
