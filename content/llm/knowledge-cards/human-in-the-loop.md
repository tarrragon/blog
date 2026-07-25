---
title: "Human-in-the-loop（HITL）"
date: 2026-05-14
description: "人類介入 LLM 工作流的設計：三種觸發時機（pre-act / mid-stream / post-hoc）、避免橡皮圖章化的四條件"
weight: 1
tags: ["llm", "knowledge-cards", "human-in-the-loop", "ux", "safety"]
---

Human-in-the-loop（HITL）的核心概念是「**人類在 LLM 工作流中介入的設計**」、用來在 [fuzzy](/llm/knowledge-cards/deterministic-vs-fuzzy/) AI 行為的關鍵節點插入 deterministic 人類判斷。HITL 不是「有 vs 沒有」的二元、是 spectrum：位置由 risk（副作用範圍 + 失敗代價）跟自動 validator 能力決定。

## 概念位置

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

## 設計責任

讀 AI 應用設計或 agent paper 看到「HITL」「human-in-the-loop」「approval flow」「appeal」就是這個機制。實作判讀：

1. **位置由 risk 跟 validator 能力決定**：risk 高 + validator 弱、HITL 頻率高；risk 低 + validator 強、HITL 頻率低。
2. **三時機可組合**：pre-act 擋高代價、mid-stream 處理 agent 不確定性、post-hoc 收回饋。三者各擋不同 risk class、不互斥。
3. **避免橡皮圖章化的四條件**：分級不同 risk 走不同 gate、approval UI 強制 show diff、reject 有明確 fallback、approval 訊號回饋進系統。任一不滿足、HITL 退化成形式。
4. **跟 [jagged frontier](/llm/knowledge-cards/jagged-frontier/) 的關係**：frontier 外的任務該強制 HITL、不交給 user 自由心證。
5. **跟 fuzzy engineering 典範的關係**：HITL 是 fuzzy 行為的 deterministic guardrail 一種、不是預設要有、看 risk 跟自動 validator 能力決定。

完整 HITL 拓樸設計見 [4.5 人機協作拓樸](/llm/04-applications/human-ai-collaboration/)。
