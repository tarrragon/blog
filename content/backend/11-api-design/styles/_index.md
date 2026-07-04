---
title: "API 風格流派層"
date: 2026-07-03
description: "各 API 風格的深度使用判準：每個流派的適用邊界、失敗案例、選了怎麼用；中性選型軸見主章"
weight: 90
tags: ["backend", "api-design", "styles"]
---

流派層收各 API 風格的深度使用判準、對應其他模組的 `vendors/` 慣例：每個流派一個目錄、給該風格的適用邊界、失敗案例與使用觀念。中性選型軸在 [主章](/backend/11-api-design/)、選型判讀從 [11.2 風格選型總覽](/backend/11-api-design/api-style-selection/) 進入；讀者已熟悉主流做法、想看某個風格什麼時候該選、選了要扛什麼、直接從本層進入。

| 目錄                                                       | 主題                                                     | 狀態   |
| ---------------------------------------------------------- | -------------------------------------------------------- | ------ |
| [rest/](/backend/11-api-design/styles/rest/)               | REST 這個歧義詞的選型用法、hypermedia 與成熟度的適用邊界 | 已完成 |
| [graphql/](/backend/11-api-design/styles/graphql/)         | schema 演進、執行成本與安全、公開 API 的進退             | 已完成 |
| [grpc/](/backend/11-api-design/styles/grpc/)               | proto 演進紀律、部署邊界、內部 RPC 選型                  | 已完成 |
| [rpc-revival/](/backend/11-api-design/styles/rpc-revival/) | tRPC 型別共享、JSON-RPC 適用條件                         | 已完成 |
| [standards/](/backend/11-api-design/styles/standards/)     | 採現成格式標準還是自建規範、描述格式的選型               | 已完成 |
| [realtime/](/backend/11-api-design/styles/realtime/)       | server 推 client 四機制的對外承諾差異                    | 已完成 |
