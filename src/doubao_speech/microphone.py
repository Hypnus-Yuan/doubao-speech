"""Microphone capture helper for streaming ASR.

Provides :func:`microphone_chunks`, an async generator that yields raw
PCM16 mono audio chunks from the default input device, suitable for feeding
directly into :func:`doubao_speech.transcribe_stream_async`.

``pyaudio`` (and the system PortAudio library) is an **optional** dependency.
Install it with::

    pip install "doubao-speech[mic]"

    # PortAudio is a system dependency pyaudio links against:
    #   macOS:  brew install portaudio
    #   Ubuntu: sudo apt install portaudio19-dev

Keeping audio capture out of the core package means the 99% of users who only
transcribe files or feed their own audio source never pay the PortAudio build
cost.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from .exceptions import DoubaoConfigError

#: Default capture sample rate. Volcengine bigmodel ASR only accepts 16 kHz.
DEFAULT_SAMPLE_RATE = 16000

#: Default capture chunk in milliseconds. 200 ms is Volcengine's recommended
#: packet size for the bidirectional streaming endpoints.
DEFAULT_CHUNK_MS = 200


def ensure_pyaudio() -> Any:
    """Import and return :mod:`pyaudio`, or raise an actionable error.

    Public so callers can fail fast (before opening a WebSocket) when the
    optional ``pyaudio`` / PortAudio dependency is missing, keeping the install
    hint from being masked by a later network or auth error.
    """
    try:
        import pyaudio  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - exercised via monkeypatch
        raise DoubaoConfigError(
            "microphone capture requires the 'pyaudio' package. Install it with "
            "'pip install \"doubao-speech[mic]\"'. pyaudio links against the "
            "PortAudio system library: macOS 'brew install portaudio', "
            "Ubuntu 'sudo apt install portaudio19-dev'."
        ) from exc
    return pyaudio


async def microphone_chunks(
    *,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    chunk_ms: int = DEFAULT_CHUNK_MS,
    device_index: int | None = None,
) -> AsyncGenerator[bytes, None]:
    """Yield raw PCM16 mono audio chunks captured from the microphone.

    Runs the blocking ``stream.read`` in a worker thread so the event loop is
    never starved. Capture continues until the consumer stops iterating
    (e.g. breaks out of ``async for``), at which point the stream and PortAudio
    are torn down cleanly.

    Parameters
    ----------
    sample_rate :
        Capture sample rate in Hz. Volcengine bigmodel ASR requires 16000.
    chunk_ms :
        Duration of each yielded chunk in milliseconds.
    device_index :
        PortAudio input device index. ``None`` uses the system default.

    Yields
    ------
    bytes
        Little-endian signed 16-bit PCM, single channel.

    Raises
    ------
    DoubaoConfigError
        If ``pyaudio`` / PortAudio is not installed, or no input device is
        available.
    """
    pyaudio = ensure_pyaudio()

    frames_per_chunk = int(sample_rate * chunk_ms / 1000)
    pa = pyaudio.PyAudio()
    try:
        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                input=True,
                frames_per_buffer=frames_per_chunk,
                input_device_index=device_index,
            )
        except (OSError, ValueError) as exc:
            raise DoubaoConfigError(f"could not open microphone input stream: {exc}") from exc

        try:
            while True:
                data = await asyncio.to_thread(
                    stream.read, frames_per_chunk, exception_on_overflow=False
                )
                if data:
                    yield data
        finally:
            stream.stop_stream()
            stream.close()
    finally:
        pa.terminate()
