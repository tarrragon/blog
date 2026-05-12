---
title: "1.4 寫 code 場景的模型選型優先順序"
date: 2026-05-11
description: "Gemma 4 31B MTP → Qwen3-Coder 30B → Qwen3 14B → gpt-oss 20B 的取捨與適用情境"
tags: ["llm", "model-selection", "coding"]
weight: 4
---

裝完伺服器後，下一個決策是「該裝哪個 model」。本地 LLM 模型百百種，但寫 code 場景的真正候選名單其實很短：2026 年 5 月有四個值得認真考慮的選擇，加幾個 niche 選項。

本章用「優先順序」而不是「對比表羅列」呈現，因為實際使用上 95% 的讀者只需要從前兩三個選一個；後面的選擇是給特定情境用的補充。先給結論再給推導，讀者可以快速看到結論、有空再回頭看為什麼。

## 本章目標

讀完本章後，你應該能：

1. 對自己的 Mac 規格，立刻知道該裝哪個模型。
2. 理解每個模型的能力強項與適用情境。
3. 看到新模型發表時，知道怎麼放進這個優先順序。
4. 看到「最強本地模型」這類排名時、用具體任務脈絡判讀。

## 優先順序總覽

對 32GB+ Mac 的讀者、建議的選型順序：

1. **Gemma 4 31B [MTP](/llm/knowledge-cards/mtp/)**（首選）— 速度最快、coding 任務 MTP 加速 2 ~ 3 倍
2. **Qwen3-Coder 30B**（次選）— coding 專科、[SWE-bench](/llm/knowledge-cards/swe-bench/) 表現最強的本地模型
3. **Qwen3 14B**（通用備案）— 較小較快、記憶體吃緊或要跑 long context 時切回來
4. **gpt-oss 20B**（OpenAI 開源）— 風格較像 GPT、想嘗試 OpenAI 風味時用

對 24GB Mac、跳過 31B、從 14B 起步。對 16GB Mac、可用模型限於 7B 或 Gemma 4 E4B、能力明顯下降、建議混用雲端。

## 1. Gemma 4 31B MTP：日常主力首選

Gemma 4 31B MTP 在「速度 × 能力 × 工具支援」三軸取得寫 code 場景的最佳平衡、是首選的原因。Gemma 4 31B 在 SWE-bench、[HumanEval](https://github.com/openai/human-eval)（OpenAI 提供的 164 題 Python 函式補完 benchmark）等 coding benchmark 上接近 Qwen3-Coder 30B、但因為 Google 釋出官方 MTP [drafter](/llm/knowledge-cards/drafter-model/)、Ollama v0.23.1 一鍵整合、實際使用體感速度比 Qwen3-Coder 30B 快 2 ~ 3 倍（同硬體、同任務）。

**Ollama tag**：`gemma4:31b-coding-mtp-bf16`

**記憶體需求**：~18GB（含 drafter），32GB Mac 順暢、24GB Mac 吃緊。

**能力範圍**：

- 簡單 function 補完、改寫、加 type：強
- 寫 unit test、寫 docstring：強
- 解釋程式碼、提建議：中強
- 跨檔案重構：中等（仍輸雲端旗艦）
- 跟你討論架構設計：中等（會給合理方向但深度有限）
- 多步驟 agent 規劃：弱（雲端旗艦領先明顯）

**為什麼選它而不是 Qwen3-Coder 30B**：MTP 加速在寫 code 場景太明顯。Qwen3-Coder 在 benchmark 上略強，但實際工作流的「等模型回應」時間差會抵消那點 benchmark 差距。除非你的任務剛好命中 Qwen3-Coder 強過 Gemma 4 的部分（後面會說），Gemma 4 是更穩的預設。

## 2. Qwen3-Coder 30B：coding 專科

Qwen3-Coder 30B 是「benchmark 最強、速度次之」的本地 coding 模型、做為 benchmark 敏感工作流的次選。Qwen3-Coder 在 SWE-bench Verified（OpenAI 篩過的高品質子集、500 題）上達 77.2 分（2026 年 4 月 Alibaba 釋出時的公開數據）、是本地模型中 coding 表現最強的。對「複雜程式碼任務、不在乎速度差一倍」的使用者、這是更好的選擇。

**Ollama tag**：`qwen3-coder:30b`

**記憶體需求**：~18 ~ 20GB，32GB Mac 順暢。

**Qwen3-Coder 30B 強項**（JSON 結構穩定 / SQL Rust Go / 200+ 行 code / 演算法題）：

- 需要嚴格遵循 prompt 結構（例如要求輸出 JSON）— Qwen3-Coder 較穩定
- 需要寫 SQL、Rust、Go 等較少見語言 — 訓練資料較多
- 需要產出較長 code（200+ 行）— 比較不容易在中段失控
- 需要解 leetcode 風格演算法題（注重題目模式 + 標準解）— benchmark 強項

**為什麼不是首選**：MTP 加速目前限於 Gemma 4 官方 drafter、Qwen3-Coder 還沒有對應的官方 drafter（2026 年 5 月）。生字速度明顯慢於 Gemma 4 31B MTP、體感等候時間長。

## 3. Qwen3 14B：通用備案

Qwen3 14B 是 32GB Mac 想留記憶體餘裕（多 model 並存、長 [KV cache](/llm/knowledge-cards/kv-cache/)、其他重 app）時的合理「降一級」選擇。能力較弱但記憶體佔用減半。

**Ollama tag**：`qwen3:14b`

**記憶體需求**：~10GB，24GB Mac 順暢、32GB Mac 留更多空間給 IDE 與系統。

**能力範圍**：

- 簡單 function 補完、加 type：尚可
- 解釋程式碼：尚可
- 寫 unit test：有時會錯
- 跨檔案重構：明顯弱於 31B 等級
- 複雜推理：明顯弱

**主要使用情境**：

1. 24GB Mac 的預設選擇。
2. 32GB Mac 但想留記憶體給其他重 app（如同時跑 Docker、跑大型測試）。
3. Tab autocomplete 的小模型（搭配主對話 31B 模型）。
4. 長 context 場景（KV cache 佔用較少）。

## 4. gpt-oss 20B：OpenAI 開源版

gpt-oss 20B 是 OpenAI 在 2025 年釋出的開源模型、風格較接近 GPT 系列、定位是「習慣 GPT 語感的使用者」的補充選項。如果你已經很習慣 GPT 的回答方式、這個模型的「語感」會比 Gemma 或 Qwen 親切。

**Ollama tag**：`gpt-oss:20b`

**記憶體需求**：~12GB，24GB Mac 起點可跑。

**能力範圍**：

- coding 表現中等，輸 Gemma 4 31B、Qwen3-Coder 30B。
- 一般對話、解釋、寫作風格較 polished。
- Tool use 支援較好（OpenAI 自家生態的優勢）。

**主要使用情境**：

1. 你已習慣 GPT 風格、不想換語感。
2. 寫 code + 一般對話混用（一般對話 gpt-oss 較自然）。
3. 24GB Mac 的進階選擇（比 Qwen3 14B 大、能力強，比 Gemma 4 31B 小、塞得進）。

## 16GB Mac 的選擇

16GB Mac 是現實上的最小可用配置。能跑的選擇：

| 模型         | Ollama tag    | 體感                              |
| ------------ | ------------- | --------------------------------- |
| Gemma 4 E4B  | `gemma4:e4b`  | 寫 code 勉強堪用、明顯弱於 14B 級 |
| Qwen3 7B     | `qwen3:7b`    | 跟 E4B 類似                       |
| Llama 3.2 8B | `llama3.2:8b` | 通用任務尚可，coding 較弱         |

實話：16GB Mac 跑這些模型只能做「簡單補完、解釋短段程式碼」、比較複雜的任務還是要切雲端。如果你想以本地 LLM 為主力寫 code、16GB 不在本指南推薦範圍；建議混用雲端、或評估升級到 24GB+ Mac。

## 48GB+ Mac 的選擇

48GB 以上記憶體可以跑更大模型，但邊際效益要考慮。可用選擇：

| 模型                 | Ollama tag               | 記憶體 | 體感                                 |
| -------------------- | ------------------------ | ------ | ------------------------------------ |
| Qwen3-Coder 32B Q5   | `qwen3-coder:32b-q5_K_M` | ~22GB  | 比 Q4 略強，差異不大                 |
| Llama 3.3 70B Q4     | `llama3.3:70b`           | ~42GB  | 通用能力強，但 coding 不一定超越 31B |
| Qwen3-Coder 32B bf16 | `qwen3-coder:32b-bf16`   | ~64GB  | 64GB Mac 才行，接近 GPT-4 mini       |

48GB Mac 的主要收益不是「跑得到更大模型」，而是「同時跑兩個 model」或「長 context 不卡」。例如同時跑 31B 主對話 + 4B autocomplete + 留空間給 IDE。

## 判斷新模型是否值得換的步驟

本地模型發布速度很快、每 2 ~ 3 個月會有新候選。判斷要不要換的步驟：

1. **看 [SWE-bench](/llm/knowledge-cards/swe-bench/) Verified 分數**：新模型在 SWE-bench Verified 上比現用模型高 5 分以上、值得試。
2. **看模型大小與記憶體預算**：新模型大小落在 Mac 預算內、再進入下一步評估。
3. **看 [speculative decoding](/llm/knowledge-cards/speculative-decoding/) 支援**：有 [drafter](/llm/knowledge-cards/drafter-model/) 的新模型在體感速度上常勝過稍強但沒加速的模型。
4. **用自己的 5 ~ 10 個日常任務當私人 benchmark**：公開 benchmark 是參考、自己跑一遍才能拿到能用在自己場景的數字。
5. **看 Ollama / LM Studio 的 release notes**：新模型要被伺服器支援、Ollama registry 已收錄的模型用起來最直接。

合理的更換節奏是一年 2 ~ 3 次主力模型。每換一次要重新適應它的語感、prompt 風格、體感速度、切換成本不算低；穩定下來再換、收益比追新發布每個都試大。

## 量化等級的選擇

對所有模型，量化等級的選擇大致一致：

| 量化等級  | 建議使用情境                                                |
| --------- | ----------------------------------------------------------- |
| Q8 / bf16 | 32GB+ Mac、品質敏感任務、能塞得進就用                       |
| Q5_K_M    | 24GB Mac 跑 14B 模型；32GB Mac 跑 31B（記憶體稍緊）         |
| Q4_K_M    | **主流甜蜜點**。32GB Mac 跑 31B Q4 是 2026 年最佳價格效能比 |
| Q3        | 寫 code 場景品質下降明顯、慎用、見下方判讀                  |

量化等級的延伸判讀：

- **Q8 / bf16 的回退條件**：模型載入時 swap 到 SSD（生字速度掉一個量級）就要往下降一級。
- **Q5_K_M 的回退條件**：載入後 KV cache 跟 IDE 一起擠到記憶體上限、改 Q4_K_M。
- **Q4_K_M 的回退條件**：跑 coding 任務通過率明顯下降（基準 vs Q5 / Q8 下降 10% 以上）就換較小模型的 Q5、不再下降到 Q3。
- **Q3 的觸發訊號**：hallucination 上升、編造 API、長 context 累積誤差。寫 code 場景的具體判讀：Q3 31B 在 coding 任務上常輸給 Q5 14B、選 model size 時先看任務通過率、再用量化調記憶體、不是反過來。

## 適合寫 code 以外場景的模型

以下五類模型各自有專屬定位、跟「寫 code 主力」是不同的工作流；放在寫 code 主力位置會踩到能力錯位。每類各自有不同的判讀條件、用同一個欄位塞會遺失各自的失敗模式。

### Llama 3.x base 等 base model

[Base model](/llm/knowledge-cards/base-model/) 是純粹做下一個 token 預測訓練、沒做 [instruction-tuning](/llm/knowledge-cards/instruction-tuned/) 的原始模型。直接拿來對話會跟著 prompt 隨機接龍、不會「回答你的問題」。適合下游 fine-tuning 跟研究；寫 code 場景改選同 family 的 instruction-tuned 版本（例如 `llama3.3:70b-instruct` 而不是 `llama3.3:70b`）。

### 純對話模型（Vicuna、ChatGLM 早期等）

純對話模型是 2023 年早期對話研究的成果、訓練資料偏自然對話、coding 表現遠輸後來的專科模型。早期教學示範或對話技術 baseline 仍會用到；現階段 coding 任務直接選 Qwen3-Coder 或 Gemma 4、不在這條路線上糾結。

### 多模態模型（Llava、Gemma 4 多模態版等）

多模態模型訓練資料含圖片 + 文字、能做圖片理解、UI 描述、OCR、圖文對應、適合「給 LLM 看截圖」這類工作流。寫 code 場景如果不需要看圖、改選同等級的純文字模型較省記憶體（多模態的 vision tower 佔額外 GB 級記憶體、純文字 coding 用不到）。

### 中文特化模型

中文特化模型在純中文寫作、客服場景表現好、但 coding 仍以英文 prompt + 英文 code comment 為主流。寫 code 用通用模型 + 英文 prompt 通常表現較穩、中文特化模型反而在英文程式碼相關任務上劣勢。除非工作流真的有大量中文 docstring / 註解需求、否則用通用模型。

### 「最新最強」測試模型

社群每週都有新模型釋出、號稱「跑分爆表」。日常主力建議等社群驗證 1 ~ 2 個月再採用、避免踩到「benchmark 強但 prompt 適應性差」「prompt 模板未進入主流工具預設」的坑。嘗鮮跟跑分是另一條工作流、用 LM Studio 探索性測試後再決定是否切主力。

## 模型不只 chat、還有 embedding

Continue.dev 的 codebase 索引功能要用 embedding model，這跟 chat model 是兩種不同的模型。常用 embedding：

```bash
ollama pull nomic-embed-text
```

`nomic-embed-text` 約 274MB，記憶體佔用低，是 Continue.dev codebase 索引的好搭檔。其他選項：

| Embedding 模型      | 大小  | 用途                      |
| ------------------- | ----- | ------------------------- |
| `nomic-embed-text`  | 274MB | 主流選擇，英文為主        |
| `mxbai-embed-large` | 670MB | 較強的英文 embedding      |
| `bge-m3`            | 1.2GB | 多語言（含中文）embedding |

Embedding 模型的選擇對 codebase 搜尋品質有影響，但邊際效益遠小於 chat model。先用預設 `nomic-embed-text`，有需求再換。

## 何時不適用本章優先順序

本章選型假設「Apple Silicon Mac + 寫 code 為主 + 個人使用」。以下情境的選型邏輯不同、需要另外的判讀路徑：

| 情境                           | 該往哪去                                                                                               |
| ------------------------------ | ------------------------------------------------------------------------------------------------------ |
| Windows / Linux + 獨立 GPU     | 模組五 [VRAM + RAM 分層預算](/llm/05-discrete-gpu/vram-ram-budget/) — VRAM 限制 + MoE CPU 卸載決定選型 |
| 需要 vision / multimodal       | 改用多模態模型（如 Gemma 4 多模態版）、本章選型只覆蓋純文字 coding                                     |
| 離線部署到生產（不接個人 Mac） | 考慮 vLLM、TGI 等資料中心 inference server、本章假設個人桌機推論                                       |
| 訓練 / fine-tune 為主          | 模組三 [訓練流程](/llm/03-theoretical-foundations/training-pipeline/)、推論優先順序不適用              |
| 非英文工作流 / 中文寫作為主    | 中文特化模型（DeepSeek、Yi 等）、本章 coding 場景以英文 prompt 為基準                                  |
| 嘗鮮 / 跑分驗證新模型          | 用 LM Studio 探索性測試、跟本章主力選型分開、避免日常主力被新模型 churn                                |

## 給讀者的最快決策路徑

決策表把記憶體預算跟用途摺成一張快查、依情境定位、不需要重讀整章：

| 你的情境                   | 該裝的 model                              | 觸發回退條件                                       |
| -------------------------- | ----------------------------------------- | -------------------------------------------------- |
| 32GB+ Mac、首次本地 LLM    | `gemma4:31b-coding-mtp-bf16`              | 跑 Qwen3-Coder 強項任務時改用下一列                |
| 32GB Mac、想要 coding 最強 | `qwen3-coder:30b`、接受速度比 Gemma 慢    | 體感等候時間太久、退回 Gemma 4 MTP                 |
| 24GB Mac                   | `qwen3:14b` 或 `gpt-oss:20b`              | 任務複雜度超過 14B 上限、改混用雲端                |
| 16GB Mac                   | `gemma4:e4b` 或 `qwen3:7b`、主力仍雲端    | 跨檔案 / 多步驟任務直接切雲端                      |
| 48GB+ Mac、要榨乾硬體      | `qwen3-coder:32b-bf16` 或同時跑兩個 model | 同時跑兩 model 時 KV cache 擠到上限、改 Q5 量化    |
| 想當 codebase 搜尋用       | + `nomic-embed-text`（embedding model）   | 大型 monorepo 索引品質差、換 cloud embedding model |
| 想當 tab autocomplete 用   | + `gemma4:e4b` 或 `qwen3:7b`（速度優先）  | autocomplete 延遲 > 500ms、降到更小的 model        |

決策表的兩個閱讀方式：先按「你的情境」找對應 model、再注意「觸發回退條件」決定何時切換到下一行。回退條件常被忽略、導致讀者在條件變化時還抱著原本的選擇。

## 小結

寫 code 場景的本地模型優先順序在 2026 年 5 月很清楚：Gemma 4 31B MTP 是預設首選（速度最快），Qwen3-Coder 30B 是 coding 專科次選（benchmark 最強），Qwen3 14B 是通用備案，gpt-oss 20B 是 OpenAI 風味補充。記憶體預算決定能跑哪一級；量化等級用 Q4_K_M 是甜蜜點。

下一章：[1.5 期望管理](/llm/01-local-llm-services/expectation-management/)，把本地 LLM 放在「免費的初階 pair programmer」這個正確位置，避免錯誤期待造成的挫折。
