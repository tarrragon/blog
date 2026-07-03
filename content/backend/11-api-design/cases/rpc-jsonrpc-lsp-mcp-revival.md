---
title: "11.C34 JSON-RPC 重生：LSP 與 MCP 都選它當訊息層"
date: 2026-07-03
description: "死在 web API、活在編輯器與 agent 協議：最小夠用訊息層的選型條件組合"
weight: 34
tags: ["backend", "api-design", "case-study", "rpc"]
---

這個案例的核心責任是記錄 JSON-RPC 重生場景的共同形狀：兩份現代 spec 的採用事實。

## 觀察

LSP spec 明文 content part 使用 JSON-RPC 描述 requests / responses / notifications、固定 `jsonrpc: "2.0"`、外層自訂 Content-Length header 傳輸。MCP spec 規定所有訊息 MUST follow JSON-RPC 2.0、並在其上收緊（request ID 不可為 null、同 session 不可重用）、transport 支援 stdio 與 HTTP、schema 以 TypeScript 為 source of truth。注意：LSP spec 只陳述採用、未寫選型理由段 — 教材推導理由時要標明是判讀、不是引文。

## 判讀

重生場景的共同形狀：本地 process 間、雙向、低頻、需要 notification 語意、且生態工具（編輯器 / agent）要求零 codegen 可自省 — 這組條件下 gRPC 的 HTTP/2 加 codegen 成本全是負資產。兩份 spec 都「在 JSON-RPC 上加約束」而非發明新協議、是「選最小夠用訊息層」的教材主軸。

## 對應大綱

styles/rpc-revival/「JSON-RPC 的重生場景」（anchor）、11.2 風格選型交叉。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Language Server Protocol Specification 3.17（Microsoft）](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/)
- [Model Context Protocol: Base Protocol（spec、2025-06-18）](https://modelcontextprotocol.io/specification/2025-06-18/basic)
