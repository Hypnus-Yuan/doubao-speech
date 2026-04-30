"""CLI tests using click.testing.CliRunner (no network, no subprocess)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from doubao_speech.cli import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "say" in result.output
    assert "list-voices" in result.output
    assert "config" in result.output


def test_version(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "doubao-speech" in result.output


def test_list_voices_default(runner: CliRunner) -> None:
    result = runner.invoke(main, ["list-voices"])
    assert result.exit_code == 0
    assert "zh-female-warm" in result.output


def test_list_voices_filter_zh(runner: CliRunner) -> None:
    result = runner.invoke(main, ["list-voices", "--lang", "zh"])
    assert result.exit_code == 0
    assert "zh-female-warm" in result.output
    assert "en-female-assistant" not in result.output


def test_list_voices_filter_no_match(runner: CliRunner) -> None:
    result = runner.invoke(main, ["list-voices", "--lang", "xyz"])
    assert result.exit_code == 0
    assert "no voices match" in result.output


def test_config_path(runner: CliRunner) -> None:
    result = runner.invoke(main, ["config", "path"])
    assert result.exit_code == 0
    assert ".doubao-speech" in result.output


def test_config_show_without_creds_errors_loud(runner: CliRunner) -> None:
    """No creds → exit 1 with a helpful message, not a traceback."""
    result = runner.invoke(main, ["config", "show"])
    assert result.exit_code == 1
    assert "Missing" in result.output or "app_id" in result.output


def test_config_show_redacts(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VOLCENGINE_APP_ID", "app_1234567890")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "tok_very_long_secret_value")
    result = runner.invoke(main, ["config", "show"])
    assert result.exit_code == 0
    assert "tok_very_long_secret_value" not in result.output
    assert "tok_" in result.output  # prefix visible, middle hidden


def test_say_requires_text_or_file(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(main, ["say", "--out", str(tmp_path / "o.mp3")])
    assert result.exit_code != 0
    assert "TEXT" in result.output or "text-file" in result.output


def test_say_rejects_both_text_and_file(runner: CliRunner, tmp_path: Path) -> None:
    tf = tmp_path / "in.txt"
    tf.write_text("hi")
    result = runner.invoke(
        main,
        ["say", "hi", "--text-file", str(tf), "--out", str(tmp_path / "o.mp3")],
    )
    assert result.exit_code != 0


def test_say_empty_text_rejected(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(main, ["say", "   ", "--out", str(tmp_path / "o.mp3")])
    assert result.exit_code != 0
    assert "empty" in result.output.lower()


def test_say_happy_path_with_mocked_synthesize(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise argument parsing end-to-end without touching the network."""
    monkeypatch.setenv("VOLCENGINE_APP_ID", "id")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "tok_abcdef1234")

    out = tmp_path / "out.mp3"

    def fake_synth(text: str, output_path: Path, **_kw: object) -> Path:
        Path(output_path).write_bytes(b"fake-mp3")
        return Path(output_path)

    with patch("doubao_speech.api.synthesize", fake_synth):
        result = runner.invoke(main, ["say", "hello", "--out", str(out)])

    assert result.exit_code == 0, result.output
    assert out.exists()
    assert out.read_bytes() == b"fake-mp3"
    assert "wrote" in result.output
