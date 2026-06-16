---
title: "Replay Window"
date: 2026-06-16
description: "說明事件可重播的時間或 offset 範圍邊界，由 retention 與 checkpoint 決定"
weight: 378
---

Replay window 的核心概念是「事件能往回重播的範圍」。它由 broker 的 retention 與 consumer 的 checkpoint 共同界定，決定出事後能補送多久以前的事件。 可先對照 [Recovery Semantics](/backend/knowledge-cards/recovery-semantics/)。

## 概念位置

Replay window 是 [recovery semantics](/backend/knowledge-cards/recovery-semantics/) 的具體邊界。它把「可恢復」量化成一段 [offset](/backend/knowledge-cards/offset/) 或時間區間：超出 retention 的事件已被刪除、無法重播，補償就要改走資料庫或上游來源。

## 可觀察訊號與例子

Kafka 設 7 天 retention，replay window 就是 7 天，第 8 天的錯誤要重算就找不到原始事件；SQS 最長保留 14 天、Pub/Sub 預設 7 天，managed 佇列的 replay window 由保留期上限決定。

## 設計責任

設計時把 replay window 對齊事故偵測到修復的最長時間。偵測延遲若可能超過 retention，就拉長保留期或在下游留可重算的來源，避免事件已過期才發現要補。
