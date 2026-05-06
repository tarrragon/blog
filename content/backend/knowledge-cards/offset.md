---
title: "Offset"
date: 2026-04-23
description: "說明 consumer 在事件流中的讀取位置與重放基準"
weight: 74
---


Offset 的核心概念是「consumer 在事件流中的讀取位置」。它讓 consumer 知道自己已經處理到哪裡，也讓系統可以從某個位置繼續或重放。 可先對照 [On-Call](/backend/knowledge-cards/on-call/)。

## 概念位置

Offset 是 stream replay、consumer lag 與 checkpoint 的基礎。Offset 提交太早可能造成處理遺失；提交太晚可能造成重複處理。 可先對照 [On-Call](/backend/knowledge-cards/on-call/)。

## 可觀察訊號與例子

系統需要理解 offset 的訊號是 consumer 重啟後需要接續處理。報表 consumer 處理到某個 offset 後 crash，重啟時要從安全位置繼續，並用 idempotency 承受可能重複的事件。

## 設計責任

Offset 提交要和業務處理完成條件對齊。Runbook 應說明如何查 current offset、committed offset、lag、重設 offset 與 replay 影響。
