---
title: "Agent Loop"
date: 2026-05-12
description: "LLM agent 自我循環的工作流：LLM 規劃下一步、執行 tool、看結果、再規劃下一步、直到任務完成或停止條件觸發"
weight: 1
tags: ["llm", "knowledge-cards", "agent", "tool-use"]
---

Agent loop 的核心概念是「LLM 在 plan → act → observe → plan 的循環中推進任務、直到任務完成或停止條件觸發」，有別於一次性回答。它讓 LLM 從「單回合工具呼叫」進化成「自主執行多步驟工作」、但同時放大 [prompt injection](/llm/knowledge-cards/prompt-injection/) 的影響面跟 [tool use](/llm/knowledge-cards/tool-use/) 副作用範圍。

## 跟其他概念的關係

典型的 [agent](/llm/knowledge-cards/agent/) loop 流程：

```text
循環開始：
  step 1：LLM 看任務目標 + 當前狀態 → 規劃下一步 → 生成 tool call
  step 2：client 執行 tool call → 得到結果
  step 3：tool 結果回灌 conversation → LLM 看到新狀態
  step 4：LLM 判斷：任務完成？ → yes 結束 / no 回 step 1
循環結束。
```

Agent loop 的兩個關鍵變數：

1. **max steps**：循環最大次數、防止無限迴圈跟成本爆炸。
2. **stop condition**：什麼算「任務完成」、由 LLM 自己判斷還是有額外驗證。

常見實作（依框架而異）：LangGraph、AutoGPT、Claude 的 agentic abilities、OpenAI Assistants API 都提供 agent loop 機制。

## 判斷條件與後果

Agent loop 的成本與風險都隨圈數累積。每多跑一圈就多一次 LLM call，所以 agent 工作流的成本常比單次 LLM call 高一個量級；loop 中段讀進一段被注入指令的 tool 結果之後，後續每一步都在被改寫過的 context 上規劃，所以 agent loop 會放大 [prompt injection](/llm/knowledge-cards/prompt-injection/) 的影響。下面四個條件各自對應一種失控的形態：

1. **沒有 max steps 上限時**：stop condition 一直判成未完成，loop 就持續呼叫模型與工具，成本沒有上界。
2. **中途沒有 review checkpoint 時**：agent 偏離原意圖的那一步之後，後面的步驟都建立在偏離的狀態上，偏離要到任務結束才被發現，其間已執行的 tool call 副作用收不回來。
3. **agent 持有的 credential 涵蓋多個服務時**：一次成功的 injection 能經由這些 credential 動到每一個服務，影響範圍等於 credential 的權限範圍，跟原任務需要的範圍無關。所以 credential 只給原任務用得到的權限。
4. **tool 結果原樣拼進 prompt、沒有標記來源時**：模型分不出哪段是使用者的指令、哪段是 tool 回傳的資料，回傳內容裡的指令句較容易被當成指令執行。用「以下是 tool 回傳的資料」這類標記包覆 tool 結果，能降低觸發率，不能保證排除。

詳見 [LLM Agent Prompt Injection 後果治理](/backend/07-security-data-protection/llm-prompt-injection-in-agent/) 跟 [4.4 Agent 架構原理](/llm/04-applications/agent-architecture/)。
