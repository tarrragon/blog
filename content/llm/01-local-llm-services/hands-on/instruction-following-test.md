---
title: "Hands-on：跨資料夾風格 follow 任務的模型對比"
date: 2026-05-12
description: "1B / 4B / 8B / 跨代 4B 在「讀風格參考、follow 既有格式、寫新章節」任務上的 structural metrics 對比、揭示 model size 不是唯一因素"
tags: ["llm", "hands-on", "ollama", "gemma", "qwen", "instruction-following"]
weight: 7
---

本篇是個讓本地 LLM 在「**讀兩個資料夾、學風格、寫新章節**」任務上自我評估的實驗。任務本身內容無關緊要（隨便挑了一份私人創作資料夾）、要看的是**不同模型在 instruction following / format consistency / 篇幅控制三個維度的差距**。

實驗跑了四個本地模型對比：

- `gemma3:1b`（815 MB、舊代 / 小）
- `gemma3:4b`（3.3 GB、舊代 / 中）
- `qwen3:8b`（5.2 GB、跨家族 / 大）
- `gemma4:e4b`（9.6 GB、新代 / 中、bf16）

對應 [4.2 Agent 架構](/llm/04-applications/agent-architecture/) 「規劃能力是雲端旗艦的明顯強項、本地小模型的明顯弱項」這條觀察、用具體 structural metrics 驗證、並揭示**「最新世代 + 較大 size」未必比「跨家族 / 較強訓練」勝出**。

> **驗證日期**：2026-05-12
> **環境**：Ollama 0.23.2、Apple Silicon、MPS backend
> **任務**：讀資料夾 A（風格參考、5 章已寫完）+ 資料夾 B（同類型、5 章已寫完、需寫 v06）→ 為 B 生成 v06
> **評估方式**：純 structural metrics、不評論內容品質

## 任務設計

兩個資料夾結構：

```text
A/                          B/
├── README.md               ├── README.md
├── v01_XXX.md              ├── v01_XXX.md
├── v02_XXX.md              ├── v02_XXX.md
├── v03_XXX.md              ├── v03_XXX.md
├── v04_XXX.md              ├── v04_XXX.md
└── v05_XXX.md              └── v05_XXX.md
                            └── v06_XXX.md  ← 要生成
```

兩個資料夾用**不同 markdown 格式**：

- A 風格：`# 標題`（H1）+ `## 場景設定` 段 + 結尾 `**【本章結束】**`
- B 風格：`## v0X｜<主題>（<角色1>×<角色2>）`（H2）+ 直接敘事、無結尾 marker

LLM 看完 A + B 後、要寫 B 的 v06——**必須 follow B 的格式、不是 A 的**。是個 format discrimination 測試。

## 評估維度

純 structural、不涉內容：

| 維度             | 測法                                          |
| ---------------- | --------------------------------------------- |
| 篇幅控制         | char count、跟 B 既有 v01-v05 平均比          |
| 段落結構         | paragraph count、avg paragraph char           |
| Markdown heading | H1 / H2 count、是否寫對 v06 title 格式        |
| 結尾 marker      | 是否誤加 A 風格的「**【本章結束】**」         |
| 角色 fidelity    | 提到 B 兩個主角名次數（太少 = 內容偏離）      |
| 跨資料夾串戲     | 提到 A 資料夾角色名次數（contamination）      |
| 對話 follow      | 「對話行」（行首是 `「`）數量、跟 baseline 比 |
| 生成時間         | 從送 prompt 到收完整 response                 |

不評估的：

- 內容品質、文筆好壞
- 敘事邏輯是否合理
- 角色塑造是否生動

純 structural 評估的好處是 reproducible、不需 reviewer 主觀判斷、可自動跑。

## Baseline：B 既有 v01-v05 的 metrics

B 資料夾 5 個既有章節的平均：

| Metric                   | Average        |
| ------------------------ | -------------- |
| char count               | ~933           |
| paragraph count          | ~32            |
| avg paragraph chars      | ~29            |
| dialogue lines           | ~7             |
| H1 used                  | 0（全部用 H2） |
| H2 used                  | 1              |
| 結尾「**【本章結束】**」 | 全部 False     |
| Cross leak               | 全部 0         |
| 主角名提及（合計）       | ~60            |

這是 LLM 該模仿的目標。

## 四個模型的結果

四個 model 跑同樣 prompt、同樣輸入內容。

### 對比表

| 維度                | Baseline | `gemma3:1b`  | `gemma3:4b` | `qwen3:8b`       | `gemma4:e4b`          |
| ------------------- | -------- | ------------ | ----------- | ---------------- | --------------------- |
| **模型大小**        | —        | 815 MB       | 3.3 GB      | 5.2 GB           | 9.6 GB（bf16）        |
| **發布世代**        | —        | Gemma 3      | Gemma 3     | Qwen 3           | **Gemma 4（2026/4）** |
| char count          | ~933     | 4324（4.6×） | 1330        | **951（1.02×）** | 679                   |
| paragraph count     | ~32      | 145          | 29          | **36**           | 11                    |
| avg paragraph chars | ~29      | 30           | 46          | **26**           | 62                    |
| H1 = 0              | ✓        | ✗（1）       | ✓           | ✓                | ✗（1）                |
| H2 = 1              | ✓        | ✗（0）       | ✓           | ✓                | ✗（3）                |
| v06 title 格式      | —        | ✗            | ✓           | ✓                | ✗                     |
| 結尾 marker         | False    | ✓            | ✓           | ✓                | ✓                     |
| Cross leak          | 0        | ✓（0）       | ✓（0）      | ✓（0）           | ✓（0）                |
| dialogue lines      | ~7       | 4            | **0**       | **7**            | 0                     |
| 主角名提及（合計）  | ~60      | 286          | 24          | **27**           | **0**                 |
| **通過項目**        | —        | **2 / 7**    | **6 / 7**   | **7 / 7**        | **1 / 7**             |
| 生成時間            | —        | 41.8s        | 36.5s       | 97.5s            | 43.5s                 |

### 各模型觀察

**`gemma3:1b`（815 MB）**：

- 篇幅 4.6× 失控、段落數 4.5× 超標、用 H1 而不是 H2。
- 顯示 1B 模型對「2000-3000 字」這種 numeric instruction 沒有有效執行能力、會一直生成到 context 限制。
- 但 cross leak 0、結尾 marker 也沒誤加——「不要 X」這類 negative instruction follow 較成功。

**`gemma3:4b`（3.3 GB）**：

- 篇幅 / 段落 / heading 結構全 OK、明顯比 1B 大幅改善。
- **dialogue lines = 0**：完全沒寫對話、整篇純敘事。表示 4B 抓到字面 structural feature、但沒抓到「對話 driven 敘事」這個 stylistic feature。
- 主角名提及 24 次（baseline ~60）—內容偏短、提及次數偏低、但比例合理。

**`qwen3:8b`（5.2 GB、跨家族）**：

- **唯一 7/7 全 pass 的模型**——篇幅完美匹配（951 vs ~933）、段落數合理（36 vs ~32）、heading 對、對話 7 行完全等於 baseline。
- 跨家族 + 大一級的組合表現質變，比同家族下一級的 4B 模型大幅提升。
- 代價：生成時間 97.5s、約是 4B 模型的 2.7×。

**`gemma4:e4b`（9.6 GB、新代）**：

- **驚人的 1/7、最差表現**——比 1B 還少通過項目。
- **主角名提及 0**：完全沒寫角色名、純抽象敘述「某一方」「另一方」。
- **dialogue 0**：沒對話。
- **生成內容是「劇情大綱建議」而非實際章節**：含「劇情核心思路」「預計情緒強度」「寫作切入點建議」等 meta-text。
- 輸出末尾「**（此為結構化建議、等待具體的指令後、將會生成與風格一致的劇情內容。）**」——明示它把 prompt 理解成「給建議框架、等下一步」。

### Strict prompt retest：揭示 internal alignment

懷疑 1/7 可能是「prompt 不夠強硬」、用 strict prompt 重跑 `gemma4:e4b`。Strict 加了八條規則、明示：

```text
- 直接從 `## v06｜...` 開頭、不寫前言
- 絕對不可寫「劇情核心思路」「預計情緒強度」「寫作切入點」等 meta-text
- 必須直接寫敘事內容、含對話、動作、感受描寫
- 強制提到角色名多次、不要用「某一方」「另一人」抽象稱呼
- ...
```

Strict prompt 結果：

| Metric         | 原 prompt | strict prompt | 變化       |
| -------------- | --------- | ------------- | ---------- |
| char count     | 679       | 660           | 相同量級   |
| H1 = 0         | ✗（1）    | ✓             | **改善**   |
| H2 = 1         | ✗（3）    | ✓             | **改善**   |
| v06 title 格式 | ✗         | ✓             | **改善**   |
| meta-text 出現 | ✓         | ✗             | **改善**   |
| dialogue lines | 0         | 3             | **改善**   |
| **主角名提及** | **0**     | **0**         | **未改善** |
| **通過項目**   | **1 / 7** | **4 / 7**     | **+3**     |

從 1/7 → 4/7、prompt 強化明顯有用。但**主角名提及兩次都 0**、即使 strict prompt 明示「強制提到角色名」、模型仍用「兩人」「彼此」「對方」抽象稱呼。

這比「模型不會 follow」更精確、是兩個層次的 follow 差別：

- **Surface level instruction**（heading 格式、不要 meta-text、要對話）：model 願意 follow strict prompt。
- **Semantic level instruction**（在這個情境用具名角色）：model 有 **internal alignment 抗拒**、即使 prompt 明示也不 follow。

Gemma 4 e4b 是 device-deployable edge variant、RLHF 可能特別針對「敏感情境下的人物識別」做 alignment。這個 alignment 比 prompt-level instruction follow 更深、是 hard line、不能用 prompt engineering 繞過。

## 關鍵觀察

### Model size 不是唯一因素、訓練 alignment 更重要

最反直覺的結果：

- `gemma4:e4b`（9.6 GB、最新世代）原 prompt 通過 **1/7**、strict prompt 通過 **4/7**。
- `gemma3:4b`（3.3 GB、舊一代）通過 **6/7**。
- `qwen3:8b`（5.2 GB、跨家族）通過 **7/7**。

「最大 + 最新」不等於「最好 follow instruction」。在這個任務上、ranking 是：

```text
qwen3:8b > gemma3:4b > gemma3:1b ≈ gemma4:e4b (strict) > gemma4:e4b (default)
```

可能因素：

1. **訓練資料分佈差異**：Qwen 系列訓練資料含大量中文、對中文 instruction follow 更穩。
2. **Edge variant 的 alignment 設計**：`gemma4:e4b` 是 device-deployable edge variant、RLHF 可能特別在敏感情境用 conservative output。Strict prompt 能改善 surface-level（heading、meta-text、對話）、但 semantic-level（具名角色）有 hard line 不能繞過。
3. **跨家族效應 > 跨代效應**：Qwen vs Gemma（不同家族）比 Gemma 3 vs Gemma 4（同家族跨代）影響更大。

### 兩層 instruction follow

`gemma4:e4b` 的 strict prompt retest 揭示一個重要區分：

- **Surface-level instruction**（heading 格式、不要 meta-text、要對話）：可以用 strict prompt 改善、prompt engineering 有效。
- **Semantic-level alignment**（特定情境的角色處理、敏感主題的表述方式）：是 RLHF 階段建立的 hard line、prompt engineering 繞不過。

設計應用時要意識：**「LLM follow 不了 instruction」可能不是能力問題、是 alignment 問題**。模型訓練時被刻意 align 不做某些事、即使 prompt 明示也不會做。發現這種情況、應該換 model（或用 less-aligned variant）、不要繼續調 prompt 浪費時間。

### 「最新世代」的標籤可能誤導

Gemma 4 是 2026/4/2 才發布的最新代、size 也夠大、但在這個 instruction following 任務上**輸給 6 個月前發布的 Gemma 3 4b**。

設計應用 / 選模型時、不能只看「最新 / 最大」、要實測對自己 task 的表現。Benchmark ranking（如 LMSYS Chatbot Arena）反映平均表現、不一定 reflect 你的 narrow 任務。本實驗示範了「自己跑一次」比「看 benchmark」更可靠的判讀方法。

### Structural feature 跟 stylistic feature 兩層

跨四個模型一致觀察：

- **Structural feature**（heading level、結尾 marker、不要 cross leak）：所有模型多少都抓到。
- **Stylistic feature**（對話 driven 敘事、篇幅精準）：差異極大、Qwen3 8B 完美、其他三個都有明顯失分。

這對應 [4.2 Agent](/llm/04-applications/agent-architecture/) 的「規劃 vs 字面 follow」差距——字面 instruction 容易、stylistic mimic 困難。寫應用時、預期 follow「形式約束」（output JSON、結尾 signature）跟 follow「風格約束」（用簡潔口吻、bullet 而非段落）兩種 instruction 的成功率不同。

### Cross-pairing leak：全 0

四個模型 cross leak 都 0——表示「不要混角色」這個 instruction 兩個都 follow 成功。可能因素：

- 角色名是名詞、模型 generation 時容易 constrain。
- Prompt 已明示「為 B 寫」、模型沒被 A 角色名干擾。

如果改成模糊 instruction（「混合 A、B 風格」）、leak 可能會出現——本實驗沒涵蓋這個 case。

### 生成時間：size ≠ 時間

四個模型的生成時間：

| 模型       | size   | 時間      |
| ---------- | ------ | --------- |
| gemma3:1b  | 815 MB | 41.8s     |
| gemma3:4b  | 3.3 GB | 36.5s     |
| qwen3:8b   | 5.2 GB | **97.5s** |
| gemma4:e4b | 9.6 GB | 43.5s     |

意外發現：

1. **1B 比 4B 慢**：因為 1B 生成 4324 字、4B 生成 1330 字、總 token 量決定總時間、不是 model size。
2. **qwen3:8b 慢 2.7×**：8B 的 forward pass 較慢、加上 generation 量級正常、總時間最長。
3. **gemma4:e4b 跟 1B 相近**：generation 短（679 字）、抵消 model 較大的開銷。

[tokens per second](/llm/knowledge-cards/tokens-per-second/) 跟 total latency 是兩件事——decode 速度快但生成太多 token、未必更快完成任務。

## 對寫應用的啟示

1. **「最新最大」≠ 「最好 follow」**：選模型實測自己 task、別只看 benchmark / size。
2. **本地小模型（< 3B）做需要 follow 結構規則的任務、要嚴格驗證**：用 structural metrics 自動 check、不要相信模型「看起來有做到」。
3. **Edge variant 可能有 special behavior**：device-deployable variant 可能 RLHF 偏向 conservative、不一定適合所有任務。
4. **跨家族對比比同家族升 size 收益大**：Qwen3 8B vs Gemma3 4B 比 Gemma3 4B vs Gemma3 1B 改善更明顯。
5. **「形式跟風格」分開驗證**：應用層的 validation 要分維度 score、不要一次評全部。

## 跑這個實驗的 framework

通用流程（不放具體 script、會綁定 corpus 內容）：

```text
1. 準備兩個資料夾、A 是風格參考、B 是 work-in-progress
2. 寫 helper script 把兩個資料夾完整內容 + 任務說明做成 prompt
3. 跑多個 model 各一次（同 prompt、不同 model）
4. 對輸出計算 structural metrics（char count、paragraph、heading、dialogue lines）
5. 跟 B 既有章節的 baseline metrics 對比
6. 列通過 / 失敗矩陣
```

關鍵設計選擇：

- **A 跟 B 風格故意不一樣**：才能驗證 LLM 是否分辨「該 follow 哪個」。
- **不評估內容品質**：純 structural 評估 reproducible、不需 reviewer 主觀判斷。
- **baseline 用既有章節算**：B 自己的 v01-v05 是「正確答案」的 reference。
- **跑多個跨家族 / 跨世代 / 跨 size 模型**：避免「只測一個就下結論」的偏差。

## 何時這份對比會過時

- **具體模型 ranking**：新模型發布後 ranking 會變、特別是新版 Gemma 4 / Qwen 4 / Llama 4 等推出時。
- **「Gemma 4 edge 表現差」這個觀察**：可能隨後續 fine-tune 或新版改善。

**不會過時的部分**：

- Model size 不是 instruction following 的唯一因素——這個現象在所有 LLM 都存在。
- Structural vs stylistic 兩層 follow 難度不同。
- 跨家族對比比同家族升 size 收益大、這個現象可能持續。
- 純 metrics-based 評估比主觀判斷可重現。
- 「自己跑一次」比「看 benchmark」更可靠的判讀邏輯。

未來想擴展、可以加入更多維度（如反向 retrieval：把生成內容當 query、看能不能找回原資料夾；或 perplexity-based 評估）。
