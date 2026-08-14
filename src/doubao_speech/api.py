"""Public high-level API for doubao-speech.

Four public entry points split across two directions:

- :func:`synthesize` / :func:`synthesize_async` — text → audio (TTS).
- :func:`transcribe`  / :func:`transcribe_async`  — audio → text (STT).

All four accept explicit kwargs; any value left as ``None`` is resolved
via :class:`doubao_speech.config.DoubaoConfig.resolve`.

:mod:`websockets` is imported lazily through :mod:`doubao_speech._ws_client`
so that ``import doubao_speech`` stays cheap.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from .config import DoubaoConfig
from .exceptions import (
    DoubaoAPIError,
    DoubaoAuthError,
    DoubaoConfigError,
    DoubaoTimeoutError,
)
from .voices import resolve_voice

__all__ = ["synthesize", "synthesize_async", "transcribe", "transcribe_async"]


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------
async def synthesize_async(
    text: str,
    output_path: str | Path,
    *,
    voice: str | None = None,
    app_id: str | None = None,
    access_token: str | None = None,
    api_key: str | None = None,
    audio_format: str | None = None,
    sample_rate: int | None = None,
    resource_id: str | None = None,
    speed: float | None = None,
    emotion: str | None = None,
    emotion_scale: float | None = None,
    loudness: float | None = None,
    config: DoubaoConfig | None = None,
    **extras: Any,
) -> Path:
    """Asynchronously synthesize ``text`` and write audio to ``output_path``.

    Authenticate with ``api_key`` (new console) or the legacy
    ``app_id`` / ``access_token`` pair.

    Returns
    -------
    pathlib.Path
        The written file path.
    """
    cfg = config or DoubaoConfig.resolve(
        app_id=app_id,
        access_token=access_token,
        api_key=api_key,
        speaker=resolve_voice(voice) if voice else None,
        audio_format=audio_format,
        sample_rate=sample_rate,
        resource_id=resource_id,
    )

    from . import _ws_client

    request_kwargs: dict[str, Any] = {
        "app_id": cfg.app_id,
        "access_token": cfg.access_token,
        "api_key": cfg.api_key,
        "speaker": cfg.speaker,
        "audio_format": cfg.audio_format,
        "sample_rate": cfg.sample_rate,
    }
    if cfg.resource_id:
        request_kwargs["resource_id"] = cfg.resource_id
    if speed is not None:
        # Public API uses "speed" (canonical in most TTS libs); Volcengine calls it speed_ratio.
        request_kwargs["speed_ratio"] = float(speed)
    if emotion is not None:
        request_kwargs["emotion"] = emotion
    if emotion_scale is not None:
        # Volcengine wants int on the wire even though users think of it as a float dial.
        request_kwargs["emotion_scale"] = int(emotion_scale)
    if loudness is not None:
        # Advertised in 0.1.0 prototypes but never wired: Volcengine seed-tts-2.0
        # has no dedicated loudness field. Raise loudly so we don't silently
        # accept an argument the server never sees.
        raise DoubaoConfigError(
            "loudness is not supported by doubao-speech 0.1.0; "
            "the Volcengine seed-tts-2.0 endpoint has no loudness field. "
            "Remove the argument or track https://github.com/Hypnus-Yuan/doubao-speech for support."
        )
    request_kwargs.update(cfg.extras)
    request_kwargs.update(extras)

    try:
        return await _ws_client.tts_to_file(text, output_path, **request_kwargs)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        raise _translate_ws_error(exc) from exc


def synthesize(
    text: str,
    output_path: str | Path,
    **kwargs: Any,
) -> Path:
    """Synchronous wrapper around :func:`synthesize_async`.

    Inside a running event loop, raises :class:`RuntimeError` — callers
    should ``await synthesize_async(...)`` directly.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(synthesize_async(text, output_path, **kwargs))
    raise RuntimeError(
        "synthesize() cannot be called from a running event loop; "
        "use `await synthesize_async(...)` instead."
    )


# ---------------------------------------------------------------------------
# STT
# ---------------------------------------------------------------------------
#: Default ASR resource ID for Volcengine bigmodel streaming.
DEFAULT_ASR_RESOURCE_ID = "volc.bigasr.sauc.duration"


def _asr_request_kwargs(
    *,
    cfg: DoubaoConfig,
    audio_format: str,
    codec: str,
    sample_rate: int,
    bits: int,
    channel: int,
    enable_itn: bool,
    enable_punc: bool,
    enable_ddc: bool,
    segment_duration_ms: int,
    resource_id: str | None,
    endpoint: str | None,
    timeout: float,
    extras: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the keyword arguments for :func:`_ws_client.asr_stream`.

    Single source of truth shared by :func:`transcribe_async` and
    :func:`transcribe_stream_async`, so the wire-request shape can't drift
    between the buffered and streaming entry points.
    """
    kwargs: dict[str, Any] = {
        "app_id": cfg.app_id,
        "access_token": cfg.access_token,
        "api_key": cfg.api_key,
        "audio_format": audio_format,
        "codec": codec,
        "sample_rate": sample_rate,
        "bits": bits,
        "channel": channel,
        "enable_itn": enable_itn,
        "enable_punc": enable_punc,
        "enable_ddc": enable_ddc,
        "show_utterances": True,
        "segment_duration_ms": segment_duration_ms,
        "resource_id": resource_id or DEFAULT_ASR_RESOURCE_ID,
        "endpoint": endpoint,
        "timeout": timeout,
    }
    kwargs.update(extras)
    return kwargs


async def transcribe_async(
    audio: str | Path | bytes,
    *,
    audio_format: str | None = None,
    codec: str = "raw",
    sample_rate: int = 16000,
    bits: int = 16,
    channel: int = 1,
    language: str | None = None,
    enable_itn: bool = True,
    enable_punc: bool = True,
    enable_ddc: bool = True,
    segment_duration_ms: int = 200,
    app_id: str | None = None,
    access_token: str | None = None,
    api_key: str | None = None,
    resource_id: str | None = None,
    endpoint: str | None = None,
    config: DoubaoConfig | None = None,
    timeout: float = 60.0,
    **extras: Any,
) -> str:
    """Asynchronously transcribe ``audio`` via Volcengine bigmodel streaming ASR.

    Authenticate with ``api_key`` (new console) or the legacy
    ``app_id`` / ``access_token`` pair.

    Parameters
    ----------
    audio :
        Audio source. Either a file path (``str`` / ``Path``) or raw bytes.
        File extensions ``.wav`` / ``.mp3`` / ``.ogg`` / ``.flac`` are
        auto-detected when ``audio_format`` is ``None``.
    codec :
        ``"raw"`` for PCM16 framing (default), ``"opus"`` for Opus.
    sample_rate / bits / channel :
        Only used for ``codec="raw"``; defaults match standard telephony.
    language :
        Accepted for cross-library API compatibility; **currently ignored**.
        The Volcengine bigmodel streaming ASR endpoint auto-detects language
        and does not expose a dedicated language field.  Kept in the
        signature so callers porting from Whisper / other STT libraries do
        not need to remove the argument.
    enable_itn :
        Inverse text normalization (e.g. "一百二十三" → "123").
    enable_punc :
        Insert punctuation.
    enable_ddc :
        Disfluency removal.
    segment_duration_ms :
        Size of each ASR audio chunk. Smaller = lower latency, higher
        network overhead.
    endpoint :
        Which Volcengine ASR endpoint to use. ``None`` (default) keeps the
        standard ``bigmodel`` bidirectional endpoint. Accepts the aliases
        ``"bigmodel"`` / ``"bigmodel_async"`` (optimized: server only emits a
        packet when the result changes — better RTF and first/last-char
        latency on genuinely streamed audio) / ``"bigmodel_nostream"``
        (streaming-input: highest accuracy, higher latency), or an explicit
        ``wss://`` URL. All endpoints share the same wire protocol.

    Returns
    -------
    str
        Final transcript (concatenated from all server-emitted utterances).
    """
    cfg = config or DoubaoConfig.resolve(
        app_id=app_id,
        access_token=access_token,
        api_key=api_key,
    )

    # Lazy import — keeps top-level `import doubao_speech` free of websockets.
    from . import _ws_client

    # Normalize audio source: accept Path/str/bytes; infer format from extension.
    if isinstance(audio, bytes):
        source: Any = audio
        inferred_format = audio_format or "raw"
    else:
        source = Path(audio)
        inferred_format = audio_format or _infer_audio_format(source)

    # ``language`` is accepted for cross-library symmetry but has no wire field
    # on the bigmodel endpoint (language is auto-detected); we drop it rather
    # than forward it to the low-level client.
    _ = language

    request_kwargs = _asr_request_kwargs(
        cfg=cfg,
        audio_format=inferred_format,
        codec=codec,
        sample_rate=sample_rate,
        bits=bits,
        channel=channel,
        enable_itn=enable_itn,
        enable_punc=enable_punc,
        enable_ddc=enable_ddc,
        segment_duration_ms=segment_duration_ms,
        resource_id=resource_id,
        endpoint=endpoint,
        timeout=timeout,
        extras=extras,
    )

    transcript = ""
    try:
        async for result in _ws_client.asr_stream(source, **request_kwargs):
            if result.get("text"):
                transcript = result["text"]
            if result.get("is_final"):
                break
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        raise _translate_ws_error(exc) from exc
    return transcript.strip()


def transcribe(audio: str | Path | bytes, **kwargs: Any) -> str:
    """Synchronous wrapper around :func:`transcribe_async`.

    Inside a running event loop, raises :class:`RuntimeError` — callers
    should ``await transcribe_async(...)`` directly.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(transcribe_async(audio, **kwargs))
    raise RuntimeError(
        "transcribe() cannot be called from a running event loop; "
        "use `await transcribe_async(...)` instead."
    )


async def transcribe_stream_async(
    audio_source: AsyncIterator[bytes],
    *,
    audio_format: str = "pcm",
    codec: str = "raw",
    sample_rate: int = 16000,
    bits: int = 16,
    channel: int = 1,
    enable_itn: bool = True,
    enable_punc: bool = True,
    enable_ddc: bool = True,
    segment_duration_ms: int = 200,
    app_id: str | None = None,
    access_token: str | None = None,
    api_key: str | None = None,
    resource_id: str | None = None,
    endpoint: str | None = None,
    config: DoubaoConfig | None = None,
    timeout: float = 30.0,
    **extras: Any,
) -> AsyncIterator[dict[str, Any]]:
    """Stream transcription results from a live async audio source.

    Authenticate with ``api_key`` (new console) or the legacy
    ``app_id`` / ``access_token`` pair.

    Unlike :func:`transcribe_async` (which buffers a finite source and returns
    a single final string), this yields the incremental
    ``{"text", "is_final", "utterances"}`` dicts as the server emits them —
    suitable for an unbounded source such as a microphone.

    ``audio_source`` must be an async iterator of raw audio bytes already in
    the advertised ``audio_format`` / ``codec`` (default: PCM16 mono, the
    format produced by :func:`doubao_speech.microphone_chunks`).

    ``endpoint`` selects the ASR endpoint; see :func:`transcribe_async`. For
    genuinely live streaming (e.g. a microphone) the ``"bigmodel_async"``
    optimized endpoint is usually the better default.

    Yields
    ------
    dict
        ``{"text": str, "is_final": bool, "utterances": list}`` per update.
    """
    cfg = config or DoubaoConfig.resolve(
        app_id=app_id,
        access_token=access_token,
        api_key=api_key,
    )

    from . import _ws_client

    request_kwargs = _asr_request_kwargs(
        cfg=cfg,
        audio_format=audio_format,
        codec=codec,
        sample_rate=sample_rate,
        bits=bits,
        channel=channel,
        enable_itn=enable_itn,
        enable_punc=enable_punc,
        enable_ddc=enable_ddc,
        segment_duration_ms=segment_duration_ms,
        resource_id=resource_id,
        endpoint=endpoint,
        timeout=timeout,
        extras=extras,
    )

    try:
        async for result in _ws_client.asr_stream(audio_source, **request_kwargs):
            yield result
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        raise _translate_ws_error(exc) from exc


async def transcribe_microphone_async(
    *,
    sample_rate: int = 16000,
    chunk_ms: int = 200,
    device_index: int | None = None,
    endpoint: str | None = "bigmodel_async",
    enable_itn: bool = True,
    enable_punc: bool = True,
    enable_ddc: bool = True,
    app_id: str | None = None,
    access_token: str | None = None,
    api_key: str | None = None,
    resource_id: str | None = None,
    config: DoubaoConfig | None = None,
    timeout: float = 30.0,
    **extras: Any,
) -> AsyncIterator[dict[str, Any]]:
    """Transcribe live microphone audio, yielding incremental results.

    Authenticate with ``api_key`` (new console) or the legacy
    ``app_id`` / ``access_token`` pair.

    Thin convenience wrapper that pipes :func:`doubao_speech.microphone_chunks`
    into :func:`transcribe_stream_async`. Requires the optional ``pyaudio``
    dependency (``pip install "doubao-speech[mic]"``).

    Defaults to the ``"bigmodel_async"`` optimized endpoint, which is the
    sweet spot for continuous live capture (the server only emits a packet
    when the recognized text changes).

    Yields
    ------
    dict
        ``{"text", "is_final", "utterances"}`` per update. For an open mic the
        stream is effectively unbounded; break out of the ``async for`` to stop.

    Raises
    ------
    DoubaoConfigError
        If ``pyaudio`` / PortAudio is unavailable.
    """
    from .microphone import ensure_pyaudio, microphone_chunks

    # Fail fast on a missing pyaudio *before* opening the WebSocket, so the
    # actionable install hint isn't masked by a later network/auth error.
    ensure_pyaudio()

    source = microphone_chunks(
        sample_rate=sample_rate,
        chunk_ms=chunk_ms,
        device_index=device_index,
    )
    async for result in transcribe_stream_async(
        source,
        audio_format="pcm",
        codec="raw",
        sample_rate=sample_rate,
        enable_itn=enable_itn,
        enable_punc=enable_punc,
        enable_ddc=enable_ddc,
        segment_duration_ms=chunk_ms,
        endpoint=endpoint,
        app_id=app_id,
        access_token=access_token,
        api_key=api_key,
        resource_id=resource_id,
        config=config,
        timeout=timeout,
        **extras,
    ):
        yield result


_FORMAT_BY_EXT = {
    ".wav": "wav",
    ".mp3": "mp3",
    ".ogg": "ogg",
    ".oga": "ogg",
    ".flac": "flac",
    ".pcm": "raw",
    ".raw": "raw",
}


def _infer_audio_format(path: Path) -> str:
    """Guess Volcengine-acceptable ``audio_format`` from a filename extension."""
    return _FORMAT_BY_EXT.get(path.suffix.lower(), "wav")


def _translate_ws_error(exc: BaseException) -> Exception:
    """Map internal ``_ws_client`` / OS exceptions to the public hierarchy.

    Keeps the public contract in ``exceptions.py`` honest: every error a user
    catches from :mod:`doubao_speech.api` inherits from
    :class:`DoubaoSpeechError`.  Preserves useful codes on
    :class:`DoubaoAPIError` when the upstream exception carries one.
    """
    from . import _ws_client

    message = str(exc)
    code_attr = getattr(exc, "code", None)
    code = code_attr if isinstance(code_attr, int) else None

    if isinstance(exc, _ws_client.VolcengineAuthError):
        return DoubaoAuthError(message)
    if isinstance(exc, _ws_client.VolcengineTimeoutError):
        return DoubaoTimeoutError(message)
    if isinstance(exc, _ws_client.VolcengineVoiceError):
        return DoubaoAPIError(message, code=code)
    if isinstance(exc, FileNotFoundError):
        # Most commonly: ``ffmpeg`` not on PATH when decoding MP3/OGG for STT.
        if "ffmpeg" in message.lower() or getattr(exc, "filename", "") == "ffmpeg":
            return DoubaoAPIError(
                "ffmpeg not found; install ffmpeg or pass a WAV/PCM input. "
                "macOS: 'brew install ffmpeg'; Ubuntu: 'apt install ffmpeg'."
            )
        return DoubaoAPIError(message)
    if isinstance(exc, TimeoutError):
        return DoubaoTimeoutError(message)
    if isinstance(exc, (OSError, ValueError)):
        return DoubaoAPIError(message)
    # Fallback: wrap unknown exception types rather than leak them.
    return DoubaoAPIError(f"unexpected doubao-speech failure: {type(exc).__name__}: {message}")
