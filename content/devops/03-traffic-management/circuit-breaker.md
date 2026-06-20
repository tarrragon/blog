---
title: "熔斷器"
date: 2026-06-20
description: "依賴服務失敗時怎麼快速失敗而非拖慢自己 — 三狀態模型（closed → open → half-open）和熔斷判斷條件"
weight: 3
tags: ["devops", "traffic-management", "circuit-breaker", "fault-tolerance", "dependency"]
---

熔斷器保護的是「呼叫外部依賴」的路徑。當外部依賴（資料庫、第三方 API、通知服務）持續失敗時，熔斷器讓後續的呼叫立即失敗（回傳預設值或錯誤），而非每次都等待逾時。等待逾時的代價是佔住 goroutine / thread 不釋放，積累到一定數量就拖垮整個服務。

## 三狀態模型

### Closed（正常）

所有呼叫正常通過。熔斷器記錄成功和失敗的計數。

### Open（熔斷）

當失敗率或連續失敗次數超過閾值時，熔斷器進入 open 狀態。此後所有呼叫**立即回傳錯誤**，不實際呼叫外部依賴。

Open 狀態持續固定時間（如 30 秒），時間到後進入 half-open。

### Half-open（探測）

允許少量呼叫（如 1 個）實際通過到外部依賴。如果成功 → 回到 closed；如果失敗 → 回到 open（重設計時器）。

Half-open 的目的是自動探測依賴是否恢復，不需要人工介入。

## 熔斷判斷條件

| 條件            | 適用場景         | 參數                      |
| --------------- | ---------------- | ------------------------- |
| 連續 N 次失敗   | 依賴完全不可用   | N = 5-10                  |
| 失敗率 > X%     | 依賴間歇性失敗   | X = 50%，統計窗口 = 10 秒 |
| 平均延遲 > Y ms | 依賴變慢但未失敗 | Y = 依據 SLA 設定         |

「失敗」的定義需要明確：HTTP 5xx 是失敗、4xx 通常不是（client 的問題）、timeout 是失敗、connection refused 是失敗。

## 熔斷時的 fallback

熔斷觸發後，呼叫端收到的是「快速失敗」而非逾時。呼叫端需要有 fallback 策略：

| 依賴                      | Fallback                               |
| ------------------------- | -------------------------------------- |
| 通知服務（Slack webhook） | 記錄到本地 log、恢復後補發             |
| 外部 API（enrichment）    | 回傳無 enrichment 的原始資料           |
| 認證服務                  | 用本地 cache 的 token 驗證（短暫降級） |

沒有 fallback 的依賴被熔斷 = 對應功能完全不可用。熔斷器保護的是「不讓不可用的功能拖垮整個服務」。

## 監控系統的應用

[Collector](/monitoring/04-collector/) 的 rule engine 在規則命中時可能呼叫外部服務（Slack webhook、HTTP POST 到 alert endpoint）。如果外部服務掛了，每個命中的規則都會等待逾時 — 大量規則命中時 goroutine 積壓。

熔斷器包在 rule engine 的「執行外部動作」環節：連續 5 次外部呼叫失敗 → 熔斷 → 後續規則命中不再嘗試外部呼叫、改寫本地 log → 30 秒後探測一次 → 外部服務恢復 → 恢復正常呼叫。

## 下一步路由

- 被動的流量控制 → [背壓機制](/devops/03-traffic-management/backpressure/)
- 主動的速率限制 → [Rate Limiting](/devops/03-traffic-management/rate-limiting/)
- 不同工作負載的資源隔離 → [Bulkhead 隔離](/devops/03-traffic-management/bulkhead/)
