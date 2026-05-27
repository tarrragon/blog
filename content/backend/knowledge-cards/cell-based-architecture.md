---
title: "Cell-Based Architecture"
date: 2026-05-27
description: "把系統拆成多個獨立 cell、跨 cell 共用標準介面、控制 blast radius 的架構模式"
weight: 359
---

Cell-based architecture 把整個系統拆成多個 isolated cell、每個 cell 內含完整 stack（front + back + data）、跨 cell 共用標準介面。核心責任是 **blast radius 控制** — 任何一個 cell 的故障、最壞影響範圍是該 cell 的使用者群、不會跨 cell 擴散。AWS、Slack、DoorDash 用這條模式。跟 [Modular monolith](/backend/knowledge-cards/modular-monolith/) 跟 microservice 是不同維度的拆分 — 後兩者沿「功能」拆、cell-based 沿「使用者群 / 區域 / tenant」拆。

## 概念位置

Cell-based architecture 處於系統架構的「失敗隔離」維度、跟 [modular monolith](/backend/knowledge-cards/modular-monolith/) 是不同維度的拆分（modular 沿業務功能、cell-based 沿使用者群 / region）。常見 cell 切分軸：

- **按地理 region**：AWS 把每個 region 視為獨立 cell、cross-region failover 需要明示流量切換
- **按 tenant**：multi-tenant SaaS 把大客戶各放獨立 cell、避免一個客戶事故影響其他
- **按 user shard**：user ID hash 分到 N 個 cell、每 cell 承擔 1/N 流量
- **按業務 vertical**：DoorDash dispatch / payment / merchant 各 cell、業務邊界 + cell 邊界對齊

## 跟其他拆分模式的差異

| 維度         | Microservice                       | Cell-based                       | Modular monolith   |
| ------------ | ---------------------------------- | -------------------------------- | ------------------ |
| 拆分軸       | 業務功能                           | 使用者群 / region                | 業務功能（內部）   |
| 部署單位     | N 個服務獨立部署                   | N 個完整 stack 並排部署          | 單一部署           |
| Blast radius | 一個服務掛、影響使用該服務的所有人 | 一個 cell 掛、影響該 cell 使用者 | 全掛               |
| 適用規模     | 多團隊、業務分化                   | 高規模 + 高可用要求              | 中型團隊、業務複雜 |

Cell-based 跟 microservice 可以組合：每個 cell 內部用 microservice、跨 cell 也用 microservice 通訊、但 cell 邊界是故障隔離的硬邊界。

## 關鍵設計

- **Cell 間共用標準介面**：所有 cell 對外提供相同的 API contract、client 不該感知 cell 拆分
- **Cell 路由層**：API gateway / DNS / 負載均衡決定 request 進哪個 cell、路由邏輯不能跨 cell（避免 cell 間隱式依賴）
- **資料邊界硬切**：cell A 的資料庫跟 cell B 完全分離、跨 cell 查詢走標準 API
- **每 cell 獨立 deploy**：rollout 一次只動一個 cell、出問題影響範圍可控

## 適用 vs 不適用

適用：

- 規模到「全站事故代價」遠超「N 個 cell 維運成本」（通常每 cell 服務 10 萬+ 使用者才划算）
- 業務本質支援使用者分群（不要求跨使用者一致性）
- 合規要求資料 / 流量地理隔離

不適用：

- 規模太小（cell 間維運成本超過故障隔離收益）
- 業務要求跨使用者強一致（如即時跨用戶搜尋、聊天室）
- 沒有 cell 路由層能力

## 失敗模式

- **隱式跨 cell 依賴**：某個 shared service（如 user auth）所有 cell 都打、變成跨 cell 故障的單點
- **資料分割錯**：tenant 同時用多個 cell、查詢時跨 cell 拼資料、退化成 microservice 的協調成本
- **Cell 內仍 monolithic**：每 cell 內部沒模組化、cell 內事故仍會擴散到整個 cell
