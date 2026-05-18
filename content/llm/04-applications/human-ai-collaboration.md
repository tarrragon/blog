---
title: "4.5 人機協作拓樸：何時人介入、怎麼介入"
date: 2026-05-14
description: "Centaur vs Cyborg 工作模式、jagged frontier、HITL 三種觸發時機（pre-act / mid-stream / post-hoc）、確認流程的設計避免橡皮圖章化"
tags: ["llm", "applications", "human-in-the-loop", "collaboration", "ux"]
weight: 5
---

[HITL（human-in-the-loop）](/llm/knowledge-cards/human-in-the-loop/) 設計的本質是**在「人類介入頻率」spectrum 上選位置**——位置由 risk（副作用範圍 + 失敗代價）跟自動 validator 能力決定。risk 高 + validator 弱、人類介入頻率高；risk 低 + validator 強、人類介入頻率低。落點選錯就會出兩種事故：自動化過度跑 production migration 是 over-trust、每個 tool call 都要 approval 是 under-trust。

本章寫人機協作的拓樸設計：兩種工作模式（centaur / cyborg）、能力邊界的不規則性（jagged frontier）、三種 HITL 觸發時機、跟 [4.4 agent 自主度分層](/llm/04-applications/agent-architecture/) 的對應。這層問題是跨產品 / 跨領域通用、跟具體 framework 無關。

## 本章目標

讀完本章後你能：

1. 區分 centaur 跟 cyborg 兩種工作模式、判斷哪種適合哪種任務。
2. 描述 jagged frontier、解釋為什麼「全自動」是錯題。
3. 在 pre-act / mid-stream / post-hoc 三個時機點選對 HITL 設計。
4. 設計確認流程、避免人類變橡皮圖章。
5. 把這層設計對應回 [4.4 agent 架構](/llm/04-applications/agent-architecture/) 的自主度分層。

## 兩種工作模式：Centaur 跟 Cyborg

Centaur 跟 cyborg 是兩種人類跟 LLM 共事的姿態。概念起源於 Kasparov 2010 提的 advanced chess（人類 + AI 配合下棋）、HBS / UPenn / Wharton 對 BCG 顧問使用 AI 的研究把這對 framing 套到 knowledge work、觀察到兩種使用模式都存在且各有適用。

### Centaur 模式

人類把整段任務委派給 LLM、等結果回來再審。

- **比喻**：人馬獸——上半身人、下半身馬、清楚的職責分工。
- **典型場景**：「寫一份這個主題的 PPT 大綱、含三個案例、按以下風格、做完給我」、LLM 跑幾分鐘、人類審結果。
- **適合**：任務邊界清楚、人類能事先描述完整需求、結果可離線審。
- **失敗模式**：任務描述漏細節、LLM 跑偏到沒注意、結果不能用。緩解：先給小範圍試跑、確認方向再放手。

### Cyborg 模式

人類跟 LLM 緊密協作、快速來回、人類隨時調整方向。

- **比喻**：半機械人——人類跟 LLM 融合、邊做邊改。
- **典型場景**：寫 code 時 IDE 內 inline completion、寫文章時邊輸入邊看 LLM 建議、debug 時來回問。
- **適合**：任務探索性、需求邊做邊浮現、無法事先完整描述。
- **失敗模式**：頻繁打斷思路、context switch 成本高、最後產出反而比 centaur 慢。緩解：對熟悉的任務 cyborg、不熟的任務 centaur。

### 該用哪種

| 任務性質                     | 預設模式            |
| ---------------------------- | ------------------- |
| 邊界清楚、需求可事先描述完整 | Centaur             |
| 探索性、邊做邊定義           | Cyborg              |
| 大量重複（如 100 篇文章）    | Centaur             |
| 創意 / 設計、要看回饋微調    | Cyborg              |
| 高代價、要 rollback 控制     | Centaur + 強 review |

學生 / 個人開發更常 cyborg 工作、企業自動化更常 centaur 工作。看到一個產品設計時、問「它鼓勵 user 走 centaur 還是 cyborg」、就能判讀它的設計取向。

## Jagged Frontier：AI 能力的不規則邊界

[Jagged frontier](/llm/knowledge-cards/jagged-frontier/) 是觀察 AI 能力分佈的 framing。直覺上「AI 能做的任務」應該是一個 smooth 的連續區、簡單的能做、難的不能。實際上不是——AI 能做的任務分佈是**鋸齒狀（jagged）**：某些看起來難的任務 AI 做得很好、某些看起來簡單的任務 AI 反而做不好。

| 看起來簡單但 AI 容易壞 | 看起來複雜但 AI 做得好    |
| ---------------------- | ------------------------- |
| 精確算術               | 寫一段風格指定的程式碼    |
| 計數（這段有幾個字）   | 翻譯複雜技術文章          |
| 嚴格遵守冷僻格式       | 從一段文字抽取關鍵 entity |
| 引用真實的 URL         | 解釋複雜概念              |

這張表是 2024-2025 的觀察、**frontier 會隨模型升級漂移**——reasoning model + tool use 普及後、算術跟計數已經部分往「能做」那邊移、URL 也可以靠 web search tool 補救。表的價值在於 framing「能力分佈不規則」、不是把具體 4 個 case 當定論。

每個例子背後的失敗機制各不相同：

- **精確算術**：靠符號操作、訓練資料中算術佔比小、tokenizer 把數字切成多 token 也加難度。Tool use（呼叫 calculator）能補救。
- **計數**：要對 input 做精確 traversal、跟 LLM 的並行 [attention](/llm/knowledge-cards/attention/) 機制不對盤、容易少算多算。對 needle in long context 的失敗模式類比見 [needle in haystack](/llm/knowledge-cards/needle-in-haystack/) 卡。
- **嚴格遵守冷僻格式**：format 沒在訓練分佈中見過、模型回退到「我熟悉的格式」。Constrained decoding（見 [3.10](/llm/03-theoretical-foundations/constrained-decoding-internals/)）能補救。
- **引用真實 URL**：模型沒辦法區分「真實存在」跟「看起來合理」、[hallucinate](/llm/knowledge-cards/hallucination/) 出格式對但內容假的 URL。靠 tool（web search、URL validator）才能驗證。

整體看：能力分佈跟訓練資料分佈、tokenizer 行為、推論機制相關、跟人類直覺的「難易」沒對齊。這給三個實務啟示：

- **不要用「人類直覺難易」推測 AI 能力**。試跑、看結果、不要預判。
- **「全自動」是 over-trust 假設**：frontier 鋸齒、總有些子任務落在 frontier 外、需要人介入或 tool 補。設計時要假設「有部分子任務 AI 會失敗」、而不是「都會成功」。
- **失敗在 frontier 外的任務、再加 prompt iteration 通常無效**：那是模型能力邊界問題、不是 prompt 問題。對應 [4.0 prompt 技術光譜](/llm/04-applications/prompt-techniques-landscape/) 的 systematic vs random error 診斷。

### Falling asleep at the wheel：frontier 外的隱性風險

研究發現一個跟 jagged frontier 互動的人類行為模式：**人類傾向不分辨任務是否在 frontier 內、對 AI 結果一律低度審查**。結果 frontier 內的任務 AI 做得好、人類審不審差別不大；frontier 外的任務 AI 做得差、但人類也沒審出來、產出帶錯送出。

緩解：

- **明確標 frontier**：對團隊 / 產品 user 標出「AI 在這類任務可靠 / 不可靠」、不要假設 user 會自己分辨。
- **frontier 外的任務強制人類審查**：把「該審 vs 不該審」做成 deterministic 規則、不交給 user 自由心證。
- **抽樣審查**：即使 frontier 內任務、隨機抽樣審查、偵測 frontier 漂移（模型升級或 prompt 變動後 frontier 可能移動）。

## HITL 三種觸發時機

人類介入的時機決定 HITL 的型態。三個時機點各有適用場景：

### Pre-act：動作執行前確認

LLM 決定要做某個 action、但 action 真的執行前停下來、給人類審 + approve。

```text
LLM decides: 「我要刪除 user_id=123 的 record」
   ↓
[HUMAN APPROVE?]
   ↓ (approved)
Execute deletion
```

- **適用**：不可逆 / 高代價的 action。對應 [4.4 agent](/llm/04-applications/agent-architecture/) 的「step-by-step approval」協作模型。
- **失敗模式**：approval 流程太頻繁、人類疲勞、最後變橡皮圖章。緩解見後面「避免橡皮圖章化」段。

### Mid-stream：執行過程中介入

Agent loop 跑到一半、發現自己不確定、主動停下來問人類。

```text
Agent: 「我有兩個方案、不確定哪個、請選 A 還是 B？」
   ↓
[HUMAN PICKS]
   ↓
Agent continues with chosen path
```

- **適用**：任務有多個合理路徑、選擇影響後續策略、不該由 agent 自決。
- **跟 pre-act 的差異**：pre-act 是「我準備做 X、你 approve 嗎」（agent 已決定方向）、mid-stream 是「我不確定該做什麼、你決定」（決策權交給人類）。
- **失敗模式**：agent 不知道自己該不知道（unknown unknowns）、該問沒問、自己亂走。緩解：在 prompt 內 enumerate 常見的「該問人類」情境、降低 agent 自決的範圍。

### Post-hoc：事後申訴 / 校正

Agent 已執行、結果交付、user 看完後可以申訴 / 校正。

```text
Agent produces result → User sees result
                              ↓
                       [USER APPEALS?]
                              ↓ (yes)
                       Human reviews + adjusts
                              ↓
                       Feedback loop → 改 prompt / fine-tune
```

- **適用**：行為層次的細節調整、評分類任務（如自動打分後 user 申訴）、預先審不可行的場景。
- **跟 pre/mid 的差異**：post-hoc 不擋執行流、執行完才介入；前兩者擋在執行前 / 執行中。
- **典型例子**：自動評分系統的 appeal 流程——LLM 打分完、user 對分數有異議時、走人類審查、結果不只改這次分數、還回饋進系統改善後續評分。
- **失敗模式**：appeal rate 過高（系統信任度差）、或 appeal rate 過低（user 不知道可以申訴 / 申訴成本高）、回饋訊號失真。

### 三個時機的選擇

| 時機       | 適合任務                         | 不適合                           |
| ---------- | -------------------------------- | -------------------------------- |
| Pre-act    | 高代價、不可逆、副作用範圍大     | 高頻率動作（會把人類淹死）       |
| Mid-stream | 路徑分歧、需要 domain judgment   | 路徑可由 agent 自決的低代價任務  |
| Post-hoc   | 評分 / 評估、低代價、user 數量大 | 不可逆動作（事後 appeal 來不及） |

實務多重組合：pre-act 擋高代價、mid-stream 處理 agent 的不確定性、post-hoc 收 user 回饋改善系統。**三者各自處理不同 risk class、不互斥**。

## 有效 HITL 的四個設計條件

HITL 要真的擋住失敗、不退化成 rubber-stamp approval、設計上要滿足四個條件。每個條件對應一個常見退化模式、可以同時當 checklist 用。

### 條件一：分級、不同 risk 走不同 gate

高 risk 動作（push、deploy、production change）強制 step-by-step approval；中等 risk（檔案寫入、本機 commit）每 N 步 checkpoint；低 risk（read-only、本機 sandbox）full auto。對應 [4.3 tool use 副作用範圍](/llm/04-applications/tool-use-principles/) 的等級分類。

對應反例：每個 tool call 都要 approve、不分高低代價、user 每天按 100 次 approve、按到下意識、根本沒看內容。

### 條件二：approval UI 強制 show diff

審查的具體內容（準備寫的檔案內容、準備執行的 SQL、準備發的 email 草稿）必須在 approval UI 上呈現、user 看得到才能做出有意義的判斷。

對應反例：「approve this action?」按鈕、但 user 看不到 action 的具體內容、只能盲簽。沒有 diff 就沒有審查、不要假裝有審查。

### 條件三：reject 有明確 fallback 路徑

User reject 後 agent 該怎麼處理（換方案、停下來、escalate）要在設計時確定、不能讓「reject 等同流程斷」。

對應反例：只能 approve、reject 的話 agent 不知道怎麼辦、user 怕 reject 後續流程斷、就一律按 approve、HITL 失去意義。

### 條件四：approval 訊號要回饋進系統

User 的 approve / reject pattern 進 trace、定期 analyze、把「總是 approve 的動作」自動降級、「總是 reject 的動作」進 prompt 改變 agent 預設行為。

對應反例：User 一直 approve / reject、但訊號沒回饋、agent 下次還是問一樣的問題、user 疲勞累積。

## 跟 Agent 自主度分層的對應

[4.4 agent 架構](/llm/04-applications/agent-architecture/) 列了五種人類審查協作模型：full auto、checkpoint、step-by-step approval、plan first then auto、human-in-the-loop。本章三種 HITL 時機跟這五種協作模型的對應：

| Agent 自主度分層                | 主要 HITL 時機                 | 設計重點                                       |
| ------------------------------- | ------------------------------ | ---------------------------------------------- |
| Full auto                       | Post-hoc                       | Appeal 流程、抽樣審查、distribution monitoring |
| Checkpoint                      | Pre-act（每 N 步）             | 分級 approval、diff 必須 show                  |
| Step-by-step approval           | Pre-act（每步）                | UI 簡潔、reject 路徑清楚、避免疲勞             |
| Plan first, then auto           | Pre-act（plan 階段）+ Post-hoc | Plan diff + 執行後審查                         |
| Human-in-the-loop（mid-stream） | Mid-stream                     | Agent 知道自己該問人類、不該問的事不問         |

選哪一層、看 [4.3 工具副作用範圍](/llm/04-applications/tool-use-principles/) 等級：等級 1-2 用 full auto + post-hoc、等級 3 用 checkpoint、等級 4-5 強制 step-by-step。

## 跟 Fuzzy Engineering 典範的關係

[0.8 Deterministic vs Fuzzy Engineering](/llm/00-foundations/deterministic-vs-fuzzy-engineering/) 講 fuzzy 邊界要包 deterministic guardrail。HITL 是 guardrail 的一個 case——把人類判斷當成 deterministic check 來包 fuzzy LLM 行為。

判讀 HITL 該存在的訊號：

- 任務的 fuzzy 行為輸出進入不可逆 deterministic 系統（DB write、API call、實體 action）。
- LLM 在這類 boundary 上的失敗代價遠高於 HITL 的人類 cost。
- 沒有可靠的自動 validator（用 LLM judge 風險也太高）。

三者俱備時、HITL 是必要的 guardrail。任一不滿足、可能用 schema validation / output validator / distribution monitoring 替代、不需要人類在 loop 內。

## 何時過時 / 何時不過時

**不會過時的部分**：

- Centaur vs cyborg 兩種工作模式的分類。
- Jagged frontier 概念、「全自動」是錯題的論證。
- 三種 HITL 觸發時機（pre-act / mid-stream / post-hoc）的分類。
- 橡皮圖章化的四個反模式跟緩解。
- 跟 agent 自主度分層、fuzzy engineering 典範的對應結構。

**會變的部分**：

- Jagged frontier 的具體位置（哪些任務在 frontier 內、隨模型能力進步會移動）。
- HITL 的 UI / UX 工具（隨產品 framework 演化）。
- Approval 自動化的程度（更強的 distribution monitoring 可能讓部分 HITL 變得不必要）。

## 小結

人機協作不是「人類監督 AI」這麼單一、是 spectrum：centaur 委派 / cyborg 共事兩種姿態、jagged frontier 決定 AI 哪些能放手、HITL 三個時機（pre-act / mid-stream / post-hoc）各擋不同 risk class、橡皮圖章化是最常見的失敗模式。設計反射動作：先看 [4.3 副作用範圍](/llm/04-applications/tool-use-principles/) 等級、對應到 [4.4 自主度分層](/llm/04-applications/agent-architecture/)、再選 HITL 時機跟確認流程。HITL 是 [0.8 fuzzy engineering](/llm/00-foundations/deterministic-vs-fuzzy-engineering/) guardrail 的一種、不是預設要有、看 risk 跟自動 validator 能力決定。

下一章：[4.6 應用層協議](/llm/04-applications/application-protocols/)、把 function calling / structured output / MCP 三個概念放回正確層級、銜接 agent 跟外部系統的協議設計。Agent 自主度分層完整討論見 [4.4](/llm/04-applications/agent-architecture/)、工具副作用範圍見 [4.3](/llm/04-applications/tool-use-principles/)、HITL 在 fuzzy engineering 中的定位見 [0.8](/llm/00-foundations/deterministic-vs-fuzzy-engineering/)。
