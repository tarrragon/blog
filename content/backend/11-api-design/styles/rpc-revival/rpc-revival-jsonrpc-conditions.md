---
title: "JSON-RPC 的適用條件：最小夠用的訊息層"
date: 2026-07-03
description: "本地雙向低頻、需 notification 語意、生態要求零 codegen 可自省 —— 這組條件下 JSON-RPC 比重型 RPC 更貼"
weight: 2
tags: ["backend", "api-design", "rpc"]
---

JSON-RPC 落在一組很具體的條件上：本地 process 之間、雙向、低頻、需要 notification（不等回應的單向通知）語意、且生態工具要求零 codegen、可自省。這組條件湊齊時、JSON-RPC 的「最小夠用訊息層」剛好夠、而重型 RPC 的能力反而變成負擔。以下界定這組條件、並用兩份現代協議的採用當實證。

## 條件組合：什麼時候最小訊息層剛好夠

JSON-RPC 只規定訊息的形狀：一個 request 帶 method、params、id、一個對應的 response、以及沒有 id 的 notification。它不管傳輸（誰負責搬 bytes 由外層決定）、不強制 schema、不要 codegen。這個「少」在對外 web API 是缺點 —— 缺工具生態、缺標準化的錯誤與分頁 —— 但在下面這組條件裡剛好是優點：

- **本地 process 間**：傳輸是 stdio 或本機 socket、不需要 HTTP/2 的 multiplexing 與流量控制。
- **雙向且需要 notification**：server 要能主動推事件給 client（編輯器的診斷、agent 的進度）、JSON-RPC 的 notification 原生支援這個語意。
- **零 codegen、可自省**：工具（編輯器外掛、agent runtime）要能不經 build pipeline 就發一個請求、JSON 純文字可讀、不必先產 client stub。

這組條件下、gRPC 的 HTTP/2 加 codegen 成本全是負資產（此為選型判讀、見下方對照）—— 你付了重量、換不到對應的價值。

JSON-RPC 不限於本地 —— Ethereum 節點的 JSON-RPC API 就是網路遠端、走 HTTP、也不低頻。本篇 scope 到「本地雙向低頻」、是因為那是它明顯勝過 gRPC 的區間、不是 JSON-RPC 的全部適用面。

## 實證：LSP 與 MCP 都在 JSON-RPC 上加約束

兩份現代協議在這組條件下選了 JSON-RPC、而且都是「在它上面加約束」而非發明新協議 —— 這個做法本身是選型訊號。LSP（編輯器與 language server 的協議）明文用 JSON-RPC 描述 requests、responses、notifications、固定 `jsonrpc: "2.0"`、外層自訂 Content-Length header 當傳輸框（見 [11.C34](/backend/11-api-design/cases/rpc-jsonrpc-lsp-mcp-revival/)）。MCP（agent 與工具的協議、2025-06-18 spec）規定所有訊息 MUST follow JSON-RPC 2.0、並在其上收緊約束（request ID 不可為 null、同 session 不可重用）、傳輸支援 stdio 與 HTTP。

這裡有一個引用邊界要標明：兩份 spec 都只陳述「採用 JSON-RPC」這個事實、沒有寫「為什麼選它」的理由段。上一節那組條件是本模組從採用事實反推的判讀、不是 spec 的原話。能直接學的做法是：選一個最小夠用的訊息層、然後在它上面加你自己場景需要的約束（ID 語意、session 規則）、而不是為每個新協議重造訊息結構。

## 對照：與 gRPC、tRPC 的分工

JSON-RPC 跟 [gRPC](/backend/11-api-design/styles/grpc/grpc-internal-rpc-selection/) 服務的是不同 deployment shape：gRPC 落在跨服務、高吞吐、要框架層集中的位置；JSON-RPC 落在本地、雙向、低頻的位置。兩者不是競爭、是消費者形狀這條軸的不同列 —— 判準見 [11.2](/backend/11-api-design/api-style-selection/)。

還有一個當代共性值得點出：MCP 的 schema 以 TypeScript 為 source of truth、跟 [tRPC](/backend/11-api-design/styles/rpc-revival/rpc-revival-trpc-type-sharing/) 用型別系統當契約、都指向「用 TypeScript 型別當契約源頭」的模式。這是觀察到的趨勢共性、不是說兩者可互換 —— MCP 仍是跨語言協議、tRPC 綁單語言。

## 下一步路由

- 高吞吐跨服務的對照位置：[gRPC 內部 RPC 的選型位置](/backend/11-api-design/styles/grpc/grpc-internal-rpc-selection/)
- 型別當契約的同倉路線：[tRPC 型別共享](/backend/11-api-design/styles/rpc-revival/rpc-revival-trpc-type-sharing/)
- 三軸選型判準：[11.2 風格選型總覽](/backend/11-api-design/api-style-selection/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
