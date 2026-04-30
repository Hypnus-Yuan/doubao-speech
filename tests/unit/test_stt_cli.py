"""CLI transcribe subcommand tests (mocked, no network)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from doubao_speech.cli import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _creds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLCENGINE_APP_ID", "id_x")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "tok_very_long_example_token")


def test_transcribe_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["transcribe", "--help"])
    assert result.exit_code == 0
    assert "bigmodel" in result.output.lower()
    assert "AUDIO" in result.output


def test_transcribe_requires_existing_file(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(main, ["transcribe", str(tmp_path / "nope.wav")])
    assert result.exit_code != 0
    assert "does not exist" in result.output.lower() or "invalid" in result.output.lower()


def test_transcribe_stdout_default(runner: CliRunner, tmp_path: Path) -> None:
    audio = tmp_path / "in.wav"
    audio.write_bytes(b"fake-wav")

    def fake(audio_path, **_kw):
        return "兄弟早安"

    with patch("doubao_speech.api.transcribe", fake):
        result = runner.invoke(main, ["transcribe", str(audio)])
    assert result.exit_code == 0, result.output
    assert "兄弟早安" in result.output


def test_transcribe_writes_to_out(runner: CliRunner, tmp_path: Path) -> None:
    audio = tmp_path / "in.wav"
    audio.write_bytes(b"fake")
    out = tmp_path / "transcript.txt"

    def fake(audio_path, **_kw):
        return "这是一段转写文本。"

    with patch("doubao_speech.api.transcribe", fake):
        result = runner.invoke(main, ["transcribe", str(audio), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "这是一段转写文本。"
    assert "wrote" in result.output


def test_transcribe_flags_forward(runner: CliRunner, tmp_path: Path) -> None:
    audio = tmp_path / "in.mp3"
    audio.write_bytes(b"x")

    captured: dict = {}

    def fake(audio_path, **kw):
        captured.update(kw)
        return "ok"

    with patch("doubao_speech.api.transcribe", fake):
        result = runner.invoke(
            main,
            [
                "transcribe",
                str(audio),
                "--language",
                "zh-CN",
                "--no-itn",
                "--no-punctuation",
                "--sample-rate",
                "24000",
                "--segment-ms",
                "500",
            ],
        )
    assert result.exit_code == 0, result.output
    assert captured["language"] == "zh-CN"
    assert captured["enable_itn"] is False
    assert captured["enable_punc"] is False
    assert captured["sample_rate"] == 24000
    assert captured["segment_duration_ms"] == 500
