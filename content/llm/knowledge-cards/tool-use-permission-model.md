---
title: "Tool-Use Permission Model"
date: 2026-05-14
description: "把 LLM tool use 的讀取、寫入、外部副作用與審查節點分級管理的權限模型"
weight: 1
tags: ["llm", "knowledge-cards", "tool-use", "security"]
---

Tool-use permission model 的核心概念是「**按工具副作用範圍設計 LLM 可以做什麼、何時需要人類批准**」。模型只生成 [tool use](/llm/knowledge-cards/tool-use/) call，真正副作用由 client、MCP server、shell 或外部 API 執行，因此權限邊界必須放在工具層與執行環境。

## 跟其他概念的關係

它建立在 [tool use](/llm/knowledge-cards/tool-use/)、[MCP](/llm/knowledge-cards/mcp/) 與 [sandbox](/llm/knowledge-cards/sandbox/) 之上。核心不是模型是否「想」執行，而是執行該 tool 的 process 是否有權限、是否有 allowlist、是否需要 approval。

## 可觀察訊號與例子

Read-only file search 可以自動；修改檔案要 checkpoint；刪除資料、push、部署、發送外部訊息通常要 step-by-step approval。第三方 MCP server 如果能讀整個 home directory，風險高於只讀 workspace 的 server。

## 判斷條件與後果

一個工具出錯之後能不能挽回，取決於它的副作用範圍：read、local write、external side effect、irreversible operation 四級。read 工具出錯時沒有狀態被改變，自動執行的代價只是一次錯誤的讀取；local write 出錯時本機檔案被改壞，有 checkpoint 或 rollback 才還原得了；external side effect 與 irreversible operation（push、部署、發送外部訊息、刪除資料）一旦執行，本機的 rollback 碰不到它們。模型只生成 tool call，實際執行的是 client、MCP server 或 shell 的 process，所以 prompt 裡要求模型小心，限制不了那個 process 能做的事；高風險工具因此預設由人類批准，並以 sandbox、allowlist 限制 process 碰得到的範圍，audit log 留下事後追查的紀錄。
