"""Logging helpers with credential and payload redaction.

Volcengine API calls carry two sensitive things that must never hit logs:

1. The ``access_token`` — leaking it gives another party full TTS quota.
2. The synthesis ``text`` — users may be reading private agent output,
   customer messages, or confidential documents aloud.

This module provides a single-line helper :func:`redact_secret` for tokens
and a logger-factory :func:`get_logger` that sets a sensible default
formatter without taking over the root logger.
"""

from __future__ import annotations

import logging
import os

_TRACE_ENV = "DOUBAO_SPEECH_TRACE_PAYLOADS"


def redact_secret(value: str | None) -> str:
    """Return a short, non-reversible fingerprint of a secret.

    - ``None`` / empty → empty string.
    - 1-8 chars → ``"***"`` (too short to fingerprint safely).
    - longer → first-4 + ``...`` + last-4.

    >>> redact_secret("sk_ABCDEFGHIJKLMN")
    'sk_A...KLMN'
    """
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def trace_payloads_enabled() -> bool:
    """True iff the user explicitly opted in to raw-payload logging.

    Controlled by the :envvar:`DOUBAO_SPEECH_TRACE_PAYLOADS` environment variable.
    Any truthy value (``1``, ``true``, ``yes``) enables tracing; tracing is
    off by default because payloads contain user text.
    """
    raw = os.environ.get(_TRACE_ENV, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_logger(name: str) -> logging.Logger:
    """Return a package logger; no handlers attached, no root pollution."""
    return logging.getLogger(name)
