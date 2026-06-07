"""Command-line interface for doubao-speech.

Exposes subcommands:

- ``doubao-speech say TEXT --out FILE`` — text → audio (TTS)
- ``doubao-speech transcribe AUDIO`` — audio → text (STT)
- ``doubao-speech list-voices [--lang zh|en|...]``
- ``doubao-speech config {show,path}``
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from . import __version__
from ._logging import redact_secret
from .exceptions import DoubaoConfigError, DoubaoSpeechError


def _configure_logging(verbose: int) -> None:
    level = logging.WARNING
    if verbose >= 2:
        level = logging.DEBUG
    elif verbose == 1:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(__version__, "-V", "--version", prog_name="doubao-speech")
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (-v info, -vv debug).",
)
@click.pass_context
def main(ctx: click.Context, verbose: int) -> None:
    """doubao-speech — Volcengine Doubao voice client & CLI (TTS + STT)."""
    _configure_logging(verbose)
    ctx.ensure_object(dict)


# ---------------------------------------------------------------------------
# say (TTS)
# ---------------------------------------------------------------------------
@main.command()
@click.argument("text", required=False)
@click.option(
    "--text-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read the text to synthesize from this file instead of argv.",
)
@click.option(
    "--out",
    "-o",
    "output",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Write the generated audio to this path.",
)
@click.option("--voice", help="Friendly alias (see list-voices) or raw speaker ID.")
@click.option("--audio-format", type=click.Choice(["mp3", "wav", "ogg", "pcm"]))
@click.option("--sample-rate", type=int)
@click.option("--speed", type=float, help="Speaking-rate multiplier, e.g. 1.2.")
@click.option("--emotion", help="Emotion tag (model-dependent).")
@click.option("--emotion-scale", type=float, help="Emotion intensity, 0-5.")
@click.option("--loudness", type=float, help="Loudness adjustment in dB.")
def say(
    text: str | None,
    text_file: Path | None,
    output: Path,
    voice: str | None,
    audio_format: str | None,
    sample_rate: int | None,
    speed: float | None,
    emotion: str | None,
    emotion_scale: float | None,
    loudness: float | None,
) -> None:
    """Synthesize TEXT (or --text-file) and write audio to --out."""
    if text is None and text_file is None:
        raise click.UsageError("Provide TEXT positionally or --text-file PATH.")
    if text is not None and text_file is not None:
        raise click.UsageError("Use either TEXT or --text-file, not both.")

    payload = text if text is not None else text_file.read_text(encoding="utf-8")  # type: ignore[union-attr]
    if not payload.strip():
        raise click.UsageError("Text is empty.")

    # Import here to keep `doubao-speech --help` snappy.
    from .api import synthesize

    try:
        result = synthesize(
            payload,
            output,
            voice=voice,
            audio_format=audio_format,
            sample_rate=sample_rate,
            speed=speed,
            emotion=emotion,
            emotion_scale=emotion_scale,
            loudness=loudness,
        )
    except DoubaoSpeechError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"wrote {result}")


# ---------------------------------------------------------------------------
# transcribe (STT)
# ---------------------------------------------------------------------------
@main.command()
@click.argument(
    "audio",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=False,
)
@click.option(
    "--mic",
    is_flag=True,
    help="Transcribe live microphone input instead of a file (needs the 'mic' extra).",
)
@click.option(
    "--out",
    "-o",
    "output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the transcript to this path instead of stdout.",
)
@click.option(
    "--audio-format",
    type=click.Choice(["wav", "mp3", "ogg", "flac", "raw"]),
    help="Override audio format (auto-detected from extension otherwise).",
)
@click.option("--codec", type=click.Choice(["raw", "opus"]), default="raw", show_default=True)
@click.option("--sample-rate", type=int, default=16000, show_default=True)
@click.option(
    "--endpoint",
    type=click.Choice(["bigmodel", "bigmodel_async", "bigmodel_nostream"]),
    default=None,
    help=(
        "ASR endpoint. 'bigmodel' (default) = bidirectional streaming; "
        "'bigmodel_async' = optimized (server emits only on change, better "
        "RTF/latency on live streams); 'bigmodel_nostream' = streaming-input "
        "(highest accuracy, higher latency)."
    ),
)
@click.option(
    "--language",
    help=(
        "Accepted for cross-library compatibility; currently ignored by "
        "the Volcengine bigmodel endpoint, which auto-detects language."
    ),
)
@click.option("--no-itn", is_flag=True, help="Disable inverse text normalization (numbers, dates).")
@click.option("--no-punctuation", is_flag=True, help="Disable automatic punctuation.")
@click.option("--no-ddc", is_flag=True, help="Disable disfluency removal (um/uh).")
@click.option(
    "--segment-ms",
    type=int,
    default=200,
    show_default=True,
    help="Chunk duration sent to the ASR endpoint.",
)
@click.option("--timeout", type=float, default=60.0, show_default=True)
def transcribe(
    audio: Path | None,
    mic: bool,
    output: Path | None,
    audio_format: str | None,
    codec: str,
    sample_rate: int,
    endpoint: str | None,
    language: str | None,
    no_itn: bool,
    no_punctuation: bool,
    no_ddc: bool,
    segment_ms: int,
    timeout: float,
) -> None:
    """Transcribe an AUDIO file (or live --mic) using Volcengine bigmodel ASR."""
    if mic and audio is not None:
        raise click.UsageError("Use either AUDIO or --mic, not both.")
    if not mic and audio is None:
        raise click.UsageError("Provide an AUDIO file or pass --mic.")

    if mic:
        _run_microphone(
            output=output,
            sample_rate=sample_rate,
            endpoint=endpoint,
            enable_itn=not no_itn,
            enable_punc=not no_punctuation,
            enable_ddc=not no_ddc,
            chunk_ms=segment_ms,
            timeout=timeout,
        )
        return

    from .api import transcribe as _transcribe

    assert audio is not None  # guaranteed by the usage checks above

    try:
        text = _transcribe(
            audio,
            audio_format=audio_format,
            codec=codec,
            sample_rate=sample_rate,
            endpoint=endpoint,
            language=language,
            enable_itn=not no_itn,
            enable_punc=not no_punctuation,
            enable_ddc=not no_ddc,
            segment_duration_ms=segment_ms,
            timeout=timeout,
        )
    except DoubaoSpeechError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(1)

    if output:
        Path(output).write_text(text, encoding="utf-8")
        click.echo(f"wrote {output}")
    else:
        click.echo(text)


def _run_microphone(
    *,
    output: Path | None,
    sample_rate: int,
    endpoint: str | None,
    enable_itn: bool,
    enable_punc: bool,
    enable_ddc: bool,
    chunk_ms: int,
    timeout: float,
) -> None:
    """Drive live microphone transcription, printing partials until Ctrl-C."""
    import asyncio

    from .api import transcribe_microphone_async
    from .microphone import ensure_pyaudio

    # Fail fast (before printing "listening…") if pyaudio/PortAudio is missing,
    # so the install hint is the first and only thing the user sees.
    try:
        ensure_pyaudio()
    except DoubaoSpeechError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(1)

    # The mic stream is unbounded; bigmodel_async is the sensible default but
    # respect an explicit --endpoint when the user passed one.
    mic_endpoint = endpoint or "bigmodel_async"
    final_text = ""

    async def _drive() -> str:
        nonlocal final_text
        last = ""
        click.echo("listening… (Ctrl-C to stop)", err=True)
        async for result in transcribe_microphone_async(
            sample_rate=sample_rate,
            chunk_ms=chunk_ms,
            endpoint=mic_endpoint,
            enable_itn=enable_itn,
            enable_punc=enable_punc,
            enable_ddc=enable_ddc,
            timeout=timeout,
        ):
            text = result.get("text", "")
            if text and text != last:
                last = text
                final_text = text
                if not output:
                    # Live partials to stderr so stdout stays the clean transcript.
                    click.echo(f"\r{text}", nl=False, err=True)
        return final_text

    try:
        result_text = asyncio.run(_drive())
    except KeyboardInterrupt:
        result_text = final_text
        click.echo("", err=True)
    except DoubaoSpeechError as exc:
        click.echo(f"\nerror: {exc}", err=True)
        sys.exit(1)

    if not output:
        click.echo("", err=True)  # newline after the live partial line
    if output:
        Path(output).write_text(result_text, encoding="utf-8")
        click.echo(f"wrote {output}")
    else:
        click.echo(result_text)


# ---------------------------------------------------------------------------
# list-voices
# ---------------------------------------------------------------------------
@main.command("list-voices")
@click.option("--lang", help="Filter by language prefix (e.g. 'zh', 'en').")
def list_voices_cmd(lang: str | None) -> None:
    """Print the curated voice catalog."""
    from .voices import list_voices

    voices = list_voices(lang)
    if not voices:
        click.echo("(no voices match filter)")
        return

    width_alias = max(len(v.alias) for v in voices)
    width_lang = max(len(v.language) for v in voices)
    for v in voices:
        click.echo(
            f"{v.alias:<{width_alias}}  {v.language:<{width_lang}}  {v.gender:<6}  {v.style}"
        )


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
@main.group()
def config() -> None:
    """Inspect the effective configuration."""


@config.command("show")
def config_show() -> None:
    """Print resolved configuration with secrets redacted."""
    from .config import DoubaoConfig

    try:
        cfg = DoubaoConfig.resolve()
    except DoubaoConfigError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"app_id       : {redact_secret(cfg.app_id)}")
    click.echo(f"access_token : {redact_secret(cfg.access_token)}")
    click.echo(f"speaker      : {cfg.speaker}")
    click.echo(f"audio_format : {cfg.audio_format}")
    click.echo(f"sample_rate  : {cfg.sample_rate}")
    click.echo(f"resource_id  : {cfg.resource_id or '(default)'}")


@config.command("path")
def config_path() -> None:
    """Print the config-file path doubao-speech will look for."""
    from .config import DEFAULT_CONFIG_PATH

    click.echo(DEFAULT_CONFIG_PATH)


if __name__ == "__main__":  # pragma: no cover
    main()
