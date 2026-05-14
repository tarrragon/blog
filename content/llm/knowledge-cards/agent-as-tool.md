---
title: "Agent-as-Tool"
date: 2026-05-14
description: "把一個專責 agent 包成可被另一個 agent 呼叫的 tool，形成跨 agent 的責任邊界"
weight: 1
tags: ["llm", "knowledge-cards", "agent", "multi-agent"]
---

Agent-as-tool 的核心概念是「**把一個 [agent](/llm/knowledge-cards/agent/) 封裝成另一個 agent 可呼叫的工具**」。被封裝的 agent 有自己的 prompt、工具、上下文與完成條件；呼叫方只看到一個較高階的 tool interface。

## 概念位置

它是 [multi-agent system](/llm/knowledge-cards/multi-agent-system/) 的一種拓樸，也可透過 [MCP](/llm/knowledge-cards/mcp/) 暴露成 tool server。它跟 [subagent](/llm/knowledge-cards/subagent/) 的差異是：subagent 常是同一 runtime 內的任務分派，agent-as-tool 強調對外介面與重用邊界。

## 可觀察訊號與例子

主 agent 呼叫 `run_security_review()`，背後其實是一個安全 reviewer agent 讀檔、查規則、輸出 findings。主 agent 不需要知道內部步驟，只需要 consume 結果。

## 設計責任

Agent-as-tool 要把輸入、輸出、權限、副作用與 timeout 定清楚。否則呼叫方會把它當 deterministic tool，但內部其實是 fuzzy agent，失敗模式會被隱藏。
