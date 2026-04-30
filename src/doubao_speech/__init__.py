"""doubao-speech — Python client & CLI for Volcengine Doubao voice APIs.

One Python package for both sides of the voice loop:

- **Text-to-speech** via seed-tts-2.0 bidirectional streaming.
- **Speech-to-text** via bigmodel streaming ASR.

This top-level import is intentionally cheap: nothing under :mod:`websockets`,
:mod:`yaml`, or any networking module is imported at package-load time.  All
public names are resolved on first attribute access via :pep:`562` lazy
``__getattr__``.

Public API
----------

- :func:`synthesize` — one-shot blocking TTS.
- :func:`synthesize_async` — the async TTS sibling.
- :func:`transcribe` — one-shot blocking STT.
- :func:`transcribe_async` — the async STT sibling.
- :class:`DoubaoConfig` — credential / voice / ASR defaults resolver.
- :class:`DoubaoSpeechError` (and subclasses) — public exception hierarchy.

Typical TTS usage::

    from doubao_speech import synthesize

    synthesize("你好，世界", "hello.mp3")

Typical STT usage::

    from doubao_speech import transcribe

    text = transcribe("meeting.mp3")
    print(text)

Credentials are auto-discovered in this order:

1. Keyword arguments to the public functions.
2. Environment variables (``VOLCENGINE_APP_ID`` / ``VOLCENGINE_ACCESS_TOKEN``).
3. ``~/.doubao-speech/config.yaml``.
4. Built-in defaults.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

try:
    __version__: str = version("doubao-speech")
except PackageNotFoundError:  # pragma: no cover — editable / dev install
    __version__ = "0.0.0"


__all__ = [
    "DoubaoAPIError",
    "DoubaoAuthError",
    "DoubaoConfig",
    "DoubaoConfigError",
    "DoubaoSpeechError",
    # Backwards-compat alias retained only for smoother onboarding of users
    # coming from ``doubao-tts``; prefer ``DoubaoSpeechError`` in new code.
    "DoubaoTTSError",
    "DoubaoTimeoutError",
    "__version__",
    "synthesize",
    "synthesize_async",
    "transcribe",
    "transcribe_async",
]


if TYPE_CHECKING:  # pragma: no cover — import-time-free type hints only
    from .api import synthesize, synthesize_async, transcribe, transcribe_async
    from .config import DoubaoConfig
    from .exceptions import (
        DoubaoAPIError,
        DoubaoAuthError,
        DoubaoConfigError,
        DoubaoSpeechError,
        DoubaoTimeoutError,
        DoubaoTTSError,
    )


_LAZY_ATTRS = {
    "synthesize": ("doubao_speech.api", "synthesize"),
    "synthesize_async": ("doubao_speech.api", "synthesize_async"),
    "transcribe": ("doubao_speech.api", "transcribe"),
    "transcribe_async": ("doubao_speech.api", "transcribe_async"),
    "DoubaoConfig": ("doubao_speech.config", "DoubaoConfig"),
    "DoubaoSpeechError": ("doubao_speech.exceptions", "DoubaoSpeechError"),
    "DoubaoTTSError": ("doubao_speech.exceptions", "DoubaoTTSError"),
    "DoubaoConfigError": ("doubao_speech.exceptions", "DoubaoConfigError"),
    "DoubaoAuthError": ("doubao_speech.exceptions", "DoubaoAuthError"),
    "DoubaoAPIError": ("doubao_speech.exceptions", "DoubaoAPIError"),
    "DoubaoTimeoutError": ("doubao_speech.exceptions", "DoubaoTimeoutError"),
}


def __getattr__(name: str) -> Any:
    """Lazily import public names on first access (PEP 562)."""
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    from importlib import import_module

    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value  # cache so subsequent lookups are free
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
