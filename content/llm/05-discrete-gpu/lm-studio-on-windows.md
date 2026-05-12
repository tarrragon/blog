---
title: "5.4 LM Studio 在 Windows"
date: 2026-05-12
description: "Windows + 獨立 GPU 場景用 LM Studio：CUDA / ROCm backend 選擇、GUI 內對應 -ngl / cache-type / cpu-moe 的設定位置"
tags: ["llm", "discrete-gpu", "lm-studio", "windows", "gui"]
weight: 5
---

LM Studio 在 PC 場景的價值是「不打開終端機也能調 [MoE 卸載](/llm/knowledge-cards/moe-cpu-offload/) 與 KV cache 量化」。本章不重複 [Mac 版 LM Studio](/llm/01-local-llm-services/lm-studio/) 的基本定位、改聚焦 Windows + 獨立 GPU 場景的特有設定：CUDA / ROCm backend 選擇、GUI 內對應 [5.1 MoE 卸載](/llm/05-discrete-gpu/moe-cpu-offload-strategy/) / [5.2 KV cache 量化](/llm/05-discrete-gpu/kv-cache-quantization-strategy/) 旗標的位置。LM Studio 跟 Ollama、llama-server 一樣屬於 [推論伺服器](/llm/knowledge-cards/inference-server/) 層、對外提供 [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/)。

讀完本章後、你應該能在 Windows 上：選對 LM Studio 的 GPU backend、在 GUI 內設定卸載層數與 KV cache 量化、啟動 OpenAI 相容 server、接到 VS Code Continue.dev。

## 本章目標

1. 在 Windows 上安裝 LM Studio、選對 GPU backend。
2. 知道 GUI 設定面板的哪幾個欄位對應 llama.cpp 的核心旗標。
3. 啟動 LM Studio 的本地 server、提供 OpenAI 相容 API。
4. 判斷你的工作流適不適合用 LM Studio 當主力。
5. 處理常見的 Windows + GPU 整合議題（driver 版本、CUDA toolkit）。

## 安裝

LM Studio 是 Electron 桌面 app、個人使用免費、Windows / Linux / macOS 三平台都支援。從 [lmstudio.ai 官網](https://lmstudio.ai) 下載對應系統的安裝檔即可。

Windows 版的安裝步驟：

1. 下載 `.exe` 安裝程式、執行安裝（不需 admin 權限的情況下會裝在使用者目錄）。
2. 首次啟動時、LM Studio 會偵測 GPU 並提示選擇 backend。

> **事實查核註**：LM Studio 是商業軟體、UI 跟功能會隨版本變化。本章描述以 2026 年 5 月的穩定版為基準、實際 UI 元素位置以當前版本為準。

## GPU backend 選擇

LM Studio 在 Windows 上的 [GPU compute backend](/llm/knowledge-cards/gpu-compute-backend/) 選項依 GPU 廠商不同：

| GPU 廠商            | 可選 backend                       | 建議起點                                          |
| ------------------- | ---------------------------------- | ------------------------------------------------- |
| NVIDIA RTX 系列     | CUDA、Vulkan                       | CUDA（成熟度高、社群實測案例多）                  |
| AMD Radeon 系列     | ROCm（部分卡型）、Vulkan、DirectML | 視 GPU 型號與 driver 版本、社群常見從 Vulkan 起步 |
| Intel ARC           | Vulkan、OpenVINO（部分版本）       | Vulkan 較通用                                     |
| 整合顯卡 / CPU only | CPU backend                        | 模型較小、適合試水溫                              |

backend 的切換位置：LM Studio 的設定面板（齒輪圖示）→ Hardware / Runtime 區段、會列出當前可用的 backend 與下載連結。部分 backend 在首次使用時需要下載對應的 runtime（如 CUDA runtime）。

選錯 backend 的常見徵兆：

1. **模型載入時間異常長**：可能 fallback 到 CPU、確認 GPU backend 是否正確啟用。
2. **生字速度遠低於同硬體的社群回報**：backend 不對、或 driver 版本不對、或 VRAM 不足而啟用了 CPU offload。
3. **載入時錯誤訊息提到 CUDA 版本不符**：driver 跟 LM Studio 內建的 CUDA runtime 不對齊、需更新 driver 或選擇對應的 LM Studio build。

> **事實查核註**：各 backend 的可用性跟下載方式依 LM Studio 版本變動、以當前版本的 Hardware / Runtime 設定面板顯示為準。

## GUI 設定對應到 llama.cpp 旗標

LM Studio 在背後使用 llama.cpp、GUI 內的設定欄位通常對應到 llama.cpp 的某個旗標。對熟悉 [5.3 llama.cpp 在 PC 上](/llm/05-discrete-gpu/llama-cpp-on-pc/) 旗標的讀者、這個對應表能加速 GUI 內的設定：

| LM Studio GUI 欄位（位置依版本變化） | 對應 llama.cpp 旗標     | 作用                   |
| ------------------------------------ | ----------------------- | ---------------------- |
| GPU Offload / GPU Layers             | `-ngl <N>`              | 把 N 層丟到 GPU        |
| CPU Threads                          | `-t <N>`                | CPU thread 數          |
| Context Length                       | `-c <N>`                | context window         |
| K Cache Quantization                 | `--cache-type-k <type>` | K cache 量化等級       |
| V Cache Quantization                 | `--cache-type-v <type>` | V cache 量化等級       |
| Flash Attention                      | `-fa` / `--flash-attn`  | flash attention 開關   |
| MoE Expert Offload / CPU MoE Layers  | `--n-cpu-moe <N>`       | MoE 專家層卸載         |
| Batch Size                           | `-b <N>` / `-ub <N>`    | batch / micro-batch    |
| Parallel Sequences                   | `--parallel <N>`        | 同時處理的 sequence 數 |

具體欄位名稱跟位置依 LM Studio 版本變化、以實際 UI 為準。新加入 llama.cpp 的旗標通常會在後續 LM Studio 版本被加進 GUI。

## 啟動 LM Studio Server

LM Studio 內建 OpenAI 相容 server、預設 port 1234。啟用步驟：

1. 載入想用的模型（GUI 左側 Chat / Local Server 切換）。
2. 切到「Local Server」分頁。
3. 設定上面對應的旗標（GPU Offload、Context、KV Quant、MoE Offload 等）。
4. 點「Start Server」、看 log 確認模型載入成功、port 顯示為 1234（或自訂）。

啟動成功後、可以用任何 OpenAI 相容 client 連接：

```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "loaded-model-name",
    "messages": [{"role": "user", "content": "Hi"}]
  }'
```

接到 VS Code Continue.dev：

```json
{
  "models": [
    {
      "title": "LM Studio",
      "provider": "openai",
      "model": "loaded-model-name",
      "apiBase": "http://localhost:1234/v1",
      "apiKey": "not-needed"
    }
  ]
}
```

`model` 欄位填 LM Studio 載入的模型名稱、要跟 GUI 顯示一致。

## 模型瀏覽器與下載

LM Studio 的內建模型瀏覽器直接連到 Hugging Face、可以搜尋 GGUF 格式的模型並一鍵下載。對「想試新模型但不想自己抓 GGUF」的使用者較友善。

下載時的選擇：

1. **量化等級**：LM Studio 會列出可用的量化版本（Q4_K_M、Q5_K_M、Q8_0 等）、可依 VRAM 預算選擇。
2. **模型大小估計**：LM Studio 通常會顯示「在你當前硬體上能不能跑」的提示；提示為估計、實際載入仍以 llama.cpp 啟動結果為準。
3. **下載位置**：LM Studio 預設下載到使用者目錄；可在設定面板改路徑（適合把模型放到大容量 SSD）。

> **事實查核註**：LM Studio 對「能否在當前硬體跑」的判讀是基於 VRAM + RAM 容量的估算、不考慮 MoE 卸載、KV cache 量化等進階設定；提示僅供參考、實際以實測為準。

## 跟 Ollama / llama.cpp 並存

LM Studio、Ollama、llama-server 可以同時跑、用不同 port：

| 推論伺服器   | 預設 port |
| ------------ | --------- |
| Ollama       | 11434     |
| llama-server | 8080      |
| LM Studio    | 1234      |

實務上同時跑多個的場景是調參階段比較不同 backend 或設定；常態使用通常一個就夠。

切換主力的判讀：

| 工作流類型                          | 較適合的主力工具                      |
| ----------------------------------- | ------------------------------------- |
| 多模型探索、Hugging Face 抓新模型試 | LM Studio（GUI 瀏覽器較順）           |
| 穩定日常寫 code、模型不常換         | Ollama（命令列管理較簡潔）            |
| 進階調參、`llama-bench` 校準        | 直接 `llama-server`（旗標控制最完整） |
| 不想接觸 CLI、視覺化看參數          | LM Studio                             |
| 多 agent / 多 client 同時連         | 任一、視併發設定                      |

## Windows + GPU 整合常見議題

Windows 上跑本地 LLM 的常見議題：

1. **NVIDIA driver 版本**：driver 太舊可能不支援 LM Studio 內建的 CUDA runtime；過新 driver 偶爾出現相容性問題。建議用 NVIDIA Studio Driver（相對 Game Ready Driver 更穩）、或 NVIDIA 官方建議的當前長期支援版本。
2. **WSL2 vs 原生 Windows**：LM Studio 在原生 Windows 跟 WSL2 都能跑；WSL2 可以更接近 Linux 環境（適合熟悉 Linux 工具的使用者）、但 GPU 透傳的配置略多。
3. **windows defender / 防毒軟體掃描**：模型檔案常為 10+ GB、安全軟體的即時掃描可能拖慢載入速度；建議把模型目錄加入排除清單。
4. **電源計劃**：Windows 的「省電」電源計劃可能讓 CPU 在閒置時降頻、影響 prefill 速度；建議使用「高效能」或自訂「卓越效能」計劃。
5. **VRAM 被其他應用佔用**：Chrome、Discord、遊戲都可能佔用 VRAM；觀察「工作管理員 → 效能 → GPU」確認 VRAM 餘量。

> **事實查核註**：上面的議題以 Windows 10 / 11 為背景、具體現象跟解法依 Windows 版本、driver 版本變化。引用前以自己版本的官方文件為準。

## 給多數讀者的建議

LM Studio 在 Windows + 獨立 GPU 場景的核心價值是「降低 MoE 卸載與 KV cache 量化的學習成本」。對下面類型的使用者特別合適：

1. 剛接觸本地 LLM、不熟悉 CLI 旗標。
2. 主力工作是探索新模型、不是調穩定 production-like 設定。
3. 想視覺化看「卸載層數 vs VRAM 用量」的關係、再決定要不要轉到 CLI。

對下面類型的使用者、Ollama 或直接 `llama-server` 通常更適合：

1. 熟悉 CLI、想最完整地控制旗標。
2. 主力是穩定日常寫 code、模型不常換。
3. 想用 `llama-bench` 做精確校準。
4. 部署到團隊或多人共用的 server 環境（GUI app 不適合 headless 部署）。

## 小結

LM Studio 在 Windows + 獨立 GPU 場景提供了「不接觸 CLI 也能調 MoE 卸載與 KV cache 量化」的入口。背後仍是 llama.cpp、GUI 欄位多數對應到 llama.cpp 旗標。選對 GPU backend、確認 driver 版本、把 GUI 設定的位置跟 [5.1](/llm/05-discrete-gpu/moe-cpu-offload-strategy/) / [5.2](/llm/05-discrete-gpu/kv-cache-quantization-strategy/) 的旗標表對應、就能跑起來。日常主力的選擇依個人工作流跟對 CLI 的偏好而定、沒有單一最佳解。

下一章：[5.5 PC 場景的模型選型優先順序](/llm/05-discrete-gpu/model-selection-priority-pc/)、用前面四章建好的工程選項回答「具體裝哪個模型」。
