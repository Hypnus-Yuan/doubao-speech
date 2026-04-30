"""Curated Volcengine seed-tts-2.0 voice catalog.

This module ships a small, hand-picked voice dictionary. The Volcengine
console lists hundreds of speakers with shifting IDs, so the catalog is
deliberately conservative — only voices we have verified to work with
the seed-tts-2.0 bidirectional endpoint are listed.

Users may pass any Volcengine speaker ID directly to
:func:`doubao_speech.synthesize`; the alias table is purely a convenience
for the CLI ``list-voices`` and ``--voice <alias>`` syntax.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Voice:
    """A Volcengine speaker entry with a friendly alias."""

    alias: str
    speaker_id: str
    language: str  # BCP-47-style language tag, e.g. "zh-CN" or "en-US"
    gender: str  # "female" | "male" | "neutral"
    style: str  # short description (e.g. "warm", "reporter", "assistant")


# Curated list — verified on seed-tts-2.0 bidi endpoint, 2026-04.
# Always prefer the alias in user-facing code; speaker_id is the wire value.
VOICES: tuple[Voice, ...] = (
    Voice(
        alias="zh-female-warm",
        speaker_id="zh_female_vv_uranus_bigtts",
        language="zh-CN",
        gender="female",
        style="warm, conversational (default)",
    ),
    Voice(
        alias="zh-female-reporter",
        speaker_id="zh_female_shuangkuaisisi_moon_bigtts",
        language="zh-CN",
        gender="female",
        style="crisp, news-reporter",
    ),
    Voice(
        alias="zh-male-warm",
        speaker_id="zh_male_yuanboxiaoshu_moon_bigtts",
        language="zh-CN",
        gender="male",
        style="warm, narrator",
    ),
    Voice(
        alias="zh-male-energetic",
        speaker_id="zh_male_jieshuonansheng_mars_bigtts",
        language="zh-CN",
        gender="male",
        style="energetic host",
    ),
    Voice(
        alias="en-female-assistant",
        speaker_id="en_female_anna_mars_bigtts",
        language="en-US",
        gender="female",
        style="assistant, neutral",
    ),
    Voice(
        alias="en-male-assistant",
        speaker_id="en_male_adam_mars_bigtts",
        language="en-US",
        gender="male",
        style="assistant, neutral",
    ),
)


_ALIAS_INDEX = {v.alias: v for v in VOICES}


def resolve_voice(name: str) -> str:
    """Return the wire-level speaker ID for an alias or pass-through ID.

    - If ``name`` matches a known alias, return the mapped ``speaker_id``.
    - Otherwise return ``name`` unchanged (caller passed a raw Volcengine
      speaker ID — we trust them).
    """
    if not name:
        raise ValueError("voice name must be a non-empty string")
    voice = _ALIAS_INDEX.get(name)
    return voice.speaker_id if voice else name


def list_voices(language: str | None = None) -> list[Voice]:
    """Return curated voices, optionally filtered by language tag prefix."""
    if language is None:
        return list(VOICES)
    prefix = language.lower()
    return [v for v in VOICES if v.language.lower().startswith(prefix)]
