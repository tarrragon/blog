---
title: "tRPC 與 JSON-RPC：兩種輕量 RPC 的適用條件"
date: 2026-07-03
description: "型別即契約的 tRPC 與最小訊息層的 JSON-RPC 各自落在哪個消費者形狀：前提、代價、什麼時候別選"
weight: 4
tags: ["backend", "api-design", "rpc"]
---

這兩種 RPC（remote procedure call、把遠端呼叫包裝成像呼叫本地函式）都用「把重量拿掉」換選型優勢、但拿掉的部分不同、適用的消費者形狀也不同。tRPC 拿掉 IDL 與 codegen、契約放進 TypeScript 型別系統、換到零產碼的開發體驗；JSON-RPC 拿掉傳輸與 schema 約束、只留最小訊息結構、換到零依賴的本地協議。本目錄兩篇各回答一件事：各自落在哪個消費者形狀、前提與代價是什麼、什麼時候該翻向別的風格。中性選型判準見 [11.2 風格選型總覽](/backend/11-api-design/api-style-selection/)。

| 文章                                                                                             | 主題                                           | 案例支撐 |
| ------------------------------------------------------------------------------------------------ | ---------------------------------------------- | -------- |
| [tRPC 型別共享](/backend/11-api-design/styles/rpc-revival/rpc-revival-trpc-type-sharing/)        | 型別即契約、同倉 TS-only 前提、公開 API 不適用 | C33、C23 |
| [JSON-RPC 的適用條件](/backend/11-api-design/styles/rpc-revival/rpc-revival-jsonrpc-conditions/) | 本地雙向低頻、最小訊息層、LSP 與 MCP 的實證    | C34      |
