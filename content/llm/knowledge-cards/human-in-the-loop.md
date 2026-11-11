---
title: "Human-in-the-loop（HITL）"
date: 2026-05-14
description: "人類介入 LLM 工作流的設計：三種觸發時機（pre-act / mid-stream / post-hoc）、避免橡皮圖章化的四條件"
weight: 1
tags: ["llm", "knowledge-cards", "human-in-the-loop", "ux", "safety"]
---

Human-in-the-loop（HITL）的核心概念是「**人類在 LLM 工作流中介入的設計**」、用來在 [fuzzy](/llm/knowledge-cards/deterministic-vs-fuzzy/) AI 行為的關鍵節點插入 deterministic 人類判斷。HITL 不是「有 vs 沒有」的二元、是 spectrum：位置由 risk（副作用範圍 + 失敗代價）跟自動 validator 能力決定。

## 跟其他概念的關係

HITL 三種觸發時機：

| 時機       | 介入點                      | 適合任務                            |
| ---------- | --------------------------- | ----------------------------------- |
| Pre-act    | Action 執行前確認           | 不可逆 / 高代價（DB write、deploy） |
| Mid-stream | Agent 過程中遇不確定主動問  | 路徑分歧、需要 domain judgment      |
| Post-hoc   | 結果交付後 user 申訴 / 校正 | 評分類、低代價、user 數量大         |

跟其他相關概念對照：

| 概念                                         | 跟 HITL 的關係                                                          |
| -------------------------------------------- | ----------------------------------------------------------------------- |
| Agent 自主度分層                             | Full auto / checkpoint / step-by-step / plan-first → 對應 HITL 時機     |
| Tool 副作用範圍                              | 等級 1-2 不需 HITL、等級 4-5 強制 HITL                                  |
| [Guardrail](/llm/knowledge-cards/guardrail/) | Schema / validator / monitoring 是自動 guardrail、HITL 是人類 guardrail |

## 判斷條件與後果

HITL 的設計看兩個條件：動作的風險（副作用範圍與失敗代價），以及自動 validator 擋得下多少錯。

1. **風險高而 validator 弱時**，錯誤只有人看得出來，人工介入的頻率高才擋得住；風險低而 validator 強時，多數錯誤已被 validator 擋下，再加人工審查只多出延遲與人力成本。
2. **三個時機各自擋一類風險**：pre-act 在動作執行前擋下高代價的動作，mid-stream 在 agent 遇到不確定時交給人決定，post-hoc 在交付之後收集申訴與校正。三者不互斥，同一個系統可以同時有。
3. **出現下面任一情形時，approval 退化成形式**：所有風險走同一道 gate，高風險請求混在大量低風險請求裡沒有被區分；approval UI 不顯示 diff，審查的人看不到要批准的內容；reject 之後沒有定義的 fallback，拒絕的結果是流程停住；approval 的結果沒有回饋進系統，同一類錯誤下一次照樣送來審。
4. **任務位於 [jagged frontier](/llm/knowledge-cards/jagged-frontier/) 外時**，模型失敗的機率高，而失敗的輸出看起來一樣合理，交給使用者自行決定是否審查，錯誤是否被擋下取決於使用者是否察覺；所以 frontier 外的任務強制走 HITL。
5. HITL 是 fuzzy 行為外層的一種 deterministic guardrail，是否需要由第一項的兩個條件決定。

完整 HITL 拓樸設計見 [4.5 人機協作拓樸](/llm/04-applications/human-ai-collaboration/)。
