---
title: "Hands-on：安裝 Piper TTS 做文字轉語音"
date: 2026-05-12
description: "pip install piper-tts、ONNX voice model、stdin 餵文字、WAV 輸出、跟 Whisper 互為 round-trip 驗證"
tags: ["llm", "hands-on", "tts", "piper"]
weight: 3
---

本篇紀錄裝 Piper TTS 並用它合成英文語音、再用 Whisper 轉回文字做 round-trip 驗證。選 Piper 而非雲端 TTS（OpenAI / ElevenLabs）的理由：

- 完全本地、隱私邊界乾淨。
- ONNX runtime、Apple Silicon 跑得動、不依賴 GPU。
- 模型小（low quality ~17-65 MB、medium ~50 MB、high ~125 MB）、適合 minimal 驗證。
- CLI-first、stdin 餵文字、stdout 或檔案輸出 WAV、容易串 pipeline。

> **驗證日期**：2026-05-12
> **Piper 版本**：透過 pip 安裝
> **示範 voice**：`en_US-lessac-low.onnx`（63 MB、英文女聲、low quality）
> **實測**：4 秒文字合成 < 1 秒、品質夠日常用

## 前置設定

| 項目     | 檢查指令            | 預期                              |
| -------- | ------------------- | --------------------------------- |
| Python   | `python3 --version` | 3.11+                             |
| pip      | `pip3 --version`    | 25+                               |
| 磁碟空間 | `df -h ~`           | 至少 200 MB（Piper + 一個 voice） |

Piper 跟 Whisper 一樣分離 binary 跟 model：先裝 runtime、再下載 voice。

## 安裝 Piper

`piper-tts` 沒有 Homebrew formula、用 pip 裝：

```bash
pip3 install piper-tts --break-system-packages
```

`--break-system-packages` 是 macOS 系統 Python 的安全機制——bypass `PEP 668` external-management warning。比較乾淨的做法是用 venv：

```bash
python3 -m venv ~/.piper-venv
source ~/.piper-venv/bin/activate
pip install piper-tts
```

但裝完 PATH 要指到 venv 的 piper、稍麻煩。本 demo 用 `--break-system-packages` 簡化。實際生產建議用 venv 或 pipx。

驗證 binary 在 PATH：

```bash
which piper
# /opt/homebrew/bin/piper

piper --help | head -10
```

## 下載 Voice Model

Piper 用 ONNX 格式的 voice model、每個 voice 是一對 `.onnx`（model 權重）+ `.onnx.json`（metadata、含採樣率、phoneme map）。

從 Hugging Face `rhasspy/piper-voices` repo 拉：

```bash
mkdir -p ~/.piper-voices
cd ~/.piper-voices

# 英文女聲、low quality（小、快）
curl -L -o en_US-lessac-low.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/low/en_US-lessac-low.onnx"
curl -L -o en_US-lessac-low.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/low/en_US-lessac-low.onnx.json"
```

可用 voice quality 等級：

| Quality  | 大小       | 用途                           |
| -------- | ---------- | ------------------------------ |
| `low`    | 17-65 MB   | 快、品質粗糙、適合 prototype   |
| `medium` | 50-100 MB  | 平衡、日常用                   |
| `high`   | 100-200 MB | 品質佳、合成略慢               |
| `x_low`  | < 20 MB    | 極小、品質明顯差、適合受限環境 |

語言 / 地區覆蓋（部分）：

| Locale                         | Voice 範例                  |
| ------------------------------ | --------------------------- |
| `en_US`                        | lessac、ryan、amy、libritts |
| `en_GB`                        | alan、cori、jenny           |
| `zh_CN`                        | huayan（北京話）            |
| `ja_JP`（社群）                | 較少                        |
| `de_DE` / `fr_FR` / `es_ES` 等 | 各有多個                    |

完整清單在 `rhasspy/piper-voices` 的 [VOICES.md](https://github.com/rhasspy/piper)。

驗證下載：

```bash
ls -lh ~/.piper-voices/
# en_US-lessac-low.onnx       63M
# en_US-lessac-low.onnx.json  4.9K
```

## 跑第一次合成

```bash
echo "Hello from Piper TTS, this is a synthesized voice test." \
  | piper -m ~/.piper-voices/en_US-lessac-low.onnx -f /tmp/piper-out.wav
```

說明：

- 文字從 stdin 進、是 Piper 的標準輸入方式。
- `-m`：voice model `.onnx` path。Piper 自動找同目錄的 `.onnx.json`。
- `-f`：output WAV path。不指定的話直接寫 stdout（可以 pipe 到 `aplay` / `afplay` 即時播放）。

預期輸出：

```bash
ls -lh /tmp/piper-out.wav
# 128 KB
```

驗證 WAV 規格：

```bash
file /tmp/piper-out.wav
# RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, mono 16000 Hz

ffprobe -loglevel error -show_format /tmp/piper-out.wav | grep duration
# duration=3.984000
```

16-bit PCM、16 kHz mono——跟 [Whisper](/llm/01-local-llm-services/hands-on/whisper-setup/) 期望的輸入規格一致、可以直接 round-trip。

播放確認：

```bash
afplay /tmp/piper-out.wav
```

## 常用選項

| 選項                    | 作用                                              |
| ----------------------- | ------------------------------------------------- |
| `-m MODEL`              | voice model `.onnx` 路徑（必填）                  |
| `-c CONFIG`             | metadata json 路徑（預設自動找同名 `.onnx.json`） |
| `-i FILE`               | 輸入文字檔（替代 stdin）                          |
| `-f OUTPUT`             | 輸出 WAV 路徑                                     |
| `-d DIR`                | 輸出目錄（多句時自動分檔）                        |
| `--length-scale FACTOR` | 速度調整（< 1 加速、> 1 減速、預設 1.0）          |
| `--volume FACTOR`       | 音量調整（0.0-1.0）                               |
| `-s SPEAKER`            | 多 speaker model 選 speaker（如 libritts）        |
| `--cuda`                | 用 CUDA（Apple Silicon 用不到、留 default）       |

典型應用：

```bash
# 從文字檔合成
piper -m ~/.piper-voices/en_US-lessac-low.onnx \
  -i article.txt \
  -f narration.wav

# 多句子分檔
piper -m ~/.piper-voices/en_US-lessac-medium.onnx \
  -i script.txt \
  -d ~/audio-output/ \
  --output-dir-naming text

# 慢速朗讀（學習用）
piper -m ~/.piper-voices/en_US-lessac-low.onnx \
  --length-scale 1.4 \
  -f slow.wav <<< "Slowly read this sentence."
```

## Round-Trip 驗證

確認 TTS + STT 整條串得起來：

```bash
# 1. Piper TTS：文字 → WAV
echo "The quick brown fox jumps over the lazy dog." \
  | piper -m ~/.piper-voices/en_US-lessac-low.onnx -f /tmp/test.wav

# 2. Whisper STT：WAV → 文字
whisper-cli -m ~/.whisper-models/ggml-tiny.en.bin -f /tmp/test.wav -nt
```

預期 Whisper 回應接近原文字（可能大小寫 / 標點稍變）。Round-trip 成功表示：

- Piper 輸出格式（16kHz mono WAV）符合 Whisper 輸入需求。
- 兩個模型對英文的訓練分佈相容。

## 跟 LLM 串接：「LLM 說話」的 minimal pipeline

```bash
# 1. LLM 生成回答
ANSWER=$(curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma3:1b",
    "messages": [{"role":"user","content":"Tell me a one-sentence joke."}],
    "stream": false
  }' | python3 -c "import json,sys; print(json.load(sys.stdin)['choices'][0]['message']['content'])")

# 2. Piper 把回答念出來
echo "$ANSWER" | piper -m ~/.piper-voices/en_US-lessac-low.onnx -f /tmp/llm-says.wav

# 3. 播放
afplay /tmp/llm-says.wav
```

三行 shell 完成「Local LLM 講笑話」整條 pipeline、無雲端、無 GPU。

## 常見坑

### 中文 / 多語言

`en_US-lessac-low` 是英文 voice、餵中文會發音怪。中文要下載 `zh_CN-huayan-*`：

```bash
curl -L -o ~/.piper-voices/zh_CN-huayan-medium.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx"
curl -L -o ~/.piper-voices/zh_CN-huayan-medium.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json"

echo "你好，這是 Piper TTS 的中文測試。" \
  | piper -m ~/.piper-voices/zh_CN-huayan-medium.onnx -f /tmp/zh-out.wav
```

zh_CN 預設是北京話腔調。

### `--break-system-packages` 警告

macOS 系統 Python 3.13+ 預設禁止 pip 直接裝。安全做法用 venv 或 pipx；不想搞 venv 就用 `--break-system-packages` flag（會跳警告但能裝）。長期建議遷到 venv、避免污染系統 Python。

### Voice quality 不夠

`low` quality 的 voice 適合驗證 / prototype、實際用 `medium` 或 `high`。低品質 voice 在長段文字會聽起來機械、自然度差。

### Sample rate mismatch

Voice metadata（`.onnx.json` 內 `sample_rate`）決定輸出 sample rate、不同 voice 可能不同（多數 22050 或 16000）。Whisper 期望 16000、若 Piper 輸出 22050、可能需要 ffmpeg 降採樣：

```bash
ffmpeg -i piper-out.wav -ar 16000 piper-out-16k.wav
```

`en_US-lessac-low` 本來就是 16k、沒這問題。

## 何時這篇會過時

- `pip install piper-tts` 安裝方式可能演化（轉純 binary release？）、但 ONNX model + CLI invocation 形式應該穩定。
- Voice model 格式（ONNX）是 web 通用標準、未來增加 quality / locale、現有 voice 不會被 deprecate。
- Hugging Face `rhasspy/piper-voices` repo 是 maintainer 官方、不會消失。

讀的時候若 pip install 失敗、查 [piper GitHub](https://github.com/rhasspy/piper) 最新 install 路徑；voice 列表看 piper-voices repo。
