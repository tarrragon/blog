---
title: "Retention"
date: 2026-06-22
description: "說明資料或事件保留多久，以及保留期限如何影響重放與成本"
weight: 75
tags: ["backend", "observability"]
---

Retention 的核心概念是「資料或事件在系統中保留多久」。它影響 storage cost、audit 能力、replay 能力、debug 時間窗口、合規義務與資料刪除責任。

## 概念位置

Retention 連接資料生命週期跟查詢能力。不同類型的資料需要不同保留期限 — log 的 debug 用途可能只需要 7 天、audit log 因合規要求可能需要 1 年以上、metrics 的 raw data 可能保留 15 天但 [rollup](/backend/knowledge-cards/rollup/) 保留 90 天。

Retention 跟 [storage tiering](/backend/knowledge-cards/storage-tiering/) 搭配運作 — hot tier 保留最近的高精度資料、warm / cold tier 保留較舊的低精度或歸檔資料。保留期限的設定見 [4.7 cardinality 與成本邊界](/backend/04-observability/cardinality-cost-governance/) 的保留階梯段。

## 使用情境

系統需要 retention 設計的訊號是事故排查或資料修復需要回看歷史。若 event stream 只保留 24 小時，三天前的錯誤就無法靠 replay 重建。反過來，無限保留會讓儲存成本持續成長。

## 設計責任

Retention 要同時考慮成本（儲存 × 時間）、法規（合規要求的最短保留期跟 GDPR 要求的最長保留期可能衝突）、資安（高敏感資料保留越久風險越高）、replay 需求（MQ 的 retention 影響 consumer 的 catchup 能力）跟 debug 能力（retention 太短讓事後分析無資料可用）。不同訊號類型用不同 retention 是基本做法 — error log 保留比 debug log 長、audit log 保留比 operational log 長。
