"""DoubaoConfig.resolve precedence + error handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from doubao_speech.config import (
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_SPEAKER,
    DoubaoConfig,
)
from doubao_speech.exceptions import DoubaoConfigError


def test_kwarg_beats_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOLCENGINE_APP_ID", "env_id")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "env_token")
    cfg = DoubaoConfig.resolve(app_id="kw_id", access_token="kw_token")
    assert cfg.app_id == "kw_id"
    assert cfg.access_token == "kw_token"


def test_env_beats_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("app_id: file_id\naccess_token: file_token\n")
    monkeypatch.setenv("VOLCENGINE_APP_ID", "env_id")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "env_token")
    cfg = DoubaoConfig.resolve(config_path=config_file)
    assert cfg.app_id == "env_id"
    assert cfg.access_token == "env_token"


def test_file_beats_default(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "app_id: file_id\naccess_token: file_token\nspeaker: zh_male_yuanboxiaoshu_moon_bigtts\n"
    )
    cfg = DoubaoConfig.resolve(config_path=config_file)
    assert cfg.app_id == "file_id"
    assert cfg.speaker == "zh_male_yuanboxiaoshu_moon_bigtts"


def test_defaults_when_nothing_else(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With only creds in env, speaker/audio/sample-rate fall back to defaults."""
    monkeypatch.setenv("VOLCENGINE_APP_ID", "id_x")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "tok_x")
    missing = tmp_path / "does-not-exist.yaml"
    cfg = DoubaoConfig.resolve(config_path=missing)
    assert cfg.speaker == DEFAULT_SPEAKER
    assert cfg.audio_format == DEFAULT_AUDIO_FORMAT


def test_missing_app_id_raises() -> None:
    with pytest.raises(DoubaoConfigError, match="app_id"):
        DoubaoConfig.resolve(access_token="t", env={})


def test_missing_access_token_raises() -> None:
    with pytest.raises(DoubaoConfigError, match="access_token"):
        DoubaoConfig.resolve(app_id="i", env={})


def test_malformed_yaml_is_loud(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("not: valid: yaml: [")
    with pytest.raises(DoubaoConfigError, match="Malformed YAML"):
        DoubaoConfig.resolve(config_path=bad, env={"VOLCENGINE_APP_ID": "x"})


def test_non_mapping_yaml_is_loud(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a\n- list\n")
    with pytest.raises(DoubaoConfigError, match="must contain a YAML mapping"):
        DoubaoConfig.resolve(config_path=bad, env={"VOLCENGINE_APP_ID": "x"})


def test_empty_yaml_falls_through(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty config file shouldn't break resolution if env has creds."""
    empty = tmp_path / "empty.yaml"
    empty.write_text("")
    monkeypatch.setenv("VOLCENGINE_APP_ID", "id")
    monkeypatch.setenv("VOLCENGINE_ACCESS_TOKEN", "tok")
    cfg = DoubaoConfig.resolve(config_path=empty)
    assert cfg.app_id == "id"


def test_merge_overrides_selected_fields(tmp_path: Path) -> None:
    base = DoubaoConfig(app_id="a", access_token="t", speaker="sp1")
    merged = base.merge(speaker="sp2")
    assert merged.speaker == "sp2"
    assert merged.app_id == "a"  # preserved
    assert base.speaker == "sp1"  # original unchanged (frozen)


def test_repr_redacts_token() -> None:
    cfg = DoubaoConfig(app_id="12345678", access_token="abcdefghijklmnop")
    r = repr(cfg)
    assert "abcdefghijklmnop" not in r
    assert "abcd...mnop" in r


def test_env_alternate_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """DOUBAO_APP_ID works as alternative to VOLCENGINE_APP_ID."""
    monkeypatch.setenv("DOUBAO_APP_ID", "alt_id")
    monkeypatch.setenv("DOUBAO_ACCESS_TOKEN", "alt_tok")
    cfg = DoubaoConfig.resolve()
    assert cfg.app_id == "alt_id"
    assert cfg.access_token == "alt_tok"
