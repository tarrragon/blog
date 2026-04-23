---
title: "Outbox Pattern"
date: 2026-04-23
description: "說明資料庫狀態變更與事件發布如何透過 outbox 維持一致"
weight: 26
---

Outbox pattern 的核心概念是「把業務資料變更與待發布事件寫進同一個資料庫交易」。交易提交後，獨立 publisher 再從 outbox table 讀出事件並發布到 broker。

## 概念位置

Outbox 解決的是資料已寫入但事件發布失敗的半成功問題。資料庫交易保護業務狀態與 outbox 紀錄；broker 發布則用後續重試與 idempotency 保證最終送出。

## 可觀察訊號與例子

系統需要 outbox 的訊號是「狀態改變後，其他服務必須知道」。訂單付款完成後，倉儲、通知與分析都需要收到事件；若事件發布失敗但訂單已付款，後續流程會漏執行。

## 設計責任

Outbox 要設計 event schema、publisher checkpoint、retry、dead-letter、去重與監控。Runbook 應能看到 outbox backlog、發布錯誤、最舊未發布時間與 replay 流程。
