"""Live end-to-end test against the real Volcengine seed-tts-2.0 endpoint.

Gated behind ``-m integration`` and skipped automatically when
``VOLCENGINE_APP_ID`` / ``VOLCENGINE_ACCESS_TOKEN`` are not set.

CI runs this only on pushes from trusted branches where repo secrets
are available. PRs from forks get the unit suite only.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _have_creds() -> bool:
    return bool(os.environ.get("VOLCENGINE_APP_ID") and os.environ.get("VOLCENGINE_ACCESS_TOKEN"))


@pytest.mark.skipif(not _have_creds(), reason="No Volcengine credentials in env")
def test_synthesize_produces_non_empty_mp3(tmp_path: Path) -> None:
    from doubao_speech import synthesize

    out = tmp_path / "live.mp3"
    result = synthesize("你好，测试。", out)
    assert result.exists()
    size = out.stat().st_size
    assert size > 1000, f"suspiciously small output: {size} bytes"
    # MP3 files start with either "ID3" or a frame sync (0xFF 0xFB / 0xFF 0xF3 etc.)
    head = out.read_bytes()[:3]
    assert head[:3] == b"ID3" or head[0] == 0xFF, f"not a valid MP3 header: {head!r}"
