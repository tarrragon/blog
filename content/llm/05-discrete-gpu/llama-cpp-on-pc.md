---
title: "5.3 llama.cpp 在 PC 上"
date: 2026-05-12
description: "CUDA / ROCm build 取得、核心旗標地圖、llama-bench 校準、多卡 tensor split 的入門設定"
tags: ["llm", "discrete-gpu", "llama-cpp", "cuda", "rocm"]
weight: 4
---

llama.cpp 是 PC 場景跑本地 LLM 的主流 [推論伺服器](/llm/knowledge-cards/inference-server/)、也是 Ollama、LM Studio 的底層 backend。在 PC 上直接使用 llama.cpp 的場景跟 Mac 不同：PC 需要選對 [GPU compute backend](/llm/knowledge-cards/gpu-compute-backend/)（CUDA / ROCm / Vulkan）、處理 driver 版本對齊、調 [MoE 卸載](/llm/knowledge-cards/moe-cpu-offload/) 與 KV cache 量化旗標、產出的是 [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/)。本章把這些 PC 場景特有的設定串成一條完整的調參工作流。

讀完本章後、你應該能在自己的 PC 上：選對 llama.cpp build、用 `llama-server` 跑 OpenAI 相容 API、用 `llama-bench` 校準 throughput、知道多卡跟非 NVIDIA GPU 的入門設定方向。

## 本章目標

1. 知道怎麼取得對應自己 GPU 的 llama.cpp build（pre-built release vs 自編譯）。
2. 看懂 PC 場景常用旗標的分組與互相關係。
3. 用 `llama-server` 啟動 OpenAI 相容 server、接到 VS Code Continue.dev。
4. 用 `llama-bench` 校準 prefill 跟 generation throughput。
5. 認識多卡 tensor split 的入門設定。
6. 知道 ROCm（AMD）跟 Vulkan backend 的相對成熟度。

## 取得 llama.cpp build

llama.cpp 在 PC 上的取得方式有三條：

### 路徑一：官方 pre-built release（社群常見起點）

`ggml-org/llama.cpp` 的 GitHub release 提供 Windows / Linux 的 pre-built binary、含 CUDA 12.x、ROCm、Vulkan、CPU-only 等多種 backend。下載對應自己 GPU + driver 版本的 build、解壓即用。模型權重檔通常為 [GGUF](/llm/knowledge-cards/gguf/) 格式。

選 build 時的判讀：

| GPU 廠商                   | 建議 backend                                 | 備註                                                                 |
| -------------------------- | -------------------------------------------- | -------------------------------------------------------------------- |
| NVIDIA（RTX 系列）         | CUDA 12.x build                              | 最成熟、社群回報最多、需對應 NVIDIA driver 版本                      |
| AMD（RX 系列、Radeon Pro） | ROCm build（Linux）/ Vulkan build（Windows） | ROCm Windows 支援仍在演進、Vulkan 跨平台但 throughput 通常較 CUDA 低 |
| Intel（ARC）               | Vulkan build / SYCL build                    | 工具鏈相對年輕、社群實測案例較少                                     |
| Apple Silicon              | Metal build（屬模組一範圍）                  | 見 [1.2 Mac 版 llama.cpp](/llm/01-local-llm-services/llama-cpp/)     |

> **事實查核註**：各 backend 的成熟度跟支援度依 llama.cpp 版本快速演進、上表為 2026 年 5 月常見回報的相對情況、建議引用時以 [llama.cpp release notes](https://github.com/ggml-org/llama.cpp/releases) 跟對應 backend 的官方文件為準。

### 路徑二：自編譯（需要特定功能或最新 commit）

從原始碼編譯適合下面情境：

1. 想用 release 還沒包進去的新功能（如剛 merge 的 PR）。
2. 想針對特定 CUDA compute capability 編譯、減少 binary 大小或開特定優化。
3. 自己 patch 過 llama.cpp。

CUDA build 的常見編譯指令（以 Linux 為例、Windows 請參考官方文件）：

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j
```

編譯選項依版本變化、以 `CMakeLists.txt` 跟 [build 文件](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) 為準。

### 路徑三：透過上層工具（Ollama / LM Studio）

如果你不需要直接面對 llama.cpp 旗標、用 Ollama 或 LM Studio 通常更省事。它們把 llama.cpp 包裝在背後、提供更高層的設定介面。Mac / Windows 都適用、見 [5.4 LM Studio 在 Windows](/llm/05-discrete-gpu/lm-studio-on-windows/)。

直接面對 llama.cpp 的價值：完整控制旗標、看 log 直接 debug、用 `llama-bench` 做精確校準。

## 核心旗標地圖

PC 場景常用的旗標可以分成五組：

### 1. GPU 層分配

| 旗標                  | 作用                                                                                                 |
| --------------------- | ---------------------------------------------------------------------------------------------------- |
| `-ngl <N>`            | 把 N 層 transformer block 放 GPU。常設 99 或 max 表示能放盡量放                                      |
| `--n-cpu-moe <N>`     | MoE 模型：把 N 層的專家權重保留 CPU 記憶體、見 [5.1](/llm/05-discrete-gpu/moe-cpu-offload-strategy/) |
| `--split-mode <mode>` | 多卡模式（`none` / `layer` / `row`）                                                                 |
| `-ts <floats>`        | tensor split、多卡時各卡的權重比例                                                                   |
| `-mg <N>`             | 主卡 index、特定計算（如 KV cache）放在主卡                                                          |

### 2. KV cache 與 context

| 旗標                    | 作用                                                                                                 |
| ----------------------- | ---------------------------------------------------------------------------------------------------- |
| `-c <N>`                | context window 大小                                                                                  |
| `--cache-type-k <type>` | K cache 量化（f16 / q8_0 / q4_0 等）、見 [5.2](/llm/05-discrete-gpu/kv-cache-quantization-strategy/) |
| `--cache-type-v <type>` | V cache 量化                                                                                         |
| `-fa` / `--flash-attn`  | 啟用 flash attention、部分量化組合需要                                                               |

### 3. 平行與 batch

| 旗標             | 作用                                           |
| ---------------- | ---------------------------------------------- |
| `--parallel <N>` | 同時處理的 sequence 數、高併發場景使用         |
| `-b <N>`         | logical batch size                             |
| `-ub <N>`        | micro-batch size、影響 prefill 速度            |
| `-np <N>`        | num parallel slots（部分版本旗標、依版本變動） |

### 4. 模型與量化

| 旗標             | 作用                                        |
| ---------------- | ------------------------------------------- |
| `-m <path>`      | GGUF 模型路徑                               |
| `--alias <name>` | 對外宣告的 model name（OpenAI 相容 API 用） |
| `--lora <path>`  | LoRA adapter 路徑                           |

### 5. server 設定

| 旗標            | 作用                      |
| --------------- | ------------------------- |
| `--host <addr>` | bind 位址、預設 127.0.0.1 |
| `--port <N>`    | port、預設 8080           |
| `--api-key <k>` | API key 驗證              |
| `-v`            | verbose log               |

完整旗標清單見 `llama-server --help` 跟 [tools/server/README.md](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)；版本更新後旗標可能新增、改名或棄用、以實際版本為準。

## 完整啟動範例

下面三個範例對應三種常見硬體配置、皆為起點配置、需依實測調整。

### 範例一：16GB VRAM + 64GB RAM、跑 30B MoE 寫 code

```bash
./llama-server \
  -m ~/models/Qwen3-30B-A3B-Q4_K_M.gguf \
  --alias qwen3-30b-a3b \
  -ngl 99 \
  --n-cpu-moe 30 \
  --cache-type-k q8_0 \
  --cache-type-v q4_0 \
  -fa \
  -c 32768 \
  --parallel 1 \
  --host 127.0.0.1 \
  --port 8080
```

對應的 Continue.dev 設定：

```json
{
  "models": [
    {
      "title": "Local llama.cpp",
      "provider": "openai",
      "model": "qwen3-30b-a3b",
      "apiBase": "http://localhost:8080/v1",
      "apiKey": "not-needed"
    }
  ]
}
```

### 範例二：24GB VRAM + 64GB RAM、跑 32B Dense

```bash
./llama-server \
  -m ~/models/Qwen3-32B-Q4_K_M.gguf \
  -ngl 99 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  -fa \
  -c 65536 \
  --parallel 1 \
  --port 8080
```

Dense 32B Q4_K_M 體積落在 16 ~ 20 GB 級、24GB VRAM 可全載；KV cache 保留較保守的 Q8 / Q8、context 開到 64K。

### 範例三：8GB VRAM + 32GB RAM、跑 7B 級 Dense

```bash
./llama-server \
  -m ~/models/Qwen3-7B-Q4_K_M.gguf \
  -ngl 99 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  -fa \
  -c 16384 \
  --port 8080
```

7B Q4_K_M 體積約 4 ~ 5 GB、8GB VRAM 可全載 + 適中 KV cache。

## 用 llama-bench 校準

`llama-bench` 是 llama.cpp 附帶的 benchmark 工具、用來測量特定模型 + 旗標組合的 prefill 跟 generation throughput。

基本用法：

```bash
./llama-bench \
  -m ~/models/Qwen3-30B-A3B-Q4_K_M.gguf \
  -ngl 99 \
  --n-cpu-moe 30 \
  --cache-type-k q8_0 \
  --cache-type-v q4_0 \
  -p 512 \
  -n 128
```

`-p`：prefill 測試的 prompt 長度；`-n`：generation 測試的 token 數。

輸出會列出 prefill t/s 跟 generation t/s。建議：

1. **記錄基準**：用「平衡起點」旗標跑一次、記下 prefill 跟 generation t/s。
2. **逐項調整**：每次只動一個旗標（如 `--n-cpu-moe` 從 30 改 25、再改 35）、看 t/s 怎麼變。
3. **校準目標**：找到「VRAM 用量、context 上限、t/s」三者組合符合工作流需求的設定。

llama-bench 的結果是「fixed prompt / 固定生成長度」、跟「實際工作流的混合長度」有差距；建議再用實際工作流的代表性任務做最終驗證。

> **事實查核註**：`llama-bench` 的輸出格式跟旗標名稱依 llama.cpp 版本變動、以實際 `llama-bench --help` 為準。

## 多卡 tensor split 入門

如果你有兩張或以上的 GPU、llama.cpp 支援把模型權重分散到多卡：

```bash
./llama-server \
  -m ~/models/Llama-4-Scout.gguf \
  -ngl 99 \
  --split-mode layer \
  -ts 0.5,0.5 \
  --port 8080
```

- `--split-mode layer`：以層為單位切分、最常用
- `--split-mode row`：以張量的 row 切分、用於 tensor parallel
- `-ts 0.5,0.5`：兩張卡各分一半權重；若兩卡 VRAM 不同、可調比例（如 `-ts 0.4,0.6`）

多卡的實際吞吐縮放比依下面因素變化：

1. **主機板 PCIe lane 配置**：消費級主機板常見「一條 x16 + 一條 x4」、第二張卡的 PCIe 頻寬可能受限。
2. **GPU 之間是否有 [NVLink](/llm/knowledge-cards/nvlink/)**：消費級 RTX 系列普遍不支援 NVLink、卡間通訊走 [PCIe](/llm/knowledge-cards/pcie/)、相對資料中心級配置慢。
3. **split-mode 選擇**：`row` 模式需要更高的卡間頻寬、`layer` 模式對 PCIe 頻寬要求較低。

社群常見回報：多卡縮放比通常低於線性、`layer` 模式對長 prompt 的 prefill 提升較明顯、generation 提升相對小。具體效益依工作流跟卡間頻寬、需用 `llama-bench` 校準。

對單人寫 code 場景、多卡的邊際效益通常不如「先升級單卡」或「先優化單卡配置」。

## ROCm 與 Vulkan backend 的相對成熟度

llama.cpp 對非 CUDA backend 的支援度依社群回報有以下相對位置：

| Backend | 平台支援              | 社群成熟度                              | 常見適用情境                                         |
| ------- | --------------------- | --------------------------------------- | ---------------------------------------------------- |
| CUDA    | NVIDIA、Windows/Linux | 最成熟、PR 與文件最多                   | 預設選項                                             |
| ROCm    | AMD、Linux 為主       | 演進中、Windows 支援較新                | AMD GPU on Linux                                     |
| Vulkan  | 跨廠商                | 通用但 throughput 通常較 CUDA / ROCm 低 | AMD on Windows、Intel ARC、跨平台 fallback           |
| SYCL    | Intel                 | 新興、社群實測案例較少                  | Intel ARC                                            |
| Metal   | Apple Silicon         | 成熟（屬模組一範圍）                    | Mac、見 [1.2](/llm/01-local-llm-services/llama-cpp/) |

> **事實查核註**：各 backend 的成熟度跟性能對比是社群常見回報、不是經本文系統實測。建議引用前查閱 [llama.cpp 的 PR 列表](https://github.com/ggml-org/llama.cpp/pulls)、對應 backend 的官方文件、跟自己硬體的實際 benchmark。

選 backend 的判讀：

1. **NVIDIA GPU**：用 CUDA build、不需考慮其他。
2. **AMD GPU on Linux**：優先試 ROCm build；不穩或不支援的卡型則退回 Vulkan。
3. **AMD GPU on Windows**：ROCm on Windows 在演進、Vulkan 通常較穩。具體選擇以 llama.cpp release notes 跟自己硬體實測為準。
4. **Intel ARC**：Vulkan 或 SYCL backend；社群實測案例較少、預期需要較多自己摸索。

## 跟 Ollama / LM Studio 並存

llama.cpp `server`、Ollama、LM Studio 可以同時跑、用不同 port：

| 推論伺服器   | 預設 port |
| ------------ | --------- |
| Ollama       | 11434     |
| llama-server | 8080      |
| LM Studio    | 1234      |

Continue.dev 可以同時接：

```json
{
  "models": [
    {
      "title": "Ollama default",
      "provider": "ollama",
      "model": "qwen3-30b-a3b",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "llama.cpp custom",
      "provider": "openai",
      "model": "qwen3-30b-a3b",
      "apiBase": "http://localhost:8080/v1",
      "apiKey": "not-needed"
    }
  ]
}
```

實務上、多數情況只需要一個推論伺服器；同時跑多個的場景是「比較同一模型在不同 backend / 旗標下的差異」、屬於調參階段、不是常態。

## 小結

llama.cpp 在 PC 上的核心差異是「選對 GPU backend」「設對 MoE 卸載 + KV cache 量化的搭配」「用 `llama-bench` 校準 throughput」。CUDA build 是 NVIDIA GPU 的預設選項、ROCm / Vulkan 對非 NVIDIA GPU 的支援度依版本演進、多卡 tensor split 對單人寫 code 場景邊際效益通常較小。完整旗標表 + 啟動範例可作為起點、實際數值需依自己硬體、模型版本、工作流校準。

下一章：[5.4 LM Studio 在 Windows](/llm/05-discrete-gpu/lm-studio-on-windows/)、給「不想直接面對 CLI」的讀者另一條路。
