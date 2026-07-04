---
title: "11.7 集合介面設計"
date: 2026-07-03
description: "分頁方案的承諾差異、批次操作的部分失敗語意、超過請求逾時的長時操作怎麼回 — 集合與長時操作的介面判準"
weight: 7
tags: ["backend", "api-design", "pagination"]
---

集合介面的設計難點在規模是變數：同一個 list endpoint、資料一千筆時各方案差異可忽略、一億筆加高頻寫入時、當初的分頁決策變成效能與一致性問題。本章處理三個規模敏感的介面模式：分頁、批次、長時操作。

## 分頁：offset 的兩個失效模式

offset 分頁（`?page=3&limit=50`）的介面直觀、失效有明確的機制。Slack 的工程紀錄給了一手描述：其一、`LIMIT / OFFSET` 深頁掃描 — 資料庫要掃過並丟棄前面所有列、頁數越深成本越高；其二、page window 漂移 — 高頻寫入下、兩次請求之間有新資料插入、消費者會看到跳項或重複（見 [11.C37](/backend/11-api-design/cases/pagination-slack-cursor-migration/)）。

Slack 的解法是遷移到 opaque cursor：介面收斂為 `cursor` 加 `limit`、回傳 `next_cursor`、cursor 內容 Base64 編碼、消費者不可解析。opaque 這個性質是設計重點 — **分頁狀態的表示權留在 server 端**、消費者不能解析就不能依賴內部格式、server 可以自由更換底層策略（keyset、shard 位置、甚至混合）而不動介面。同一份紀錄明列了付出的代價：失去 total count 與跳頁能力 — 這是明示的產品決策、選 cursor 前要跟產品端確認「第 N 頁」跟「共幾筆」是不是真需求。

判準：資料量小、寫入頻率低、產品要跳頁 — offset 合理且便宜；資料量大或寫入頻繁 — cursor、並從第一版就 opaque（先給透明 cursor 再收緊、又是一次 breaking change）。offset、cursor、keyset 的完整交鋒與「cursor 不透明性算承諾還是逃生門」的爭議、收在掛本章的分頁爭論文章 backlog（見 [模組頁](/backend/11-api-design/)）。

## 批次操作：部分失敗是預設、不是例外

批次介面（一次建立 100 筆）的核心設計問題是部分失敗語意：第 37 筆驗證失敗、前 36 筆算什麼。三種可承諾的語意、各有成立情境：

- **全有全無**：包成一個 transaction、任一筆失敗全部回滾。語意最乾淨、消費者重試最簡單（整包重送）；成本是 server 端要撐住大 transaction、且單筆失敗導致整批回滾的體驗、在大批次下代價過高。
- **獨立處理、逐筆回報**：回應是跟請求等長的結果陣列、每筆自己的成功或錯誤。務實預設、但消費者的重試邏輯變複雜 — 要能只重送失敗子集、這又要求逐筆操作冪等（[11.8](/backend/11-api-design/api-idempotency-design/) 的主題）。
- **fail-fast**：處理到第一個錯誤即停、回報已處理數。適合順序有意義的批次（匯入）、消費者從斷點續傳。

判準是消費者的重試能力與資料的順序性；唯一的反模式是不宣告 — 文件沒寫部分失敗語意的批次介面、消費者只能拿 production 事故來逆向工程。選定語意之後、部分成功在 status 層怎麼表達（207、200 加 per-item errors、或原子化保持單一 status）另有取捨、見 [Status 裝不下的東西](/backend/11-api-design/status-expressiveness-boundary/)。

## 長時操作：把「進行中」實體化

超過請求逾時預算的操作（報表、匯入、佈建）、介面要回的是「工作的身分」而非結果。Google AIP-151 是這個模式的系統化規範：長時方法回傳 Operation resource、client 輪詢其 `done` / `response` / `error` 狀態、回應型別事先宣告、operation 約 30 天過期（見 [11.C44](/backend/11-api-design/cases/longrun-google-aip151/)）。比起裸的 202 加 Location、Operation resource 的增量價值在統一：所有長時操作共用同一個查詢介面、client 寫一套 polling 邏輯到處用；`done=true` 直接回的 validate-only 條款、示範了用同一個介面模式涵蓋同步捷徑的手法（C44 判讀）。

設計時要明訂的三件事：operation 的生命週期（查詢結果保留多久 — AIP 選 30 天）、輪詢的節奏指引（配合 [11.9](/backend/11-api-design/external-traffic-semantics/) 的限流語意、避免消費者用 while-true 打爆查詢端點）、以及完成通知的替代路徑（webhook 回呼、屬 styles/realtime 的 backlog 範圍）。

## 常見設計錯誤

- **透明 cursor**：消費者 decode 後依賴內部欄位、底層換策略即斷 — 從第一版就 opaque。
- **批次語意未宣告**：部分失敗行為靠消費者猜。
- **長時操作同步等**：把 5 分鐘的工作掛在一條 HTTP 連線上、逾時、重試、重複執行三連發。
- **list 端點無上限**：`limit` 沒有 max、一個請求拉全表 — 上限是集合介面的基本流量防線（完整語意見 [11.9](/backend/11-api-design/external-traffic-semantics/)）。

## 下一步路由

- 批次重試的前提：[11.8 API 層冪等設計](/backend/11-api-design/api-idempotency-design/)
- 深頁掃描背後的資料庫機制：[1.13 Query 反模式](/backend/01-database/query-anti-patterns/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
