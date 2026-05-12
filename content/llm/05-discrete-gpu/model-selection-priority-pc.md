---
title: "5.5 PC 場景的模型選型優先順序"
date: 2026-05-12
description: "PC 獨立 GPU 場景下、MoE 卸載讓「全載小模型 vs 卸載大 MoE」變成主要的選型軸；對應不同 VRAM 容量的模型推薦"
tags: ["llm", "discrete-gpu", "model-selection", "moe", "coding"]
weight: 6
---

跑穩 [推論伺服器](/llm/knowledge-cards/inference-server/) 後、下一個決策是「該裝哪個模型」。PC 場景的選型有 Mac 沒有的變數：[MoE](/llm/knowledge-cards/moe/) 模型搭配 [CPU 卸載](/llm/knowledge-cards/moe-cpu-offload/) 讓「同樣 16GB [VRAM](/llm/knowledge-cards/vram/)、要全載 14B Dense 還是卸載 30B MoE」變成主要取捨；MoE 的核心判讀軸是 [active parameter](/llm/knowledge-cards/active-parameter/) 比例。本章用優先順序而不是對比表羅列、依不同 VRAM 容量給出社群常見的候選清單與適用情境。模型檔案格式以 [GGUF](/llm/knowledge-cards/gguf/) 為主、各等級的 [量化](/llm/knowledge-cards/quantization/) 版本是選型的第二軸；coding 能力評估的常見參考是 [SWE-bench](/llm/knowledge-cards/swe-bench/) 等公開 benchmark；模型來源信任的判讀見 [model card](/llm/knowledge-cards/model-card/)。

> **事實查核註**：本章引用的模型名稱、能力等級、量化版本以 2026 年 5 月的社群可用資源為基準。模型發布速度快、3 ~ 6 個月後可能有新候選、本章建議用具體版本日期跟對應的官方 model card / 技術報告校準。

## 本章目標

1. 認識 PC 場景特有的「全載 Dense vs 卸載 MoE」選型軸。
2. 知道不同 VRAM 容量對應的候選模型清單。
3. 區分「coding 專用模型」跟「通用模型」對寫 code 任務的差異。
4. 知道量化版本的取捨（Q4_K_M / Q5_K_M / Q6_K 的選擇）。
5. 認識選型決策的觀察期跟換模型的時機。

## PC 場景特有的選型軸

Mac 統一記憶體場景下、選型主要看「能不能塞進記憶體」。PC 場景多了 MoE 卸載這個變數、變成三軸選型：

```text
選型三軸：
├── VRAM 是否能全載      → 決定是否需要卸載
├── MoE vs Dense          → 決定卸載的代價大小
└── coding vs 通用        → 決定能力對寫 code 任務的契合度
```

兩條典型路線（同樣 16GB VRAM）：

| 路線           | 範例模型                                        | 優勢                             | 代價                                    |
| -------------- | ----------------------------------------------- | -------------------------------- | --------------------------------------- |
| 全載 14B Dense | Qwen3 14B、CodeLlama 13B、DeepSeek-Coder-V2 16B | 生字速度上限高、Latency 較穩     | 模型能力 14B 級、跨檔案任務成功率較低   |
| 卸載 30B MoE   | Qwen3-30B-A3B、Llama 4 Scout                    | 模型能力 30B 級、長 context 友善 | 生字速度低於全載、對 RAM 容量有較高要求 |

社群多數寫 code 場景的回報傾向「卸載 30B MoE 對任務成敗的幫助大於速度損失」、但工作流以高頻短補完為主的使用者、有時偏好全載 14B Dense 的速度。實際取捨需用自己的工作流任務校準。

## 16GB VRAM + 64GB RAM 的候選清單

這是 2026 年 5 月 PC 場景最常被討論的配置、對應幾個主要候選：

### 候選一：Qwen3-30B-A3B（MoE、卸載）

**模型定位**：MoE 架構、總參數約 30B、active parameter 約 3B、coding / 通用混合訓練。

**啟動旗標起點**（GGUF Q4_K_M、需配合 [5.1](/llm/05-discrete-gpu/moe-cpu-offload-strategy/)）：

```bash
llama-server -m Qwen3-30B-A3B-Q4_K_M.gguf \
  -ngl 99 --n-cpu-moe 30 \
  --cache-type-k q8_0 --cache-type-v q4_0 -fa \
  -c 32768
```

**主要使用情境**：

1. 跨檔案重構、需要理解較多上下文的任務。
2. 長 context 場景（RAG、大型 codebase 索引）。
3. 中文 + 英文混合的 prompt。

### 候選二：Qwen3 14B（Dense、全載）

**模型定位**：Dense 架構、14B 參數、通用 + coding 混合訓練。

**啟動旗標起點**：

```bash
llama-server -m Qwen3-14B-Q4_K_M.gguf \
  -ngl 99 \
  --cache-type-k q8_0 --cache-type-v q8_0 -fa \
  -c 32768
```

**主要使用情境**：

1. 工作流以高頻短補完為主、對生字即時體感要求高。
2. 想保持較穩的 latency、避開 MoE 卸載的調參。
3. 系統 RAM 只有 32GB、卸載空間有限。

### 候選三：Qwen3-Coder 30B / CodeLlama 13B 等 coding 專用模型

**模型定位**：在通用訓練後、用 code corpus 做了額外的 instruction tuning 或 continued pre-training。

**社群常見回報**：

- 在「補完 / 行內編輯」這種純 code-completion 任務上、coding 專用模型通常表現較好。
- 在「需要解釋程式碼 / 設計討論」混合任務上、通用模型有時更自然。

**選擇邏輯**：若你的工作流以純補完為主、coding 專用模型是合理優先；若以 chat-based 設計討論為主、通用模型也許更合適。

### 量化版本的取捨

GGUF 量化版本對同一模型的選擇：

| 量化   | bits/權重 | 適用情境                                  |
| ------ | --------- | ----------------------------------------- |
| Q8_0   | 8         | VRAM / RAM 充裕、想接近原始品質           |
| Q6_K   | 6.56      | 平衡、品質損失社群回報為輕微              |
| Q5_K_M | 5.5       | VRAM 介於 Q4 跟 Q8 之間時的選擇           |
| Q4_K_M | 4.5       | 寫 code 場景的常見起點、體積 / 品質平衡   |
| Q3_K_M | 3.5       | VRAM 緊張時退一步、品質衰減社群回報為明顯 |

**選擇邏輯**：先用 Q4_K_M 起步、若品質符合需求且 VRAM 有餘量、可試 Q5 / Q6；若 VRAM 不足、優先考慮「換小一級的模型 + Q5/Q6」而非「同模型 + Q3」、因為品質衰減在小模型上較易感知。

## 24GB VRAM 的候選清單

24GB VRAM（如 RTX 4090、RTX 3090）能跑全載 32B Dense 或重度卸載 70B MoE：

| 模型                             | 路線              | 適用情境                             |
| -------------------------------- | ----------------- | ------------------------------------ |
| Qwen3-32B、Qwen2.5-Coder-32B     | Dense 全載 Q4_K_M | 寫 code 場景能力較 14B 顯著提升      |
| Qwen3-30B-A3B 全載 / 輕度卸載    | MoE               | 比 16GB 卸載速度快、可開更大 context |
| Llama 3.3 70B Q3 全載 / Q4 卸載  | Dense + 重度卸載  | 對能力極限有需求、可接受較慢生字     |
| DeepSeek V3 / Llama 4 Scout 卸載 | 大型 MoE          | 適合需要長 context + 多領域的工作流  |

選擇邏輯：24GB 是「Dense 32B 級」跟「MoE 70B 級」的分水嶺；多數寫 code 場景在 Dense 32B 級已能勝任、再往 70B 級的邊際效益依任務變化。

## 32GB VRAM 的候選清單

32GB VRAM（如 RTX 5090）能跑 70B Dense Q4 全載：

| 模型                        | 路線                | 適用情境                                          |
| --------------------------- | ------------------- | ------------------------------------------------- |
| Llama 3.3 70B Q4_K_M        | Dense 全載          | 通用能力強、Latency 穩定                          |
| Qwen2.5-72B Q4_K_M          | Dense 全載          | 中文 / 多語言場景                                 |
| Llama 4 Maverick 等大型 MoE | MoE 全載 / 輕度卸載 | 長 context、多任務、active parameter 友善生字速度 |

32GB VRAM 場景下、選型回到「能力 vs 生字速度」的傳統取捨、MoE 卸載這個變數的影響相對減弱。

## 8GB / 12GB VRAM 的候選清單

VRAM 較小的場景、候選清單較短：

| VRAM | 候選模型                                 | 適用情境                                         |
| ---- | ---------------------------------------- | ------------------------------------------------ |
| 8GB  | Qwen3 7B、Gemma 4 8B、Llama 3.2 8B       | 入門體驗、補完任務尚可、跨檔案任務通常需混用雲端 |
| 12GB | Qwen3 14B Q4 全載、20B MoE Q4 卸載部分層 | 介於入門跟主流之間、可選 Dense 或 MoE 起步       |

8GB 場景下、本地 LLM 的「跑得起來但能力有限」需先設好期望、見 [1.5 期望管理](/llm/01-local-llm-services/expectation-management/)（跨平台共用）。

## coding 專用 vs 通用模型

選型的另一條軸是「coding 專用模型 vs 通用模型」：

| 維度                        | coding 專用模型                                      | 通用模型                               |
| --------------------------- | ---------------------------------------------------- | -------------------------------------- |
| 補完 / 行內編輯品質         | 社群多數回報較佳                                     | 視具體模型而定                         |
| 跨檔案重構                  | 視訓練資料涵蓋程度而定                               | 大型通用模型的推理能力有時表現較好     |
| 設計討論 / 解釋程式碼       | 視訓練模式（純 completion vs instruction tuned）而定 | instruction tuned 的通用模型通常較自然 |
| 中文 / 英文 prompt          | 視模型語言訓練比例                                   | 視模型語言訓練比例                     |
| Tool use / function calling | 視模型是否做過對應訓練                               | 視模型是否做過對應訓練                 |

**選擇邏輯**：純補完場景優先 coding 專用；chat-based 工作流通用模型也許更合適；多數使用者可以用兩個（一個 coding 專用 + 一個通用）、依任務切換。

## 選型決策步驟

實際選模型時、可以照下面的步驟：

1. **盤點硬體**：VRAM 容量、系統 RAM 容量、CPU 性能。
2. **盤點工作流**：補完為主 vs 跨檔案任務為主、短 prompt 為主 vs 長 prompt 為主、純 code vs 設計討論混合。
3. **依 VRAM 級別查上面候選清單**：選 1 ~ 2 個起點模型。
4. **用 Q4_K_M 量化版本起步**：跑一週實測、用代表性任務記錄品質、速度、VRAM 用量。
5. **依瓶頸調整**：
   - 品質不夠 → 試更大模型 / 更高量化等級 / 不同訓練取向
   - 速度不夠 → 試較小 Dense 全載 / 減少卸載
   - VRAM 不夠 → 加量化（Q5 → Q4）、加 MoE 卸載、量化 KV cache
6. **建立可重複的校準腳本**：把代表性任務寫成 prompt 集、新模型來時跑一次回歸測試。

## 觀察期與換模型時機

社群常見的換模型節奏：

1. **新模型發布**：本地 LLM 模型平均每 2 ~ 3 個月有新候選。
2. **觀察期**：新模型剛發布時、量化版本可能不全、社群實測案例較少；建議等 2 ~ 4 週、看是否有 Q4_K_M / Q5_K_M 等常用量化、社群回報是否穩定。
3. **回歸測試**：用自己的校準腳本跑一次、比較跟現有主力模型的品質、速度、VRAM。
4. **切換**：明顯優於現有主力 + 校準腳本通過 + 旗標設定穩定 → 才切換。

過早跳到新模型的常見代價：量化版本不穩、社群 issue 還在湧現、自己的旗標設定要從頭調。

## 小結

PC 場景的模型選型有「全載 Dense vs 卸載 MoE」這條 Mac 沒有的軸、16GB VRAM + 64GB RAM 配置下、Qwen3-30B-A3B MoE 卸載跟 Qwen3 14B Dense 全載是兩條主要候選；24GB / 32GB VRAM 則開始能跑 Dense 32B / 70B 級。量化版本起點建議 Q4_K_M、coding 專用模型適合純補完工作流。選型決策依硬體 + 工作流 + 觀察期、建立校準腳本可降低換模型的成本。

下一章：[5.6 GPU 廠商差異](/llm/05-discrete-gpu/gpu-vendor-differences/)、處理 NVIDIA / AMD / Intel 在 llama.cpp 生態的相對位置。
