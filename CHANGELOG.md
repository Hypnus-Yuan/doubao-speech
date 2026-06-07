# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Selectable ASR endpoint via `endpoint=` on `transcribe` / `transcribe_async`
  and `--endpoint` on the CLI. Accepts the aliases `bigmodel` (default),
  `bigmodel_async` (optimized: emits only when the result changes — better
  RTF and first/last-char latency on live streams), and `bigmodel_nostream`
  (streaming-input: highest accuracy on whole-file uploads), or an explicit
  `wss://` URL. All three share one wire protocol.
- `transcribe_stream_async(audio_source, ...)` — yields incremental
  `{"text", "is_final", "utterances"}` updates from any async byte source
  (microphone, socket, real-time-paced file).
- `transcribe_microphone_async(...)` — live microphone transcription,
  defaulting to the `bigmodel_async` endpoint. Plus `microphone_chunks()`,
  an async PCM16 capture generator. Requires the optional `mic` extra
  (`pip install "doubao-speech[mic]"`; PortAudio is a system dependency).
- CLI: `doubao-speech transcribe --mic` for live microphone input.

## [0.1.0] — 2026-05-01

Initial public release. Unifies TTS and STT for Volcengine Doubao into one Python package.

### Added

- `synthesize(text, out_path)` sync API and `synthesize_async` companion (TTS).
- `transcribe(audio)` sync API and `transcribe_async` companion (STT).
- CLI:
  - `doubao-speech say TEXT --out FILE` — text → audio
  - `doubao-speech transcribe AUDIO [--out FILE]` — audio → text
  - `doubao-speech list-voices [--lang zh|en|...]`
  - `doubao-speech config {show,path}`
- `DoubaoConfig.resolve` with precedence:
  keyword args > env vars > `~/.doubao-speech/config.yaml` > defaults.
- Curated voice catalogue with friendly aliases (`zh-female-warm`,
  `zh-male-warm`, `en-female-assistant`, ...). Raw Volcengine speaker IDs
  also pass through.
- Public exception hierarchy: `DoubaoSpeechError` (and `DoubaoTTSError` as
  back-compat alias), `DoubaoConfigError`, `DoubaoAuthError`,
  `DoubaoAPIError`, `DoubaoTimeoutError`.
- STT features: ITN, automatic punctuation, disfluency removal (DDC),
  utterance timestamps, low-latency streaming (200 ms default chunks).
- Credential fingerprinting helper and payload-log opt-in
  (`DOUBAO_SPEECH_TRACE_PAYLOADS=1`).
- 86 unit tests, 95% coverage, mypy strict on public modules.
- 2 integration tests including a TTS → STT roundtrip that validates
  both directions against the real Volcengine endpoint.
- macOS, Linux, Windows wheels on PyPI; Python 3.10-3.13.

### Relation to `doubao-tts`

This supersedes the earlier `doubao-tts` 0.1.0 package (TTS-only).
`doubao-tts` users can migrate by:

1. `pip install doubao-speech` and `pip uninstall doubao-tts`
2. Replacing `from doubao_tts import ...` with `from doubao_speech import ...`
3. Renaming the optional config file: `~/.doubao-tts/config.yaml` → `~/.doubao-speech/config.yaml`
4. Renaming the trace env var if used: `DOUBAO_TTS_TRACE_PAYLOADS` → `DOUBAO_SPEECH_TRACE_PAYLOADS`

The public API surface is otherwise identical for TTS paths; STT is purely
new capability.

[Unreleased]: https://github.com/Hypnus-Yuan/doubao-speech/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Hypnus-Yuan/doubao-speech/releases/tag/v0.1.0
