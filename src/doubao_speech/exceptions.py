"""Public exception hierarchy for doubao-speech.

All user-facing errors subclass :class:`DoubaoSpeechError`, so callers can
catch everything from this package with a single ``except`` clause::

    from doubao_speech import DoubaoSpeechError, synthesize

    try:
        synthesize("你好", "out.mp3")
    except DoubaoSpeechError as exc:
        log.error("Doubao failed: %s", exc)

Internal plumbing errors (for example, un-decodable WebSocket frames) are
converted to :class:`DoubaoAPIError` before they leave the package.

:class:`DoubaoTTSError` is kept as an alias for the canonical
:class:`DoubaoSpeechError` for users porting from the earlier
``doubao-tts`` package.
"""

from __future__ import annotations


class DoubaoSpeechError(Exception):
    """Base class for every error raised by :mod:`doubao_speech`."""


# Back-compat alias. New code should prefer :class:`DoubaoSpeechError`.
DoubaoTTSError = DoubaoSpeechError


class DoubaoConfigError(DoubaoSpeechError):
    """Raised when configuration is missing, malformed, or inconsistent.

    Examples: a malformed ``~/.doubao-speech/config.yaml``, unknown voice
    alias, or missing ``VOLCENGINE_APP_ID`` environment variable.
    """


class DoubaoAuthError(DoubaoSpeechError):
    """Raised when Volcengine rejects credentials (HTTP 401 / 403 equivalent)."""


class DoubaoAPIError(DoubaoSpeechError):
    """Raised when the upstream service returns a non-retryable error."""

    def __init__(self, message: str, *, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class DoubaoTimeoutError(DoubaoSpeechError):
    """Raised when the server stops sending frames inside the expected window."""
