"""api.synthesize / synthesize_async tests (no network).

We monkey-patch the low-level `tts_to_file` to avoid touching websockets
entirely — the goal here is to verify that high-level kwargs translate
correctly into request params and that config resolution happens.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from doubao_speech.api import synthesize, synthesize_async


class _RecordingFakeTTS:
    def __init__(self) -> None:
        self.last_kwargs: dict = {}

    async def tts_to_file(self, text: str, output_path, **kwargs) -> Path:
        self.last_kwargs = kwargs
        p = Path(output_path)
        p.write_bytes(b"MP3FAKE")
        return p


@pytest.fixture
def fake_ws(monkeypatch: pytest.MonkeyPatch) -> _RecordingFakeTTS:
    fake = _RecordingFakeTTS()
    # Replace the attribute on the lazy-imported module so the api sees our stub.
    from doubao_speech import _ws_client

    monkeypatch.setattr(_ws_client, "tts_to_file", fake.tts_to_file)
    return fake


@pytest.fixture(autouse=True)
def _creds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLCENGINE_APP_ID", "app_test_id")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "tok_test_value_long")


def test_sync_synthesize_writes_file(
    fake_ws: _RecordingFakeTTS,
    tmp_path: Path,
) -> None:
    out = synthesize("hello", tmp_path / "hello.mp3")
    assert out.exists()
    assert out.read_bytes() == b"MP3FAKE"


def test_api_key_credentials_propagate(
    fake_ws: _RecordingFakeTTS,
    tmp_path: Path,
) -> None:
    synthesize("hi", tmp_path / "o.mp3", api_key="new_api_key")

    assert fake_ws.last_kwargs["api_key"] == "new_api_key"
    assert fake_ws.last_kwargs["app_id"] is None
    assert fake_ws.last_kwargs["access_token"] is None


def test_credentials_propagate(
    fake_ws: _RecordingFakeTTS,
    tmp_path: Path,
) -> None:
    synthesize("hi", tmp_path / "o.mp3")
    assert fake_ws.last_kwargs["app_id"] == "app_test_id"
    assert fake_ws.last_kwargs["access_token"] == "tok_test_value_long"


def test_voice_alias_resolved(
    fake_ws: _RecordingFakeTTS,
    tmp_path: Path,
) -> None:
    synthesize("hi", tmp_path / "o.mp3", voice="zh-male-warm")
    assert fake_ws.last_kwargs["speaker"] == "zh_male_yuanboxiaoshu_moon_bigtts"


def test_raw_speaker_id_passthrough(
    fake_ws: _RecordingFakeTTS,
    tmp_path: Path,
) -> None:
    raw = "zh_female_custom_12345"
    synthesize("hi", tmp_path / "o.mp3", voice=raw)
    assert fake_ws.last_kwargs["speaker"] == raw


def test_default_speaker_when_none_given(
    fake_ws: _RecordingFakeTTS,
    tmp_path: Path,
) -> None:
    synthesize("hi", tmp_path / "o.mp3")
    assert fake_ws.last_kwargs["speaker"] == "zh_female_vv_uranus_bigtts"


def test_emotion_params_forwarded(
    fake_ws: _RecordingFakeTTS,
    tmp_path: Path,
) -> None:
    synthesize(
        "hi",
        tmp_path / "o.mp3",
        speed=1.2,
        emotion="happy",
        emotion_scale=3,
    )
    kw = fake_ws.last_kwargs
    # Public "speed" maps to Volcengine wire field "speed_ratio".
    assert kw["speed_ratio"] == 1.2
    assert "speed" not in kw
    assert kw["emotion"] == "happy"
    # emotion_scale coerced to int for the wire.
    assert kw["emotion_scale"] == 3
    assert isinstance(kw["emotion_scale"], int)


def test_none_params_not_forwarded(
    fake_ws: _RecordingFakeTTS,
    tmp_path: Path,
) -> None:
    """None kwargs should not end up in the request (server defaults apply)."""
    synthesize("hi", tmp_path / "o.mp3")
    kw = fake_ws.last_kwargs
    assert "speed" not in kw
    assert "emotion" not in kw


def test_sync_refuses_inside_running_loop(
    fake_ws: _RecordingFakeTTS,
    tmp_path: Path,
) -> None:
    async def run() -> None:
        with pytest.raises(RuntimeError, match="running event loop"):
            synthesize("hi", tmp_path / "o.mp3")

    asyncio.run(run())


def test_async_works_inside_loop(
    fake_ws: _RecordingFakeTTS,
    tmp_path: Path,
) -> None:
    async def run() -> Path:
        return await synthesize_async("hi", tmp_path / "o.mp3")

    result = asyncio.run(run())
    assert result.exists()
