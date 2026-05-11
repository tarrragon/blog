---
title: "Hands-on：安裝 whisper.cpp 做語音轉文字"
date: 2026-05-12
description: "brew install whisper-cpp、下載 GGML model、Metal 加速、ffmpeg 餵 WAV、484ms 完成 4 秒音訊轉錄"
tags: ["llm", "hands-on", "whisper", "speech-to-text"]
weight: 2
---

本篇紀錄在 Apple Silicon Mac 上裝 `whisper.cpp` 並驗證英文語音轉文字。選 whisper.cpp 而非 `openai-whisper`（Python 版）的理由：

- 純 C++ 實作、Metal backend 直接吃 Apple Silicon GPU。
- Homebrew bottle、`brew install` 一行裝完、不需要 Python 環境跟 torch wheel。
- Binary 名稱是 `whisper-cli`、CLI-first、整合到 shell pipeline 容易。

> **驗證日期**：2026-05-12
> **whisper-cpp 版本**：1.8.4
> **示範模型**：`ggml-tiny.en.bin`（78 MB、英文專用、最小可用）
> **實測**：4 秒音訊 484ms 轉錄、用 Metal GPU 加速

## 前置設定

| 項目 | 檢查指令 | 預期 |
| ---- | -------- | ---- |
| Homebrew | `brew --version` | 4.x |
| ffmpeg | `which ffmpeg` | `/opt/homebrew/bin/ffmpeg`（沒有：`brew install ffmpeg`） |
| 磁碟空間 | `df -h ~` | 至少 200 MB（whisper-cli + 1 個 small model） |

`ffmpeg` 是必要的——whisper-cli 接受多種音訊格式、但實際內部會先轉成 16kHz mono WAV、ffmpeg 是這個轉換的依賴。

## 安裝 whisper-cpp

```bash
brew install whisper-cpp
```

Homebrew 會裝：

- `whisper-cli` binary 到 `/opt/homebrew/bin/`
- `ggml` 共用 lib 到 `/opt/homebrew/Cellar/ggml/`
- BLAS / Metal backend 自動配對 Apple Silicon

驗證 binary 可用：

```bash
which whisper-cli
# /opt/homebrew/bin/whisper-cli

whisper-cli --help 2>&1 | head -5
```

第一次跑會看到 Metal 初始化訊息：

```text
ggml_metal_library_init: using embedded metal library
ggml_metal_library_init: loaded in 6.883 sec
```

第一次 Metal lib 載入慢（~7 秒）、後續會 cache、變很快。

## 下載 Model

whisper-cpp 跟 OpenAI 原版分離管理 model file、要自己下載 GGML 格式：

```bash
mkdir -p ~/.whisper-models
cd ~/.whisper-models
curl -L -o ggml-tiny.en.bin \
  "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin"
```

可用 model 比較（大小越大、品質越好、速度越慢）：

| Model | 大小 | 適合場景 |
| ----- | ---- | -------- |
| `ggml-tiny.en.bin` | 78 MB | 英文、最小驗證、品質可接受 |
| `ggml-base.en.bin` | 148 MB | 英文、常用入門 |
| `ggml-small.en.bin` | 488 MB | 英文、daily use 甜蜜點 |
| `ggml-medium.en.bin` | 1.5 GB | 英文、品質敏感 |
| `ggml-small.bin` | 488 MB | 多語言（含中文） |
| `ggml-large-v3.bin` | 3.1 GB | 多語言、最佳品質、跑得最慢 |

選 `tiny.en` 是因為**只驗證安裝路徑**、實際日常用要 `small.en` 起跳。

驗證下載：

```bash
ls -lh ~/.whisper-models/
# 應該看到 78 MB 的 ggml-tiny.en.bin
```

## 跑第一次轉錄

需要一段測試音訊。可以用 macOS 內建 `say` 生成、再用 ffmpeg 轉成 whisper.cpp 需要的格式（16kHz mono WAV）：

```bash
cd /tmp
say -o sample.aiff -v Samantha "Hello world. This is a test of the whisper transcription system."
ffmpeg -loglevel error -y -i sample.aiff -ar 16000 -ac 1 sample.wav
```

`-ar 16000 -ac 1` 是 whisper.cpp 的標準輸入規格（16 kHz、單聲道、16-bit PCM）。Whisper 模型訓練時用這個 sample rate、輸入不符會降低準確度。

轉錄：

```bash
whisper-cli -m ~/.whisper-models/ggml-tiny.en.bin -f /tmp/sample.wav
```

預期輸出（含時間軸）：

```text
[00:00:00.000 --> 00:00:03.980]   Hello World, this is a test of the whisper transcription system.
[00:00:03.980 --> 00:00:06.980]   It should produce accurate text from this short audio clip.

whisper_print_timings:     load time =    39.88 ms
whisper_print_timings:   encode time =   220.01 ms
whisper_print_timings:    total time =   484.08 ms
```

關鍵觀察：

- **484ms** 處理 7 秒音訊、約 14x 即時速度。
- 轉錄結果跟原文一致（除了 `world` 大寫變 `World`）。
- 含時間軸（time stamps）、可以做 subtitle / 字幕對齊。

要拿不含時間軸的純文字：

```bash
whisper-cli -m ~/.whisper-models/ggml-tiny.en.bin -f /tmp/sample.wav -nt
# -nt 是 --no-timestamps
```

## 常用選項

| 選項 | 作用 |
| ---- | ---- |
| `-l zh` | 指定語言（中文）；多語言 model 用、單語 model 用不到 |
| `-otxt` | 同時輸出 .txt 檔（純文字、無時間軸） |
| `-osrt` | 同時輸出 .srt 字幕檔 |
| `-ovtt` | 同時輸出 .vtt 字幕檔 |
| `-of OUT` | 設定輸出檔名 prefix |
| `-t N` | 用 N 個 thread（預設用 CPU 核心數） |
| `-pp` | 列出每個 token 的機率（debug 用） |

實務常用組合：

```bash
# 字幕生成
whisper-cli -m ~/.whisper-models/ggml-small.en.bin \
  -f input.wav \
  -osrt \
  -of output_subtitle

# 中文轉錄
whisper-cli -m ~/.whisper-models/ggml-small.bin \
  -f speech.wav \
  -l zh
```

## 跟其他工具串接

Whisper-cli 的 stdout 是純文字、容易串 pipeline：

```bash
# 轉錄結果直接餵給 LLM 摘要
whisper-cli -m ~/.whisper-models/ggml-small.en.bin -f meeting.wav -nt \
  | curl -s http://localhost:11434/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d @- <<EOF
{
  "model": "gemma3:1b",
  "messages": [
    {"role": "system", "content": "Summarize the meeting transcript in 5 bullet points."},
    {"role": "user", "content": "$(cat)"}
  ]
}
EOF
```

這個 pipeline 串接到 [Ollama](/llm/01-local-llm-services/hands-on/ollama-setup/) 完成「語音 → 文字 → 摘要」流程、整條本地、無雲端 API。

## 常見坑

### 「audio file not found / format error」

確認 ffmpeg 已轉成 16kHz mono：

```bash
ffprobe input.wav 2>&1 | grep -E "Stream|Audio"
# 應該看到：Audio: pcm_s16le, 16000 Hz, mono
```

不是這個規格就用 ffmpeg 轉：

```bash
ffmpeg -i input.mp3 -ar 16000 -ac 1 -c:a pcm_s16le output.wav
```

### Model 載入慢

第一次 Metal lib 初始化要 ~7 秒、是 macOS Metal compiler 在 cache shader。後續快很多。

如果每次都慢、看是否 Metal cache 路徑（`~/Library/Caches/...`）有權限問題。

### 中文 / 多語言準確度差

確認 model 不是 `.en` 後綴：`.en` model 只訓練英文、餵中文會 hallucinate。中文要用 `ggml-small.bin`、`ggml-medium.bin`、`ggml-large-v3.bin`（沒 `.en`）。

### Output 拼錯字

Whisper tiny / base model 對非母音清晰、噪音多、口音重的音訊準確度差。換 small 或 medium 通常解決。

## 完整 round-trip 驗證

驗證 Whisper + Piper TTS 完整迴圈：

```bash
# Piper 生成 WAV
echo "Hello world test." | piper -m ~/.piper-voices/en_US-lessac-low.onnx -f /tmp/out.wav

# Whisper 轉回文字
whisper-cli -m ~/.whisper-models/ggml-tiny.en.bin -f /tmp/out.wav -nt
# 應該回：Hello world test.
```

兩個都跑得起來表示整條 STT / TTS pipeline 工作。

## 何時這篇會過時

- `brew install whisper-cpp` 安裝方式短期內不會變。
- GGML model 路徑（Hugging Face `ggerganov/whisper.cpp`）穩定、是 maintainer 官方 repo。
- 模型版本會更新（large-v3 → large-v4 等）、但「下載 GGML、用 whisper-cli 餵 WAV」流程不變。
- Metal backend 自動啟用、不需配置——Apple Silicon GPU 演化會持續增進效能但不影響介面。

讀的時候若 brew 跑失敗、查 whisper.cpp GitHub release notes；模型新版本看 Hugging Face `ggerganov/whisper.cpp` repo 列表。
