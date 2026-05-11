---
title: "MCP（Model Context Protocol）"
date: 2026-05-11
description: "LLM application ↔ 外部 tool server 之間的標準化協議、複用 OpenAI 相容 API 的成功模式"
weight: 1
tags: ["llm", "knowledge-cards"]
---

MCP（Model Context Protocol、2024 年由 Anthropic 提出）的核心概念是「LLM application 跟外部 tool server 之間的標準化協議」。它解的是 LLM application 生態的 N×M 整合問題：N 個 application 接 M 個 tool、不標準化要寫 N×M 個 adapter；MCP 把這個成本拆成 N+M（application 端跟 server 端各實作協議一次）。

## 概念位置

MCP 在**架構協議**層、跟 [function calling](/llm/knowledge-cards/function-calling/)（模型能力層）、structured output（sampling 約束層）正交。它跟模型怎麼呼叫工具無關、只管「工具怎麼被暴露給 application」。複用 [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/) 的標準化模式：定義最小可用標準、讓生態繞著標準長、所有 player 受益。

## 可觀察訊號與例子

MCP 涵蓋 server 該提供什麼：tool 註冊、tool schema、tool 呼叫協議、resource 暴露、prompt template 共享。2026/5 主要 LLM application（Claude Desktop、Cursor 等）支援 MCP；社群維護的 MCP server 數量快速增長（檔案系統、Git、Slack、各種 API 等）；本地推論伺服器（Ollama、LM Studio）仍以 [OpenAI 相容 API](/llm/knowledge-cards/openai-compatible-api/) 為主、MCP 接入較慢。

## 設計責任

需不需要用 MCP 看應用規模：小型 in-process 應用（直接 Python function）用 function calling + 簡單 dispatcher 就夠、不需 MCP。要跨 application 共用 tool、或想接入既有 MCP server 生態（如標準化的 git / filesystem tools）才需要 MCP。詳細展開見 [4.3 應用層協議](/llm/04-applications/application-protocols/)。
