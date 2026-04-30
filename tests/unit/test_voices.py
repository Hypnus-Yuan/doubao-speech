"""voices.py curated catalog tests."""

from __future__ import annotations

import pytest

from doubao_speech.voices import VOICES, Voice, list_voices, resolve_voice


def test_catalog_not_empty() -> None:
    assert len(VOICES) >= 1
    assert all(isinstance(v, Voice) for v in VOICES)


def test_aliases_are_unique() -> None:
    aliases = [v.alias for v in VOICES]
    assert len(aliases) == len(set(aliases)), "duplicate alias in catalog"


def test_speaker_ids_are_unique() -> None:
    ids = [v.speaker_id for v in VOICES]
    assert len(ids) == len(set(ids)), "duplicate speaker_id in catalog"


def test_resolve_known_alias() -> None:
    assert resolve_voice("zh-female-warm") == "zh_female_vv_uranus_bigtts"


def test_resolve_unknown_is_passthrough() -> None:
    # Users can pass a raw Volcengine speaker ID and we trust them.
    raw = "zh_female_custom_trained_12345"
    assert resolve_voice(raw) == raw


def test_resolve_rejects_empty() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        resolve_voice("")


def test_list_voices_no_filter() -> None:
    voices = list_voices()
    assert len(voices) == len(VOICES)


def test_list_voices_language_filter() -> None:
    zh_voices = list_voices("zh")
    assert all(v.language.lower().startswith("zh") for v in zh_voices)
    en_voices = list_voices("en")
    assert all(v.language.lower().startswith("en") for v in en_voices)


def test_list_voices_empty_filter_returns_empty() -> None:
    assert list_voices("xyz") == []
