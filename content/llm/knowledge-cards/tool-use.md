---
title: "Tool Use"
date: 2026-05-12
description: "LLM 透過結構化呼叫外部工具（讀檔、查資料庫、發 API request）來擴展能力的設計、function calling 跟 MCP 是常見實作"
weight: 1
tags: ["llm", "knowledge-cards", "application", "agent"]
---

Tool use 的核心概念是「LLM 不只生成文字、還能透過結構化呼叫外部工具來執行讀檔、查資料庫、發 API request、跑程式等動作」。它擴展 LLM 從「對話模型」變成「能影響真實世界的 agent」。實作上常見透過 [function calling](/llm/knowledge-cards/function-calling/) 或 [MCP](/llm/knowledge-cards/mcp/) 協定。

## 概念位置

Tool use 的典型流程：

```text
1. 開發者定義 tools（每個 tool 含 name、description、parameters schema）
2. LLM 收到 user message 跟 tools 清單
3. LLM 決定要呼叫哪個 tool、生成結構化 tool call（JSON）
4. LLM client（不是模型本身）執行 tool call、得到結果
5. tool 結果回灌進 conversation、模型基於結果繼續生成或再呼叫
```

關鍵特性：

1. **模型本身不執行 tool**：模型只生成 tool call JSON、實際執行由 client 或 [MCP server](/llm/knowledge-cards/mcp/) 完成。
2. **權限由 OS / user / sandbox 決定**：模型再「同意」執行 `rm -rf /`、實際能不能跑取決於跑 tool 的 process 權限。
3. **副作用範圍跟 tool 設計強相關**：tool 寫得越通用（如 `run_shell`）、攻擊面越大；tool 寫得越窄（如 `read_workspace_file`）、攻擊面越小。

Tool use 跟 function calling、MCP 的關係：

| 層次                             | 角色                                                                    |
| -------------------------------- | ----------------------------------------------------------------------- |
| Tool use（概念）                 | 廣義概念、LLM 能呼叫工具                                                |
| Function calling                 | OpenAI 提出的 API 規範、用 JSON schema 定義 function                    |
| [MCP](/llm/knowledge-cards/mcp/) | Anthropic 推動的開放協議、定義 LLM client 跟 tool server 之間的通訊格式 |

## 設計責任

理解 tool use 後可以解釋三個現象：為什麼 LLM 「能跑 shell」其實是 client 跑、不是模型跑（職責切分）、為什麼 tool spec 設計直接影響攻擊面（spec 越鬆、injection 後果越大）、為什麼 [agent loop](/llm/knowledge-cards/agent-loop/) 比單次 tool call 危險（多步 tool use 中 injection 累積）。

設計 tool 跟 MCP server 時、權限白名單 + 副作用可逆性 + confirm 機制是基本配置；production 場景見 [LLM Agent Prompt Injection 後果治理](/backend/07-security-data-protection/llm-prompt-injection-in-agent/) 跟 [6.2 tool use 與 MCP server 的權限模型](/llm/06-security/tool-use-permission-model/)。
