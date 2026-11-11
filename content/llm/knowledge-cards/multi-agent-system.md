---
title: "Multi-agent system"
date: 2026-05-14
description: "多個 LLM agent 協作的系統、跟 multi-call workflow 的差異在控制流跟責任邊界、三種拓樸 flat / hierarchical / agent-as-tool"
weight: 1
tags: ["llm", "knowledge-cards", "agent", "multi-agent", "architecture"]
---

Multi-agent system 的核心概念是「**多個 LLM [agent](/llm/knowledge-cards/agent/) 協作完成任務**」。跟 multi-call workflow 的差異**不在 agent 數量多寡、在控制流跟責任邊界**——multi-call 是主程式編排每 step、multi-agent 是 agent 自決下一步並可呼叫其他 agent。屬於 [agent](/llm/knowledge-cards/agent/) 概念的進一步擴展。

## 跟其他概念的關係

跟 multi-call 對照：

| 維度     | Multi-call workflow      | Multi-agent system          |
| -------- | ------------------------ | --------------------------- |
| 控制流   | 主程式編排               | Agent 自決                  |
| 角色     | Step 是函數、無「身份」  | 每個 agent 有 role / 工具集 |
| Context  | 主程式傳 context         | Agent 自帶 memory           |
| 重用     | Step 是函數、容易 import | Agent 跨系統重用透過協議    |
| 失敗歸屬 | Step 失敗、主程式接      | Agent 失敗可能 cascading    |

三種主流拓樸：

| 拓樸          | 結構                                                          | 適用                       |
| ------------- | ------------------------------------------------------------- | -------------------------- |
| Flat          | All-to-all、無 orchestrator                                   | 2-4 個 agent、動態協商     |
| Hierarchical  | Orchestrator + specialists                                    | 多專業 agent、單一對外介面 |
| Agent-as-tool | Agent 互通像 tool call（如 [MCP](/llm/knowledge-cards/mcp/)） | 跨組織重用、標準協議       |

## 判斷條件與後果

從 multi-call workflow 換到 multi-agent，換到的是 specialization gain（單一責任、獨立優化、重用、平行），付出的是 orchestration overhead（context 重複傳遞、latency 累積、debug 困難、責任歸屬模糊）。specialization gain 大過 orchestration overhead 的條件是任務本身帶著這幾種訊號：各 role 的差異顯著、agent 要跨產品重用、子任務真正平行、協作的順序要在執行時動態決定，而且團隊熟悉這套做法；這些訊號不成立時，multi-call 由主程式編排每一步就做得到同樣的事，多出來的只有 overhead。

換成 multi-agent 之後，控制流交給 agent 自決，主程式不再逐步看得到每一步（〈跟其他概念的關係〉的 multi-call 對照表），系統因此多出特有的失敗模式：循環依賴、責任歸屬模糊、context 重複傳遞、orchestrator 單點瓶頸、agent 互相 hallucinate。各類各有對應的 guardrail：call stack 監測、trace 全紀錄、shared context、deterministic dispatch rule、schema validation。用 agent-as-tool 拓樸時，agent 可以包成 [MCP](/llm/knowledge-cards/mcp/) server 暴露，其他組織經由 MCP 的 tool 介面重用它。

完整 multi-agent 拓樸設計見 [4.8 Multi-Agent 拓樸](/llm/04-applications/multi-agent-topology/)。
