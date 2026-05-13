---
title: "Multi-agent system"
date: 2026-05-14
description: "多個 LLM agent 協作的系統、跟 multi-call workflow 的差異在控制流跟責任邊界、三種拓樸 flat / hierarchical / agent-as-tool"
weight: 1
tags: ["llm", "knowledge-cards", "agent", "multi-agent", "architecture"]
---

Multi-agent system 的核心概念是「**多個 LLM [agent](/llm/knowledge-cards/agent/) 協作完成任務**」。跟 multi-call workflow 的差異**不在 agent 數量多寡、在控制流跟責任邊界**——multi-call 是主程式編排每 step、multi-agent 是 agent 自決下一步並可呼叫其他 agent。屬於 [agent](/llm/knowledge-cards/agent/) 概念的進一步擴展。

## 概念位置

跟 multi-call 對照：

| 維度       | Multi-call workflow                  | Multi-agent system                          |
| ---------- | ------------------------------------ | ------------------------------------------- |
| 控制流     | 主程式編排                           | Agent 自決                                  |
| 角色       | Step 是函數、無「身份」              | 每個 agent 有 role / 工具集                 |
| Context    | 主程式傳 context                     | Agent 自帶 memory                           |
| 重用       | Step 是函數、容易 import             | Agent 跨系統重用透過協議                    |
| 失敗歸屬   | Step 失敗、主程式接                  | Agent 失敗可能 cascading                    |

三種主流拓樸：

| 拓樸           | 結構                              | 適用                                    |
| -------------- | --------------------------------- | --------------------------------------- |
| Flat           | All-to-all、無 orchestrator       | 2-4 個 agent、動態協商                  |
| Hierarchical   | Orchestrator + specialists        | 多專業 agent、單一對外介面              |
| Agent-as-tool  | Agent 互通像 tool call（如 MCP）  | 跨組織重用、標準協議                    |

## 設計責任

讀 agent framework / paper 看到「multi-agent」「orchestrator」「agent-as-tool」就是這層設計。實作判讀：

1. **「先 multi-call、不夠再 multi-agent」**：multi-agent 是「特定問題的解法」、不是「更高級的設計」。判讀訊號：role 顯著差異 / 跨產品重用 / 真正平行 / 動態協作 / 團隊熟悉度——四條件全滿足才走 multi-agent。
2. **Specialization gain vs orchestration overhead**：拆細帶來單一責任、獨立優化、重用、平行；代價是 context 重複傳遞、latency 累積、debug 困難、責任歸屬模糊。
3. **特有失敗模式**：循環依賴、責任歸屬模糊、context 重複傳遞、orchestrator 單點瓶頸、agent 互相 hallucinate。每類有對應 guardrail（call stack 監測、trace 全紀錄、shared context、deterministic dispatch rule、schema validation）。
4. **跟 [MCP](/llm/knowledge-cards/mcp/) 的關係**：MCP 的 tool primitive 視角下、agent-as-tool 可包成 MCP server 暴露、跨組織重用走這條路。

完整 multi-agent 拓樸設計見 [4.8 Multi-Agent 拓樸](/llm/04-applications/multi-agent-topology/)。
