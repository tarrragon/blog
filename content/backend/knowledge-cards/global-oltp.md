---
title: "Global OLTP"
date: 2026-05-13
description: "跨地理區域仍維持交易一致性的 OLTP 設計責任與代價"
weight: 241
---

Global OLTP 的核心概念是「跨 region 寫入與讀取仍維持可驗證的交易一致性」。它承擔的是跨地理距離下的正確性責任，不是單純把資料複製到多地，常依賴 [distributed-sql](/backend/knowledge-cards/distributed-sql/) 或同級一致性機制。

## 概念位置

Global OLTP 是 [transaction boundary](/backend/knowledge-cards/transaction-boundary/) 在多 region 場景的延伸。它通常需要 quorum、跨區時鐘或排序協議，並把跨區延遲納入設計前提。可先對照 [latency budget](/backend/knowledge-cards/latency-budget/) 與可用性目標（availability target）。

## 可觀察訊號與例子

需要 global OLTP 的訊號是「跨區交易順序錯誤會直接造成業務損失或合規風險」。例如支付、票務庫存、核心帳務。若業務可接受短暫不一致，多數情境可改用 eventual/session consistency，降低延遲與成本。

## 設計責任

設計 global OLTP 時要先定義三件事：一致性目標、可接受延遲上限、區域故障下的服務策略。若無法同時滿足三者，就需要調整資料分區、交易範圍或一致性層級，而不是直接加硬體。
