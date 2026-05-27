---
title: "Cell-Based Architecture"
date: 2026-05-27
description: "把系統拆成多個 isolated cell、控制 blast radius、跨 cell 共用標準介面"
weight: 359
---

Cell-based architecture 的核心責任是 blast radius 控制 — 把整個系統拆成多個 isolated cell、每個 cell 內含完整 stack（front + back + data）、跨 cell 共用標準介面。任何一個 cell 的故障、最壞影響範圍是該 cell 的使用者群、不會跨 cell 擴散。AWS、Slack、DoorDash 採用這條模式。跟 [modular monolith](/backend/knowledge-cards/modular-monolith/) 跟 microservice 是不同維度的拆分（後兩者沿功能拆、cell-based 沿使用者群 / 區域 / tenant 拆）、跟 [database sharding](/backend/knowledge-cards/database-sharding/) 同概念但不同層級（sharding 切資料、cell 切完整 stack）。

## 概念位置

Cell-based architecture 處於系統架構的「失敗隔離」維度、跟 [database sharding](/backend/knowledge-cards/database-sharding/) 同概念但不同層級（sharding 切資料、cell 切完整 stack）。常見 cell 切分軸：按地理 region（AWS 把每個 region 視為獨立 cell）、按 tenant（multi-tenant SaaS 把大客戶各放獨立 cell）、按 user shard（user ID hash 分到 N 個 cell）、按業務 vertical（DoorDash dispatch / payment / merchant 各 cell）。Cell-based 跟 microservice 可以組合：每個 cell 內部用 microservice、跨 cell 也用 microservice 通訊、但 cell 邊界是故障隔離的硬邊界。

## 可觀察訊號與例子

適合採用的訊號：規模到「全站事故代價」遠超「N 個 cell 維運成本」（通常每 cell 服務 10 萬+ 使用者才划算）、業務本質支援使用者分群、合規要求資料 / 流量地理隔離。AWS 用 cell 控制 region 級別的事故影響（每個 region 是獨立 cell）、Slack 用 cell 隔離大客戶事故、DoorDash 用 cell 切 dispatch / payment 業務 vertical。

## 設計責任

Cell 路由層（API gateway / DNS / 負載均衡）決定 request 進哪個 cell、路由邏輯限於單 cell 內 — 防範 cell 間隱式依賴。資料邊界硬切：cell A 的資料庫跟 cell B 完全分離、跨 cell 查詢走標準 API。每 cell 獨立 deploy、rollout 一次只動一個 cell、出問題影響範圍可控。常見失敗：某個 shared service（如 user auth）所有 cell 都打、變成跨 cell 故障的單點 — 真正的 cell-based 連 auth 也要每 cell 獨立或設計成 read-only cache。
