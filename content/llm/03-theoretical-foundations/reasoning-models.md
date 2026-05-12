---
title: "3.8 Reasoning models：test-time compute paradigm"
date: 2026-05-12
description: "Chain-of-thought 從 prompting 技巧演化成訓練 paradigm、reasoning model 的內部運作、本地可跑的選項與適用任務"
tags: ["llm", "theory", "reasoning", "chain-of-thought", "test-time-compute"]
weight: 8
---

[Reasoning model](/llm/knowledge-cards/reasoning-model/) 把「LLM 該想多久」從固定的 forward pass 數變成**可訓練、可在推論時動態擴展**的維度。OpenAI o1（2024 年底）跟 DeepSeek-R1（2025 年初）是這條路線的兩個里程碑、後續 Qwen-QwQ、Claude thinking、Gemini thinking 等都跟上。本章把 reasoning model 的訓練原理、推論行為、本地可跑選項、適用 / 不適用任務拆成可操作的判讀。

本章不重複 [chain-of-thought](/llm/knowledge-cards/chain-of-thought/) 跟 [test-time compute](/llm/knowledge-cards/test-time-compute/) 卡片的定義、聚焦「reasoning model 怎麼運作、怎麼跟本地工作流結合」。

## 本章目標

讀完本章後、你應該能：

1. 解釋「reasoning model」相對 instruct model 的訓練差異。
2. 看到 `<think>...</think>` 標記或「extended thinking」field 時、知道是 reasoning trace、怎麼解讀。
3. 判斷一個任務該用 reasoning model 還是 instruct model。
4. 對自己的硬體預算估算「能不能本地跑 reasoning model」、選哪個。

## Paradigm shift：從 scaling pretrain 到 scaling test-time

LLM 能力提升的兩條歷史路徑：

```text
2020-2023 時期：scale pretrain compute
  GPT-3 → GPT-4：模型大 5-10×、訓練 compute 大 50-100×
  策略：更多參數 + 更多訓練 token = 更好的 base model

2024-2026 時期：scale test-time compute
  GPT-4 → o1：模型大小接近、但推論時花 5-50× 算力
  策略：base model 不變、訓練「推理能力」+ 推論時動態擴展 reasoning trace
```

兩條路線**不對立**、是疊加：reasoning model 本身仍跑在大 base model 上、reasoning RL 是再加一層後訓練。Cost trade-off 對比的 framing 跟對使用者錢包的影響、見 [test-time compute 卡片](/llm/knowledge-cards/test-time-compute/)。本章接下來聚焦「reasoning model 的訓練流程」跟「本地選型」、不重複 paradigm 層的對比。

關鍵理解：reasoning model 不是「更聰明的 GPT-4」、是「同等聰明 base model + 學會把算力花在 reasoning 上」。底層 base model 依然是 Transformer、所有前面章節（attention、FFN、sampling）原理不變。

## Reasoning model 的訓練流程

DeepSeek-R1 是第一個公開細節的開源 reasoning model、其 paper 揭示的訓練流程具有代表性：

```text
Stage 1: Cold-start SFT
  用幾千份「高品質 long reasoning trace」資料 fine-tune base model
  目標：讓模型學會「該怎麼想」的 format

Stage 2: Reasoning-focused RL
  Reward：最終答案正確（math / code / logic 等可機械驗證的任務）
  Policy：把 reasoning trace 越拉越長、越能正確、reward 越高
  約束：保留語言流暢度（不能 reasoning trace 變成亂碼）
  → 模型自發學會「困難問題想更久」

Stage 3: SFT on reasoning + non-reasoning data
  把 reasoning RL 學到的能力跟一般 instruct 能力 mix
  避免「只會 reasoning、不會聊天」

Stage 4: Final RLHF / DPO（可選）
  跟 instruct model 同樣的 alignment 階段、refine helpfulness
```

關鍵特性：

1. **Stage 2 的 reward 機械可驗證**：math 答案、code unit test、logic 答案 — 不需要 human preference、所以可大量擴展訓練資料
2. **Reasoning trace 是「emerge」出來的**：訓練不直接告訴模型「該怎麼想」、只給「答案對不對」、模型自己摸索出最佳 reasoning strategy
3. **跨任務 transfer 有限**：reasoning model 在訓練分佈內任務（math、coding）強、跨到開放域對話、提升較小

[DeepSeek-R1 distill 系列](/llm/knowledge-cards/reasoning-model/) 是另一條路：用 R1 full 模型產生 reasoning trace、再 SFT 一個小 base model（如 Qwen2.5-32B）— 讓較小模型也有 reasoning 能力、但跳過昂貴的 RL 階段。

## Reasoning trace 的格式

主流 reasoning model 在推論時輸出 reasoning trace 的格式：

```text
DeepSeek-R1 / Qwen-QwQ：用特殊 token 標記
  <think>
  讓我先列出已知條件...先試 case 1...結果矛盾、改試 case 2...
  </think>
  最終答案：X

OpenAI o1：對使用者隱藏
  API 只回最終答案、但計費 reasoning token
  使用者看不到 reasoning trace 內容

Claude 3.7 thinking：extended thinking field
  API response 含 `extended_thinking` 跟 `text` 兩個 field
  IDE / chat 介面通常折疊顯示 thinking 內容
```

實作層的關鍵考量：

1. **Tokenizer 對 reasoning token 的處理**：`<think>` 等特殊 token 在 vocab 中被保留、tokenizer 識別後不切碎
2. **Context budget 分配**：reasoning trace 通常 1000-10000 token、要預留 [context window](/llm/knowledge-cards/context-window/) 容量
3. **Streaming 行為**：reasoning trace streaming 時、使用者看到「模型在想」、TTFT 變短但「first useful output」變長
4. **Stop sequence**：sampling 階段 `</think>` 或對應結束 token 是 reasoning trace 的 terminator

## 本地可跑的 reasoning model

2026/5 時、本地寫 code 工作流可考慮的 reasoning model：

| 模型                         | 大小        | Q4 量化後記憶體 | 適合硬體               | reasoning trace 平均 token |
| ---------------------------- | ----------- | --------------- | ---------------------- | -------------------------- |
| DeepSeek-R1-Distill-Qwen-7B  | 7B          | ~4 GB           | 16GB+ Mac / 16GB+ VRAM | 500-2000                   |
| DeepSeek-R1-Distill-Qwen-14B | 14B         | ~8 GB           | 24GB+ Mac / 16GB+ VRAM | 1000-3000                  |
| DeepSeek-R1-Distill-Qwen-32B | 32B         | ~18 GB          | 32GB+ Mac / 24GB+ VRAM | 1500-5000                  |
| QwQ-32B                      | 32B         | ~18 GB          | 32GB+ Mac / 24GB+ VRAM | 2000-8000                  |
| DeepSeek-R1（full）          | 671B（MoE） | ~140 GB         | 不實際本地跑           | 5000-30000                 |

> **事實查核註**：模型大小、量化體積、reasoning trace 長度是 2026/5 主流版本的常見數量級；具體數字隨量化等級、context 配置、任務類型而變、引用前以對應 model card 跟自己 `llama-bench` 跑為準。

選型判讀（個人 dev 場景）：

1. **24GB Mac（M4 Pro）**：可跑 14B distill、或 32B distill Q4 緊張、context 開小
2. **32GB Mac（M4 Pro 升級）**：跑 32B distill 舒服、context 32K+ 可開
3. **48GB+ Mac（M4 Max）**：跑 32B distill 寬鬆、可考慮 QwQ-32B 配 64K context
4. **16GB+ VRAM PC**：跑 14B distill；32B distill 屬 dense 架構（不是 MoE）、要用 dense CPU offload（部分層放 RAM、靠 PCIe 走、tok/s 受 PCIe 頻寬限制）、跟 [MoE CPU offload](/llm/knowledge-cards/moe-cpu-offload/) 是不同的戰術
5. **24GB+ VRAM PC（5090）**：跑 32B distill 寬鬆

## 適合 reasoning model 的任務

Reasoning model 的優勢任務有明確 pattern：

| 任務類型                 | 為什麼適合                       | 案例                                             |
| ------------------------ | -------------------------------- | ------------------------------------------------ |
| 複雜 algorithm design    | 需要多步推理 + 探索多個解法      | Leetcode hard、設計 sliding window 解法          |
| 棘手 debug               | 需要排除多種可能、追蹤跨檔案邏輯 | 「為什麼這個 race condition 偶爾出現」           |
| Math / 量化分析          | 機械可驗證、模型訓練分佈內       | 估算系統 capacity、複雜利率計算                  |
| Multi-step refactor 規劃 | 需要看到整體影響、分階段         | 「把這個 service 拆成 3 個 microservice 的步驟」 |
| 系統設計取捨             | 多 dimension 比較、需要展開論證  | 「DB 該選 Postgres 還是 Cassandra」              |
| 解 obscure error         | 需要 reason about 多個可能根因   | 「kernel panic 訊息 X 可能來源」                 |

不適合用 reasoning model 的任務（用 instruct model 即可）：

| 任務類型                 | 為什麼不適合                               | 改用                                 |
| ------------------------ | ------------------------------------------ | ------------------------------------ |
| Autocomplete             | reasoning trace 拉長 TTFT、體感變慢        | Instruct 小模型（如 Qwen3-Coder-7B） |
| 簡單 docstring / comment | 過度推理、浪費 token                       | Instruct model                       |
| 純翻譯 / 風格改寫        | 不需要 reasoning                           | Instruct model                       |
| 高頻短查詢               | 每次 reasoning overhead 累積               | Instruct model + KV cache            |
| 已知答案的查表           | reasoning 反而引入錯誤                     | Instruct model                       |
| 探索性 brainstorming     | 不需要「正確答案」、reasoning 反而限制創意 | Instruct model + 高 temperature      |

判讀反射：先問「這任務有沒有客觀正確答案 + 是否需要多步推理」、兩者都 yes 才用 reasoning model。

## Reasoning model + tool use

Reasoning model 跟 [tool use](/llm/knowledge-cards/tool-use/) 結合是 2026 新趨勢、典型形態：

```text
模型在 reasoning trace 中發現「需要驗證一個事實」
  ↓
呼叫 tool（calculator / web search / code interpreter）
  ↓
拿到結果、繼續 reasoning
  ↓
最終答案
```

代表場景：

1. **Coding agent + reasoning**：reasoning 階段規劃 refactor 步驟、tool use 階段執行 file edit、reasoning 階段檢查結果
2. **Math / data analysis**：reasoning 階段拆問題、code interpreter 跑 calculation、reasoning 階段解讀
3. **Web 研究**：reasoning 階段列出該查的事實、web search、reasoning 階段彙整

挑戰：

1. **Reasoning trace + tool result 都進 context**：context 用量爆炸快、需要 long context 模型（見 [4.7 Long context engineering](/llm/04-applications/long-context-engineering/)）
2. **Tool use 訓練跟 reasoning 訓練是兩件事**：本地 distill 模型 tool use 能力 = 對應 base model 的 tool use 能力、不一定強
3. **Error recovery**：reasoning 階段假設錯了、tool 回 error、模型要會 backtrack（[agent loop](/llm/knowledge-cards/agent-loop/) 失敗模式）

實務上、本地 reasoning + agent 是「值得試、但仍處早期」階段；雲端 R1 / o3 / Claude thinking + Claude Code / Cursor 是現階段更穩的組合。

## 跟 instruct model 共存的混用策略

寫 code 場景的合理混用配置：

```text
Default model（Continue.dev primary）：instruct model
  Qwen3-Coder-30B-Instruct / Gemma 4 31B Instruct
  日常 autocomplete、解釋、簡單 refactor

Reasoning model（Continue.dev secondary、手動切）：local reasoning
  DeepSeek-R1-Distill-Qwen-32B / QwQ-32B
  困難 bug、algorithm、複雜 refactor 規劃

Cloud fallback（手動切）：雲端旗艦
  Claude 3.7 Sonnet thinking / GPT-5 / o3
  本地 reasoning 卡住、或極困難任務
```

Continue.dev 的 multi-model config 可同時設多個、UI 下拉切換、不用重啟 server。安全 / 隱私面：reasoning trace 可能含敏感推理過程、跨雲端 / 本地邊界判讀同 [6.4](/llm/06-security/cross-cloud-local-data-boundary/)。

## 何時過時 / 何時不過時

**不會過時的部分**：

- Test-time compute 作為一個獨立 scaling 維度的概念
- Reasoning trace 結構（pre-answer reasoning + answer）
- 「適合 reasoning vs instruct」的判讀框架
- 「機械可驗證的 reward + RL」是 reasoning training 的核心
- Reasoning model + tool use 的設計取捨

**會變的部分**：

- 具體 reasoning model（R1 → R2 → ...、o1 → o3 → ...、會持續迭代）
- Reasoning trace 的具體格式（`<think>`、extended thinking field、未來可能標準化）
- 本地可跑的模型選項（distill 系列會持續更新）
- Reasoning 跟 agent 結合的最佳實踐（仍在演化）
- 是否會出現 reasoning paradigm 的下一個替代（如 neurosymbolic、multi-agent reasoning）

新 reasoning model 出來時、回到本章的 framing：訓練流程是否同 R1 pattern、reasoning trace 怎麼產出、本地能否跑、適用任務是否同樣 pattern — 多數新模型仍會 fit 進這個框架。

## 小結

Reasoning model 把 LLM 能力提升的軸從「scale pretrain」延伸到「scale test-time compute」、是 2024-2026 最大的 paradigm shift。訓練流程靠機械可驗證的 reward + RL 教模型「該想多久」、推論時動態擴展 reasoning trace。本地可跑 distill 系列（7B-32B）、對應任務是 math / debug / algorithm / 複雜 refactor 等需要多步推理的場景；簡單任務仍用 instruct model。Reasoning + tool use 的組合是新趨勢、但本地仍處早期。

下一章：[3.9 Speculative decoding 內部](/llm/03-theoretical-foundations/speculative-decoding-internals/)、看另一個推論時加速的技術細節。
