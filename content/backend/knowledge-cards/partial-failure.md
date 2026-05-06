---
title: "Partial Failure"
date: 2026-04-23
description: "說明分散式系統中部分依賴失效時如何保留整體可用性"
weight: 50
---


Partial failure 的核心概念是「系統的一部分失效，但其他部分仍然可以運作」。分散式系統很少整體同時成功或同時失敗；更常見的是某個區域、依賴、partition、consumer 或資料副本出問題。 可先對照 [Partition](/backend/knowledge-cards/partition/)。

## 概念位置

Partial failure 是降級、fallback、circuit breaker、failover 與 observability 的共同前提。設計要先承認某些功能會局部失效，再定義核心功能如何保留。 可先對照 [Partition](/backend/knowledge-cards/partition/)。

## 可觀察訊號與例子

系統需要 partial failure 設計的訊號是單一依賴失效會拖慢整體頁面。商品頁中推薦服務失效時，頁面仍可顯示商品資訊與購買按鈕；推薦區可以使用 fallback 或暫時空白。

## 設計責任

Partial failure 設計要分清核心路徑與輔助路徑。觀測資料要能按依賴、功能區塊、tenant、region 或 endpoint 顯示故障範圍。
