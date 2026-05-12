---
title: "模組五：Windows / Linux + 獨立 GPU"
date: 2026-05-12
description: "消費級 PC（Windows / Linux + NVIDIA / AMD 獨立 GPU）跑本地 LLM 的硬體判讀、MoE CPU 卸載、KV cache 量化與 llama.cpp 調參"
tags: ["llm", "discrete-gpu", "nvidia", "amd", "windows", "linux", "llama-cpp", "moe", "vram"]
weight: 5
---

本模組的核心目標是把 [模組零](/llm/00-foundations/) 的心智模型落地到「Windows / Linux + 獨立 GPU」這條硬體路線。跟 [模組一](/llm/01-local-llm-services/)（Apple Silicon Mac）平行、共用模組零的詞彙跟 [knowledge-cards](/llm/knowledge-cards/)、但硬體判讀模型本質不同：Mac 是統一記憶體一塊預算、PC 是 VRAM + 系統 RAM 兩塊分層預算、要分開判讀。

讀完本模組後、你應該能對自己這台 PC 直接回答：能跑哪些模型、要不要卸載 MoE 專家層到 RAM、KV cache 該量化到哪一級、context 能開多大、併發數能拉到多少。

## 為什麼 PC 路線值得獨立模組

Mac 統一記憶體的判讀模型把「能載入多大模型」這個問題收斂到一塊預算。PC 場景被獨立 VRAM 拆成兩個記憶體區域、判讀軸增加：

1. **VRAM**：高頻寬區。常見消費級 NVIDIA 卡的廠商標稱頻寬大致落在數百 GB/s 到 1 TB/s 級的區間（例如 RTX 5060 Ti 16GB 標稱約 448 GB/s、RTX 5070 Ti 標稱約 896 GB/s、以廠商規格表為準）、生字速度上限主要受 VRAM 頻寬影響。
2. **系統 RAM**：高容量區。DDR5 6000 雙通道的標稱頻寬約 96 GB/s（依主機板與時序變化）、相對 VRAM 慢約一個量級、但 64GB / 128GB 在 PC 平台的擴充成本相對低、適合放容量需求大但存取頻率較低的權重。
3. **PCIe**：兩個區域之間的連線。PCIe 5.0 x16 廠商標稱單向約 64 GB/s（PCIe 4.0 x16 約一半）；實際傳輸吞吐受驅動、檔案系統與工作流影響。

這三層差異產生兩個 Mac 場景上較少出現的工程選項：

1. **[MoE 模型 + 專家層 CPU 卸載](/llm/knowledge-cards/moe-cpu-offload/)**：MoE 模型每個 token 只啟用少數專家、把不活躍的專家權重放在系統 RAM、用到再走 PCIe 拉回 GPU。讓 16GB VRAM 卡能載入 30B / 70B 等級的 MoE 模型。
2. **KV cache 量化開大 context**：把 K cache 量化到 Q8、V cache 量化到 Q4、KV cache 體積大幅壓縮、騰出的 VRAM 可用於開大 context window 或提高併發數。

這兩個選項在 Mac 統一記憶體場景下較少使用（VRAM 跟 RAM 共用、不需在兩個區域之間搬資料）、在 PC 場景則是常用的調參工具。

## 章節列表

| 章節                                                        | 主題                      | 關鍵收穫                                                             |
| ----------------------------------------------------------- | ------------------------- | -------------------------------------------------------------------- |
| [5.0](/llm/05-discrete-gpu/vram-ram-budget/)                | VRAM + RAM 分層預算       | 16GB VRAM × 64GB RAM 等情境的模型對照、跟 Mac 統一記憶體的對比       |
| [5.1](/llm/05-discrete-gpu/moe-cpu-offload-strategy/)       | MoE 模型與 CPU 卸載策略   | 何時把專家層卸到 RAM、卸幾層、prefill / generation 影響各自不同      |
| [5.2](/llm/05-discrete-gpu/kv-cache-quantization-strategy/) | KV cache 量化策略         | K=Q8 / V=Q4 跟 context window / 併發數的權衡、flash attention 的關係 |
| [5.3](/llm/05-discrete-gpu/llama-cpp-on-pc/)                | llama.cpp 在 PC 上        | CUDA / ROCm build、核心旗標地圖、`llama-bench` 校準工作流            |
| [5.4](/llm/05-discrete-gpu/lm-studio-on-windows/)           | LM Studio 在 Windows      | Windows 安裝、CUDA backend 選擇、GUI 欄位對應到 llama.cpp 旗標       |
| [5.5](/llm/05-discrete-gpu/model-selection-priority-pc/)    | PC 場景的模型選型優先順序 | 全載 14B Dense vs 卸載 30B MoE 等的選型決策                          |
| [5.6](/llm/05-discrete-gpu/gpu-vendor-differences/)         | GPU 廠商差異              | NVIDIA / AMD / Intel 的工具鏈支援度、選卡判讀框架                    |

## 跟模組一的對應關係

| 模組一（Mac）                | 模組五（PC）                            | 關係                                                         |
| ---------------------------- | --------------------------------------- | ------------------------------------------------------------ |
| 0.5 Apple Silicon 記憶體預算 | 5.0 VRAM + RAM 分層預算                 | 平行、不同硬體模型；都在 [模組零](/llm/00-foundations/) 之下 |
| 1.0 Ollama                   | （Ollama Windows 同樣可用、不獨立成章） | 跨平台、不重複                                               |
| 1.1 LM Studio                | 5.4 LM Studio 在 Windows                | Windows 多了 CUDA backend 選擇與 driver 議題                 |
| 1.2 llama.cpp                | 5.3 llama.cpp 在 PC 上                  | PC 多了 CUDA build、tensor split、`--n-cpu-moe` 等參數       |
| 1.3 VS Code + Continue.dev   | （共用、不獨立成章）                    | 介面層跨平台、設定檔幾乎相同                                 |
| 1.4 模型選型優先順序         | 5.5 PC 場景的模型選型優先順序           | 選型邏輯類似、但 PC 多了 MoE 卸載這個變數                    |
| 1.5 期望管理                 | （共用、不獨立成章）                    | 本地 vs 雲端分工跟硬體無關                                   |

## 最短路徑：16GB VRAM + 64GB RAM 跑 Qwen3 30B MoE

> **事實查核註**：本模組引用的硬體規格、模型體積、社群實測數量級、廠商工具鏈成熟度、皆以 2026 年 5 月的公開資訊與社群常見回報為基準。GPU 規格、driver 版本、llama.cpp release、模型釋出與量化版本快速演進、引用前請以 [llama.cpp release notes](https://github.com/ggml-org/llama.cpp/releases)、各廠商官方規格表、各模型 Hugging Face model card 為準、並用 `llama-bench` 或實際工作流校準。

如果你有類似 RTX 5060 Ti 16GB / 5070 Ti 16GB + 64GB DDR5 的配置、想用一小時搞定 PC 本地 LLM 寫 code、下面是最短路徑：

```bash
# 1. 裝 llama.cpp 的 CUDA build（Windows / Linux 各有預編好的 release）
# 從 ggml-org/llama.cpp GitHub release 抓 CUDA 12.x 版

# 2. 抓一個 MoE 模型（如 Qwen3-30B-A3B 的 GGUF Q4_K_M 版本）
# 從 Hugging Face 下載到 ~/models/

# 3. 啟動 server、把 30 層 MoE 專家層卸載到 CPU
./llama-server \
  -m ~/models/Qwen3-30B-A3B-Q4_K_M.gguf \
  -ngl 99 \
  --n-cpu-moe 30 \
  --cache-type-k q8_0 \
  --cache-type-v q4_0 \
  -c 32768 \
  --port 8080

# 4. 在 VS Code 裝 Continue 擴充套件、config 指向 http://localhost:8080
```

關鍵參數的意義先濃縮成一句、詳細推導留給 [5.3 llama.cpp 在 PC 上](/llm/05-discrete-gpu/llama-cpp-on-pc/)：

- `-ngl 99`：把所有可放的層丟到 GPU。
- `--n-cpu-moe 30`：把 30 層的 MoE 專家權重留在系統 RAM、不上 VRAM。實際層數視模型結構與 VRAM 餘量微調。
- `--cache-type-k q8_0` / `--cache-type-v q4_0`：KV cache 量化、騰出 VRAM 開大 context。
- `-c 32768`：context window。配上 KV cache 量化、單卡 16GB 通常能開到 128K ~ 256K（看模型）。

## 為什麼這個順序

本模組章節順序的設計脈絡：

1. **先 5.0 VRAM + RAM 分層預算**：建立 PC 硬體判讀模型、是後面所有章節的前提。
2. **再 5.1 MoE 卸載**：MoE + CPU 卸載是 PC 場景相對 Mac 的核心優勢、先把這個工程選項說清楚。
3. **接 5.2 KV cache 量化**：跟 5.1 一起決定 VRAM 怎麼切、是 PC 場景的第二個獨有選項。
4. **再 5.3 llama.cpp 在 PC 上**：把前三章的理論落地到實際參數。
5. **再 5.4 LM Studio 在 Windows**：給「不想直接面對 CLI」的讀者另一條路、補上 GUI 內對應 5.1 / 5.2 設定的位置。
6. **然後 5.5 模型選型**：所有工程選項都建立後、回答「具體裝哪個模型」。
7. **最後 5.6 GPU 廠商差異**：選好模型跟參數後、再處理 NVIDIA / AMD / Intel 的工具鏈差異。

## 不在本模組內的主題

本模組不討論：

1. **多卡 NVLink、tensor parallelism**：消費級 PC 場景通常單卡、多卡分散式推論屬於資料中心級教材。
2. **資料中心級 GPU（H100 / H200 / B200）部署**：本模組聚焦消費級 PC、不涵蓋 vLLM / TGI / Triton 等資料中心 inference server。
3. **Linux 系統管理 / CUDA 驅動安裝細節**：假設讀者已會基本系統管理；具體驅動安裝步驟交給 NVIDIA / AMD 官方文件。
4. **訓練 / fine-tuning**：跟「跑現成模型」是不同工程問題、見 [模組三](/llm/03-theoretical-foundations/) 與其推薦課程。
5. **產圖模型**：[Diffusion](/llm/knowledge-cards/diffusion/) 跟 Transformer 是不同架構、見 ComfyUI / Stable Diffusion 專門教材。
