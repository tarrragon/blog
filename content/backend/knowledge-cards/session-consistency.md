---
title: "Session Consistency"
date: 2026-05-13
description: "同一使用者工作階段內維持讀寫一致、跨工作階段允許短暫不一致"
weight: 246
---

Session consistency 的核心概念是「同一 session 內讀到自己剛寫入的資料」，但不保證全域即時一致。它的責任是在體感一致與系統延遲之間提供可操作折衷，位在 [external-consistency](/backend/knowledge-cards/external-consistency/) 與 eventual consistency 之間。

## 概念位置

Session consistency 常出現在多區域資料庫的可調一致性模型，介於 [external-consistency](/backend/knowledge-cards/external-consistency/) 與 eventual consistency 之間。它常用於高互動產品路徑，降低讀者看到「我剛改完卻看不到」的落差。

## 可觀察訊號與例子

需要 session consistency 的訊號是「同一使用者回看自己操作結果時，短暫不一致會造成信任下降」，例如個人設定、遊戲狀態、用戶偏好。若是跨使用者共享狀態，仍要額外評估全域一致需求。

## 設計責任

採用 session consistency 時，要明確定義 session 邊界、token/連線續存策略與跨裝置行為。若 session 定義模糊，會讓一致性語意在不同入口不一致，反而增加除錯成本。
