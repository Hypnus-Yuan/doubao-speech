"""Live end-to-end STT test.

Roundtrip philosophy: synthesize a known phrase via TTS, then transcribe
it back — this validates *both* directions of the package against the
real Volcengine endpoint.

Gated behind ``-m integration`` and skipped when creds are missing.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _have_creds() -> bool:
    return bool(os.environ.get("VOLCENGINE_APP_ID") and os.environ.get("VOLCENGINE_ACCESS_TOKEN"))


@pytest.mark.skipif(not _have_creds(), reason="No Volcengine credentials in env")
def test_tts_stt_roundtrip(tmp_path: Path) -> None:
    """Synthesize a phrase, then transcribe the generated audio."""
    from doubao_speech import synthesize, transcribe

    phrase = "兄弟早上好，今天天气不错。"
    audio = tmp_path / "roundtrip.mp3"

    synthesize(phrase, audio)
    assert audio.exists()
    assert audio.stat().st_size > 1000

    transcript = transcribe(audio)
    assert transcript, "empty transcript"
    # Fuzzy: Volcengine may normalize punctuation / lightly rephrase.
    # Require at least one content word from the original phrase.
    content_hits = sum(ch in transcript for ch in "兄弟早上好今天天气")
    assert content_hits >= 4, f"transcript '{transcript}' doesn't resemble phrase"
