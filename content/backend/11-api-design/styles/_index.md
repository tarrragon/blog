---
title: "API 風格流派層"
date: 2026-07-03
description: "各 API 風格流派的深度論證：每個流派用自己的語言 steelman、含失敗案例與適用邊界；判準層見主章"
weight: 90
tags: ["backend", "api-design", "styles"]
---

流派層收各 API 風格內部的深度交鋒、對應其他模組的 `vendors/` 慣例：每個流派一個目錄、文章用該流派自己的詞彙陳述論證、含該流派的失敗案例與適用邊界。中性判準層在 [主章](/backend/11-api-design/)、選型判讀從 [11.2 風格選型總覽](/backend/11-api-design/api-style-selection/) 進入；讀者已熟悉主流做法、想看各流派怎麼為自己辯護時、直接從本層進入。

| 目錄                                         | 主題                                                    | 狀態       |
| -------------------------------------------- | ------------------------------------------------------- | ---------- |
| [rest/](/backend/11-api-design/styles/rest/) | REST 語意學之爭、hypermedia 復興、Richardson 成熟度     | 已完成     |
| graphql/                                     | schema 演進、執行成本與安全、公開 API 的進退            | backlog    |
| grpc/                                        | proto 演進紀律、部署邊界、內部 RPC 選型                 | backlog    |
| rpc-revival/                                 | tRPC 型別共享、JSON-RPC 重生場景                        | backlog    |
| standards/                                   | JSON:API 與 OData、OpenAPI 與 AsyncAPI 生態             | backlog    |
| realtime/                                    | WebSocket / SSE / long-polling / webhook 的對外承諾差異 | 案例待採集 |
