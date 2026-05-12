---
title: "5.6 GPU 廠商差異"
date: 2026-05-12
description: "NVIDIA CUDA、AMD ROCm、Intel ARC 在 llama.cpp 生態的相對位置、選卡時的判讀軸"
tags: ["llm", "discrete-gpu", "nvidia", "amd", "intel", "cuda", "rocm"]
weight: 7
---

選 GPU 跑本地 LLM 不只看 VRAM 容量與 [memory bandwidth](/llm/knowledge-cards/memory-bandwidth/)、工具鏈支援度同樣重要。NVIDIA / AMD / Intel 三家廠商在 llama.cpp 生態的位置不同、CUDA 之外的 backend 仍在演進。本章整理三家在 2026 年 5 月的相對位置、跟選卡時值得考慮的判讀軸。本章不重複 [統一記憶體](/llm/knowledge-cards/unified-memory/) 的 Mac 場景、改聚焦 PC 獨立 VRAM 的廠商工具鏈差異。

> **事實查核註**：GPU 工具鏈的支援度依 driver 版本、llama.cpp release 與廠商策略快速演進、本章描述為 2026 年 5 月的社群常見回報、建議引用前查閱對應 backend 的官方文件、[llama.cpp release notes](https://github.com/ggml-org/llama.cpp/releases) 跟自己硬體的實測。

## 本章目標

1. 知道 NVIDIA CUDA、AMD ROCm、Intel SYCL、跨平台 Vulkan 各自的成熟度。
2. 認識「工具鏈支援度」相對「硬體規格」對本地 LLM 體驗的重要性。
3. 在選卡時、能用「工具鏈 × 規格 × 預算」三軸做判讀。
4. 認識常見的混合場景（雲端 + 本地）。

## NVIDIA CUDA：當前生態預設

NVIDIA GPU + CUDA backend 是 2026 年本地 LLM 社群的事實預設。原因不是「規格最好」、而是「工具鏈最成熟」：

1. **llama.cpp CUDA backend 開發最久、PR 跟 issue 數量最多**：新功能（新量化、flash attention 改進、speculative decoding 等）通常先在 CUDA backend 落地。
2. **driver 跟 CUDA toolkit 對齊明確**：driver 版本對應 CUDA 版本的表清楚、出問題容易查。
3. **社群實測案例多**：Reddit、HuggingFace forum、GitHub issue 上、絕大多數 benchmark 跟調參討論基於 CUDA。
4. **上層工具（Ollama、LM Studio）優先支援**：新版本通常先 CUDA、再 Vulkan、再 ROCm。

社群常見回報的 NVIDIA 卡分級（依 VRAM 容量為主、寫 code 場景）：

| 等級           | 代表卡型                            | 適用情境                                  |
| -------------- | ----------------------------------- | ----------------------------------------- |
| 入門           | RTX 5060 8GB / RTX 4060 8GB         | 試水溫、跑 7B 級模型                      |
| 主流（甜蜜點） | RTX 5060 Ti 16GB / RTX 5070 Ti 16GB | 30B MoE 卸載、寫 code 場景社群常見起點    |
| 進階           | RTX 4090 24GB / RTX 5080 16GB       | 32B Dense 全載 / 70B MoE 卸載             |
| 旗艦           | RTX 5090 32GB                       | 70B Dense Q4 全載、長 context、多模型併存 |
| 上一代二手     | RTX 3090 24GB                       | 二手市場價格可能更友善、CUDA 支援度仍佳   |

**選卡時的常見軸**：

1. **VRAM 容量決定模型上限**：16GB 起步可跑 30B MoE 卸載、24GB 跑 32B Dense、32GB 跑 70B Dense。
2. **VRAM 頻寬決定生字速度上限**：同 VRAM 容量下、頻寬接近兩倍的卡（如 5070 Ti 對 5060 Ti）生字速度通常顯著差。
3. **CUDA compute capability**：影響某些優化能否啟用、新世代卡通常有額外指令支援。
4. **driver 長期支援**：較新世代卡的 driver 支援週期通常較長、適合長時間用。

## AMD ROCm 與 Radeon

AMD GPU 在 llama.cpp 生態的位置：ROCm backend 在演進、Vulkan backend 是跨平台 fallback。

### ROCm backend

ROCm（Radeon Open Compute）是 AMD 的 GPU 計算平台、定位類似 CUDA。社群常見回報的當前狀態：

1. **Linux 支援度較 Windows 成熟**：ROCm 在 Linux 上發展時間較長、Windows 版本相對年輕。
2. **支援 GPU 清單**：ROCm 對「官方支援」的 GPU 清單有明確限制、清單外的卡也許能跑、但走 unsupported 路徑。
3. **llama.cpp ROCm build 跟 CUDA build 的功能差異**：多數核心功能跨 backend 一致、新功能 cherry-pick 速度通常稍慢於 CUDA。
4. **效能對比**：同價格段、AMD 卡的 VRAM 容量有時較大；但生字速度依模型跟設定變化、社群回報的 NVIDIA / AMD 對比結果不一致、需自己硬體實測。

### Vulkan backend

Vulkan 是跨平台 GPU API、llama.cpp 的 Vulkan backend 適合：

1. **AMD GPU on Windows**：ROCm Windows 不穩或不支援時的選項。
2. **Intel ARC**：見下節。
3. **跨平台 fallback**：希望同一份 binary 跑在多種 GPU 上。

社群常見回報：Vulkan backend 的 throughput 通常較同硬體的 CUDA / ROCm backend 低、但通用性高。

### 選 AMD 卡的判讀

| 情境                                   | 建議                                                       |
| -------------------------------------- | ---------------------------------------------------------- |
| Linux 主力使用者、想避開 NVIDIA driver | AMD + ROCm on Linux 是合理選擇、先確認卡型在 ROCm 支援清單 |
| Windows 主力使用者                     | NVIDIA + CUDA 仍是社群預設較順的路徑                       |
| 同價格段、AMD VRAM 容量明顯較大        | 評估「容量優勢 vs 工具鏈成本」、用自己工作流校準           |
| 已有 AMD 卡、想試本地 LLM              | 直接試 Vulkan / ROCm backend、看是否符合需求               |

## Intel ARC

Intel 的獨立 GPU 系列 ARC（A 系列、後續預期 B 系列）在 llama.cpp 生態仍處於相對年輕的階段：

1. **可用 backend**：Vulkan（通用）、SYCL / OpenVINO（Intel 特化）。
2. **VRAM 容量**：ARC A770 16GB 的 VRAM 容量在價格段內競爭力較強。
3. **工具鏈成熟度**：社群實測案例較 NVIDIA / AMD 少、預期需要較多自己摸索。
4. **driver 演進**：Intel ARC driver 在 2026 年仍持續演進、不同版本的 throughput 可能差異較大。

選 Intel ARC 的合理情境：

1. 想試「相對冷門但價格友善」的選項。
2. 已有 Intel 平台、想保持廠商一致。
3. 不介意花時間自己調工具鏈設定。

對「想最快跑起來、最少調參」的使用者、ARC 不是最順的選擇。

## 工具鏈 × 規格 × 預算的判讀框架

選卡時的三軸框架：

```text
工具鏈支援度（CUDA > ROCm > Vulkan > SYCL）
  ×
硬體規格（VRAM 容量 + VRAM 頻寬 + CUDA core / CU 數量）
  ×
預算（含後續電費、機殼散熱、電源升級）
```

判讀順序：

1. **先確認工具鏈支援度符合自己的折騰意願**：怕折騰選 NVIDIA、樂於折騰可考慮 AMD / Intel。
2. **再依預算選 VRAM 容量級別**：16GB 起步、24GB 進階、32GB 旗艦。
3. **同容量下選頻寬較高的卡**：對生字速度影響直接。
4. **預留升級空間**：機殼散熱、電源、PCIe lane 配置會影響後續多卡或換卡的選擇。

## 雲端 + 本地的混合場景

本地 LLM 不必獨自解決所有任務、雲端 + 本地的混合是社群多數使用者的實際做法：

| 任務類型                       | 適合本地                     | 適合雲端                          |
| ------------------------------ | ---------------------------- | --------------------------------- |
| 補完、行內編輯（高頻、短回答） | 本地反應快、不消耗 API quota | 雲端 latency 較高、成本累積       |
| 跨檔案重構、設計討論           | 視本地模型能力               | 旗艦模型（Claude、GPT-5）能力較強 |
| 隱私敏感內容、未公開 codebase  | 本地 prompt 不離開機器       | 視服務的資料政策                  |
| 試新 prompt、調 prompt 工程    | 本地快速迭代、無 quota 壓力  | 雲端做最終驗證                    |
| 一次性 / 偶爾的複雜任務        | 投資本地硬體可能不划算       | 雲端按使用量付費較划算            |

社群常見的混合做法：本地跑 30B 級 MoE 處理日常補完、跨檔案重構或設計討論切到雲端旗艦。Continue.dev 等工具支援同時設定多個 model、可以快速切換、見 [1.3 VS Code + Continue.dev 整合](/llm/01-local-llm-services/vscode-continue-integration/)。

## 給讀者的選卡判讀

整合本章與 [5.0 VRAM + RAM 分層預算](/llm/05-discrete-gpu/vram-ram-budget/) 的建議：

1. **NVIDIA 是當前社群預設**：怕折騰、想最大化「跑得起來」概率、選 NVIDIA。
2. **VRAM 16GB 是常見起點**：16GB VRAM + 64GB RAM 配 30B MoE 卸載、是 2026 年寫 code 場景的常見配置。
3. **頻寬比容量更影響日常體感**：同容量下、頻寬接近兩倍的卡（如 5070 Ti 對 5060 Ti）日常生字速度差異明顯。
4. **二手卡也是選項**：RTX 3090 24GB 二手市場價格依在地市場變化、CUDA 支援度仍佳、適合預算敏感但想要 24GB VRAM 的使用者。
5. **多卡不是優先升級方向**：單人寫 code 場景下、單卡 + 良好設定通常勝過雙卡入門配置。

## 小結

GPU 廠商在本地 LLM 生態的位置由「工具鏈支援度」決定、不只看硬體規格。NVIDIA CUDA 是 2026 年的事實預設、AMD ROCm 在 Linux 上演進、Vulkan 是跨廠商 fallback、Intel ARC 仍年輕。選卡時的三軸框架是「工具鏈 × 規格 × 預算」、判讀順序由折騰意願決定、再依預算選 VRAM 級別。本地 + 雲端混合是社群多數使用者的實際做法、不需要本地解決所有任務。

本章是模組五的最後一章。下一步可以回到 [模組五 _index](/llm/05-discrete-gpu/) 看其他章節、或進入 [模組四 應用層原理](/llm/04-applications/) 看 LLM 作為系統元件的設計取捨。
