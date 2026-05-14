---
title: "Tool-Use Permission Model"
date: 2026-05-14
description: "把 LLM tool use 的讀取、寫入、外部副作用與審查節點分級管理的權限模型"
weight: 1
tags: ["llm", "knowledge-cards", "tool-use", "security"]
---

Tool-use permission model 的核心概念是「**按工具副作用範圍設計 LLM 可以做什麼、何時需要人類批准**」。模型只生成 [tool use](/llm/knowledge-cards/tool-use/) call，真正副作用由 client、MCP server、shell 或外部 API 執行，因此權限邊界必須放在工具層與執行環境。

## 概念位置

它建立在 [tool use](/llm/knowledge-cards/tool-use/)、[MCP](/llm/knowledge-cards/mcp/) 與 [sandbox](/llm/knowledge-cards/sandbox/) 之上。核心不是模型是否「想」執行，而是執行該 tool 的 process 是否有權限、是否有 allowlist、是否需要 approval。

## 可觀察訊號與例子

Read-only file search 可以自動；修改檔案要 checkpoint；刪除資料、push、部署、發送外部訊息通常要 step-by-step approval。第三方 MCP server 如果能讀整個 home directory，風險高於只讀 workspace 的 server。

## 設計責任

先把工具分成 read、local write、external side effect、irreversible operation，再配置 sandbox、allowlist、confirmation、audit log 與 rollback。高風險工具的預設應是人類批准，而不是 prompt 裡要求模型小心。
