# doubao-speech

English | [中文](README.zh.md)

[![PyPI](https://img.shields.io/pypi/v/doubao-speech.svg)](https://pypi.org/project/doubao-speech/)
[![Python](https://img.shields.io/pypi/pyversions/doubao-speech.svg)](https://pypi.org/project/doubao-speech/)
[![CI](https://github.com/Hypnus-Yuan/doubao-speech/actions/workflows/ci.yml/badge.svg)](https://github.com/Hypnus-Yuan/doubao-speech/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)](https://github.com/Hypnus-Yuan/doubao-speech/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-46aef7.svg)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/badge/package%20manager-uv-de5fe9.svg)](https://github.com/astral-sh/uv)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen.svg)](https://pre-commit.com/)
[![mypy strict](https://img.shields.io/badge/mypy-strict-blue.svg)](http://mypy-lang.org/)
[![Downloads](https://img.shields.io/pypi/dm/doubao-speech.svg)](https://pypistats.org/packages/doubao-speech)

> A production-minded Python client and CLI for Volcengine Doubao voice APIs —
> **seed-tts-2.0** (text → speech) and **bigmodel** (speech → text) in a single
> package. Native-quality Chinese voices with emotion control, and streaming
> ASR with ITN and punctuation.

## Why

`doubao-speech` is the first PyPI package that covers **both directions** of
Volcengine's modern voice stack:

- Other Python TTS wrappers hit the older SAMI HTTP endpoint (no streaming,
  older voice quality).
- No published PyPI package speaks seed-tts-2.0 bidi-stream **or** the
  bigmodel ASR endpoint.

This package fills that gap with a clean, unified surface:

- `synthesize()` / `transcribe()` for text → speech / speech → text.
- A CLI that drops straight into agent frameworks (Hermes Agent, Dify, LangChain, n8n, …).
- Strict mypy on every public module.
- 95% unit test coverage, atomic output writes, proper credential redaction.
- Same credentials, same config file, same error hierarchy for both directions.

## Install

```bash
pip install doubao-speech

# or with uv:
uv add doubao-speech

# CLI-only:
uv tool install doubao-speech
```

## Quick start

### Text → speech

```python
from doubao_speech import synthesize

synthesize("你好，世界", "hello.mp3")
```

### Speech → text

```python
from doubao_speech import transcribe

text = transcribe("meeting.mp3")
print(text)
```

### Async, both directions

```python
from doubao_speech import synthesize_async, transcribe_async

await synthesize_async(
    "Hello from Doubao seed-tts-2.0!",
    "hello.mp3",
    voice="en-female-assistant",
    speed=1.1,
)

transcript = await transcribe_async("interview.wav", enable_punc=True)
```

### Live microphone / streaming

Transcribe the microphone in real time (needs the optional `mic` extra:
`pip install "doubao-speech[mic]"`):

```python
from doubao_speech import transcribe_microphone_async

async for result in transcribe_microphone_async():
    print(result["text"], "(final)" if result["is_final"] else "")
```

`transcribe_microphone_async` is a thin wrapper over the lower-level
`transcribe_stream_async`, which accepts **any** async byte source — a mic,
a socket, a file paced in real time — and yields incremental
`{"text", "is_final", "utterances"}` updates:

```python
from doubao_speech import transcribe_stream_async, microphone_chunks

async for result in transcribe_stream_async(microphone_chunks(), endpoint="bigmodel_async"):
    ...
```

### Choosing an ASR endpoint

Volcengine exposes three bigmodel ASR endpoints. They share one wire
protocol, so `doubao-speech` lets you pick per call via `endpoint=`
(or `--endpoint` on the CLI):

| `endpoint`            | Behaviour                                              | Best for |
| --------------------- | ----------------------------------------------------- | -------- |
| `bigmodel` *(default)*| Bidirectional; one response per input packet          | Lowest first-char latency |
| `bigmodel_async`      | Bidirectional, optimized; emits only when text changes | Live streaming (better RTF / first-&-last-char latency) |
| `bigmodel_nostream`   | Streaming-input; returns after >15 s or the final packet | Highest accuracy on whole-file uploads |

`transcribe_microphone_async` defaults to `bigmodel_async`, the sweet spot
for continuous capture. You can also pass an explicit `wss://` URL.

### CLI

```bash
# TTS
doubao-speech say "你好" --out hello.mp3
doubao-speech say "好激动！" --voice zh-female-warm --speed 1.2 --out excited.mp3

# STT
doubao-speech transcribe meeting.mp3
doubao-speech transcribe voice-note.ogg --out transcript.txt
doubao-speech transcribe recording.wav --no-punctuation --sample-rate 16000
doubao-speech transcribe recording.wav --endpoint bigmodel_async   # optimized endpoint
doubao-speech transcribe --mic                                     # live microphone (needs [mic])

# Voice catalog
doubao-speech list-voices --lang zh

# Inspect effective config (tokens redacted)
doubao-speech config show
```

## Credentials

Resolve order — first match wins:

1. Keyword arguments to `synthesize(...)` / `transcribe(...)`
2. Environment variables
3. `~/.doubao-speech/config.yaml`
4. Built-in defaults

New Volcengine Speech console (recommended):

```bash
export DOUBAO_API_KEY="..."
```

Legacy App ID + Access Token authentication remains supported:

```bash
export VOLCENGINE_APP_ID="..."
export VOLCENGINE_ACCESS_TOKEN="..."
```

`DOUBAO_APP_ID` and `DOUBAO_ACCESS_TOKEN` are accepted as legacy aliases.
When both authentication methods exist at the same resolution level,
`DOUBAO_API_KEY` takes precedence. Explicit legacy keyword arguments still
override an API key found in the environment or config file.

Example `~/.doubao-speech/config.yaml`:

```yaml
api_key: "..."
speaker: zh_female_vv_uranus_bigtts
audio_format: mp3
sample_rate: 24000
```

For a legacy-console application, use `app_id` and `access_token` instead of
`api_key` in the same file.

Credentials come from the [Volcengine Speech console](https://console.volcengine.com/speech/service).
You need **seed-tts-2.0** activated for TTS and a **bigmodel ASR** resource
enabled for STT (free tier suffices for testing).

## Hermes Agent integration

[Hermes Agent](https://github.com/NousResearch/hermes-agent)'s declarative
`tts.providers.<name>` command-type surface makes `doubao-speech` a one-liner:

```yaml
# ~/.hermes/config.yaml
tts:
  provider: doubao
  providers:
    doubao:
      type: command
      command: 'doubao-speech say --text-file {input_path} --out {output_path}'
      output_format: mp3
      max_text_length: 1024
      timeout: 30
```

Any Hermes voice-out path now routes through Doubao seed-tts-2.0.

For speech-to-text, use Hermes' local-command STT provider with the same
`doubao-speech` CLI:

```bash
export HERMES_LOCAL_STT_COMMAND='doubao-speech transcribe {input_path} --out {output_dir}/transcript.txt'
```

```yaml
# ~/.hermes/config.yaml
stt:
  provider: local_command
```

Hermes writes the incoming voice message to `{input_path}`, runs the command,
and reads the `.txt` transcript produced under `{output_dir}`.

## Audio format support

| Direction | Input / Output | Notes |
|---|---|---|
| TTS | `mp3` (default), `wav`, `ogg`, `pcm` | 24 kHz by default |
| STT | `wav`, `mp3`, `ogg`, `flac`, `raw` PCM | Auto-detected from extension; requires `ffmpeg` for non-WAV inputs |

For STT, non-WAV inputs are transcoded to PCM16 mono via `ffmpeg` at the
target sample rate. Install ffmpeg once (`brew install ffmpeg` /
`apt install ffmpeg`) and any format works.

## Voices (TTS)

The CLI ships with curated aliases for common voices:

| Alias | Language | Gender | Style |
|---|---|---|---|
| `zh-female-warm` (default) | zh-CN | female | warm, conversational |
| `zh-female-reporter` | zh-CN | female | crisp, news-reporter |
| `zh-male-warm` | zh-CN | male | warm, narrator |
| `zh-male-energetic` | zh-CN | male | energetic host |
| `en-female-assistant` | en-US | female | assistant, neutral |
| `en-male-assistant` | en-US | male | assistant, neutral |

Volcengine publishes hundreds more speaker IDs; pass any raw speaker ID
to `voice=` directly.

## Emotion control

seed-tts-2.0 supports per-utterance emotion tags:

```python
synthesize(
    "好激动，我终于做到了！",
    "out.mp3",
    emotion="excited",
    emotion_scale=4.0,  # 0-5; higher = more intense
)
```

Supported emotions vary by speaker — check the Volcengine console.

## STT features

- **ITN** (inverse text normalization): "一百二十三" → "123"
- **Punctuation**: Automatic commas, periods, question marks
- **Disfluency removal** (DDC): Strips "嗯", "啊", repeated syllables
- **Utterance timestamps**: Available on the async generator path
- **Low-latency streaming**: 200ms chunks by default; tune via `--segment-ms`

Disable any of the above with flags:

```bash
doubao-speech transcribe lecture.mp3 --no-itn --no-punctuation --no-ddc
```

Or in Python:

```python
transcribe("lecture.mp3", enable_itn=False, enable_punc=False, enable_ddc=False)
```

## Performance

- **TTS**: One synthesize call opens a fresh WebSocket and tears it down at
  the end. End-to-end latency for ~2 s of speech is **~750 ms** on a healthy
  connection — network dominates.
- **STT**: Streaming starts returning partial transcripts within **~500 ms**.
  Final transcript for a 10 s clip arrives in **~1.5-2 s** total.
- `import doubao_speech` is **~3 ms** — `websockets` and `yaml` are loaded
  lazily only when you actually call `synthesize()` / `transcribe()`.

## Error handling

All user-facing errors inherit from `DoubaoSpeechError`:

```python
from doubao_speech import (
    DoubaoSpeechError, DoubaoConfigError,
    DoubaoAuthError, DoubaoAPIError, DoubaoTimeoutError,
    synthesize, transcribe,
)

try:
    transcribe("audio.mp3")
except DoubaoAuthError:
    ...  # rotate your token
except DoubaoTimeoutError:
    ...  # retry or check network
except DoubaoSpeechError as exc:
    ...  # catch-all
```

`DoubaoTTSError` is kept as a back-compat alias for users porting from
the earlier `doubao-tts` package.

## Security

- Access tokens are redacted in all logs and CLI output —
  see [`SECURITY.md`](SECURITY.md) for the exact policy.
- User text and transcribed content are **not** logged by default. Opt in
  with `DOUBAO_SPEECH_TRACE_PAYLOADS=1` only for protocol debugging.
- `~/.doubao-speech/config.yaml` is user-scoped; the shipped `.gitignore`
  excludes `.env` files.
- Report vulnerabilities: `hypnus.yuan@gmail.com` or a private GitHub
  security advisory.

## Development

```bash
git clone https://github.com/Hypnus-Yuan/doubao-speech.git
cd doubao-speech

uv sync --all-extras --group dev
uv run pre-commit install
uv run pytest
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full workflow.

## Roadmap

- **v0.2** — connection-reuse daemon (TCP+TLS amortization), streaming
  callback API for partial transcripts, richer voice metadata sync.
- **v0.3** — LangChain/LlamaIndex/Dify integration recipes.
- **v1.0** — API frozen, semver guarantees.

## License

MIT — see [`LICENSE`](LICENSE).

## Credits

Protocol framing extracted and hardened from
[Hermes Agent](https://github.com/NousResearch/hermes-agent) community work.
Thanks to the Volcengine Speech team for the seed-tts-2.0 bidirectional
streaming API and the bigmodel ASR endpoint.
