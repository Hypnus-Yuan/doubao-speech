# doubao-speech

[English](README.md) | 中文

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

> 面向 Agent、脚本、服务化 pipeline 的火山引擎豆包语音统一客户端 ——
> 一个包同时支持 **seed-tts-2.0** 双向流式 TTS 和 **bigmodel** 流式 ASR。
> 开箱即用的中文原生音色、情感控制，加上带 ITN 和标点的流式语音识别。

## 为什么造这个

`doubao-speech` 是 PyPI 上**第一个同时覆盖**火山引擎现代语音栈双向的包：

- 已有的 Python TTS 封装对接更老的 SAMI HTTP 端点（不支持流式、音色旧一代）。
- 没有已发布到 PyPI 的包能接 seed-tts-2.0 双向流式 API **或** bigmodel ASR。

本包用统一干净的接口填补了空白：

- `synthesize()` / `transcribe()` —— 文本→语音 / 语音→文本。
- 命令行工具可直接接入 Agent 框架（Hermes、Dify、LangChain、n8n 等）。
- 公共模块全部 mypy strict。
- 95% 单元测试覆盖率、原子写文件、凭证严格脱敏。
- TTS 和 STT 共用同一套凭证、同一个 config 文件、同一个错误等级。

## 安装

```bash
pip install doubao-speech

# 或用 uv：
uv add doubao-speech

# 只装 CLI 工具：
uv tool install doubao-speech
```

## 快速开始

### 文本→语音

```python
from doubao_speech import synthesize

synthesize("你好，世界", "hello.mp3")
```

### 语音→文本

```python
from doubao_speech import transcribe

text = transcribe("会议.mp3")
print(text)
```

### 异步接口，双向

```python
from doubao_speech import synthesize_async, transcribe_async

await synthesize_async(
    "大家好，我是豆包 seed-tts-2.0。",
    "hello.mp3",
    voice="zh-female-warm",
    speed=1.1,
)

transcript = await transcribe_async("访谈.wav", enable_punc=True)
```

### 实时麦克风 / 流式

实时转写麦克风输入（需要可选的 `mic` 额外依赖：
`pip install "doubao-speech[mic]"`）：

```python
from doubao_speech import transcribe_microphone_async

async for result in transcribe_microphone_async():
    print(result["text"], "(final)" if result["is_final"] else "")
```

`transcribe_microphone_async` 是底层 `transcribe_stream_async` 的轻量封装。
后者接受**任意**异步字节源——麦克风、socket、按实时节奏分包的文件——并逐步
yield `{"text", "is_final", "utterances"}` 增量结果：

```python
from doubao_speech import transcribe_stream_async, microphone_chunks

async for result in transcribe_stream_async(microphone_chunks(), endpoint="bigmodel_async"):
    ...
```

### 选择 ASR 接口

火山引擎提供三个 bigmodel ASR 接口，三者共用同一套二进制协议，因此
`doubao-speech` 允许按调用通过 `endpoint=`（或 CLI 的 `--endpoint`）切换：

| `endpoint`            | 行为                                          | 适用场景 |
| --------------------- | --------------------------------------------- | -------- |
| `bigmodel`（默认）    | 双向流式；每输入一包返回一包                   | 首字时延最低 |
| `bigmodel_async`      | 双向流式优化版；仅结果变化时返包               | 实时流式（RTF / 首尾字时延更优） |
| `bigmodel_nostream`   | 流式输入；>15 s 或收尾包后返回                 | 整文件上传时准确率最高 |

`transcribe_microphone_async` 默认使用 `bigmodel_async`，这是持续采集的
最佳选择。也可直接传入完整的 `wss://` URL。

### 命令行

```bash
# TTS
doubao-speech say "你好" --out hello.mp3
doubao-speech say "好激动！" --voice zh-female-warm --speed 1.2 --out excited.mp3

# STT
doubao-speech transcribe 会议.mp3
doubao-speech transcribe 语音留言.ogg --out transcript.txt
doubao-speech transcribe 录音.wav --no-punctuation --sample-rate 16000
doubao-speech transcribe 录音.wav --endpoint bigmodel_async   # 优化版接口
doubao-speech transcribe --mic                                # 实时麦克风（需 [mic]）

# 音色列表
doubao-speech list-voices --lang zh

# 查看生效配置（token 自动脱敏）
doubao-speech config show
```

## 凭证配置

鉴权优先级（**首个完整可用的鉴权方式生效**）：

1. 显式传入旧鉴权 `app_id=` / `access_token=` keyword 参数
2. 环境变量中的完整旧鉴权参数对
3. 显式传入 `api_key=` keyword 参数
4. 环境变量 `DOUBAO_API_KEY` / `VOLCENGINE_API_KEY`
5. `~/.doubao-speech/config.yaml` 中的凭证

新版火山引擎语音控制台（推荐）：

```bash
export DOUBAO_API_KEY="..."
```

原有 App ID + Access Token 鉴权继续保留：

```bash
export VOLCENGINE_APP_ID="..."
export VOLCENGINE_ACCESS_TOKEN="..."
```

旧鉴权也接受 `DOUBAO_APP_ID` / `DOUBAO_ACCESS_TOKEN` 别名。配置文件中同时存在
两种鉴权时优先使用 API Key。显式传入不完整的旧鉴权参数时，可由环境变量或
配置文件补齐；仍无法组成完整参数对则鉴权校验失败。

`~/.doubao-speech/config.yaml` 示例：

```yaml
api_key: "..."
speaker: zh_female_vv_uranus_bigtts
audio_format: mp3
sample_rate: 24000
```

旧版控制台应用可在同一文件中改用 `app_id` 和 `access_token`。

凭证来自 [火山引擎语音控制台](https://console.volcengine.com/speech/service)，
TTS 需要开通 **seed-tts-2.0**，STT 需要开通 **bigmodel** 流式 ASR 资源
（免费额度足够做测试）。

## 与 Hermes Agent 集成

[Hermes Agent](https://github.com/NousResearch/hermes-agent) 的声明式
`tts.providers.<name>` command-type 接口让 `doubao-speech` 集成变成一行事：

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

所有 Hermes 的语音输出路径现在都走豆包 seed-tts-2.0。

语音转文字可以使用 Hermes 的 local-command STT provider，继续复用同一个
`doubao-speech` CLI：

```bash
export HERMES_LOCAL_STT_COMMAND='doubao-speech transcribe {input_path} --out {output_dir}/transcript.txt'
```

```yaml
# ~/.hermes/config.yaml
stt:
  provider: local_command
```

Hermes 会把收到的语音消息写到 `{input_path}`，运行上面的命令，然后读取
`{output_dir}` 下生成的 `.txt` 转写结果。

## 音频格式支持

| 方向 | 支持格式 | 备注 |
|---|---|---|
| TTS | `mp3`（默认）、`wav`、`ogg`、`pcm` | 默认 24 kHz |
| STT | `wav`、`mp3`、`ogg`、`flac`、`raw` PCM | 根据扩展名自动识别；非 WAV 输入需要 `ffmpeg` |

STT 的非 WAV 输入会通过 `ffmpeg` 转成 PCM16 单声道到目标采样率。装一次
ffmpeg（`brew install ffmpeg` / `apt install ffmpeg`）所有格式就都能用。

## 内置音色 (TTS)

CLI 内置常用音色别名：

| 别名 | 语言 | 性别 | 风格 |
|---|---|---|---|
| `zh-female-warm`（默认）| 中文普通话 | 女 | 温暖、日常对话 |
| `zh-female-reporter` | 中文普通话 | 女 | 清脆、新闻播报 |
| `zh-male-warm` | 中文普通话 | 男 | 温暖、叙事 |
| `zh-male-energetic` | 中文普通话 | 男 | 活泼、主持 |
| `en-female-assistant` | 英语 | 女 | 助理、中性 |
| `en-male-assistant` | 英语 | 男 | 助理、中性 |

火山引擎平台上还有几百个音色 ID。直接把原始 speaker ID 传给
`voice=` 参数也可以。

## 情感控制

seed-tts-2.0 支持逐句情感标签：

```python
synthesize(
    "好激动，我终于做到了！",
    "out.mp3",
    emotion="excited",
    emotion_scale=4.0,  # 0-5，越大越强烈
)
```

每个音色支持的情感类型不一样，到火山引擎控制台查看当前可用列表。

## STT 功能

- **ITN**（数字/日期规范化）：比如 "一百二十三" → "123"
- **自动标点**：逗号、句号、问号
- **语气词过滤** (DDC)：去掉 "嗯"、"啊"、重复音节
- **句级时间戳**：在 async generator 路径上可拿到
- **低延迟流式**：默认 200ms 分片；通过 `--segment-ms` 可调

任何功能都能关掉：

```bash
doubao-speech transcribe 讲座.mp3 --no-itn --no-punctuation --no-ddc
```

Python 里同理：

```python
transcribe("讲座.mp3", enable_itn=False, enable_punc=False, enable_ddc=False)
```

## 性能

- **TTS**：每次调用开一条新 WebSocket 连接，结束后关闭。~2 秒语音的
  端到端延迟大约 **750 ms**，瓶颈在网络。
- **STT**：**~500 ms** 内开始返回 partial transcript。10 秒音频的
  完整转写大约 **1.5-2 秒**。
- `import doubao_speech` 很轻量 —— **约 3 ms** —— 因为 `websockets`
  和 `yaml` 都是懒加载，只有真正调用时才导入。

## 错误处理

所有用户能碰到的错误都继承自 `DoubaoSpeechError`：

```python
from doubao_speech import (
    DoubaoSpeechError, DoubaoConfigError,
    DoubaoAuthError, DoubaoAPIError, DoubaoTimeoutError,
    synthesize, transcribe,
)

try:
    transcribe("audio.mp3")
except DoubaoAuthError:
    ...  # token 错了，需要重置
except DoubaoTimeoutError:
    ...  # 网络或服务端超时，可以重试
except DoubaoSpeechError as exc:
    ...  # 兜底
```

`DoubaoTTSError` 保留为向后兼容别名（从更早的 `doubao-tts` 包迁移过来的用户）。

## 安全

- Access token 在所有日志和 CLI 输出里都会脱敏，详见
  [`SECURITY.md`](SECURITY.md)。
- 用户文本和转写内容**默认不记录**。排查协议问题时才开
  `DOUBAO_SPEECH_TRACE_PAYLOADS=1`。
- `~/.doubao-speech/config.yaml` 是用户级配置；项目 `.gitignore`
  已经排除了 `.env` 文件。
- 安全漏洞请发邮件 `hypnus.yuan@gmail.com`，或在 GitHub 开 private
  security advisory。

## 本地开发

```bash
git clone https://github.com/Hypnus-Yuan/doubao-speech.git
cd doubao-speech

uv sync --all-extras --group dev
uv run pre-commit install
uv run pytest
```

完整流程见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 路线图

- **v0.2** —— 连接复用 daemon（TCP+TLS amortization）、流式回调 API
  暴露 partial transcript、更丰富的音色元信息。
- **v0.3** —— LangChain / LlamaIndex / Dify 集成范例。
- **v1.0** —— API 冻结，正式语义化版本承诺。

## 许可证

MIT —— 详见 [`LICENSE`](LICENSE)。

## 致谢

协议解析代码提炼并加固自 [Hermes Agent](https://github.com/NousResearch/hermes-agent)
社区工作。感谢火山引擎 Speech 团队提供 seed-tts-2.0 双向流式 API
和 bigmodel ASR 端点。
