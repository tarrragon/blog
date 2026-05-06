---
title: "Soft TTL"
date: 2026-04-23
description: "說明資料進入刷新期後仍可短暫使用以降低 stampede"
weight: 96
---


Soft TTL 的核心概念是「資料過了建議刷新時間後仍可短暫使用，同時觸發背景刷新」。它讓系統在資料需要更新時仍保留可用結果，降低 cache stampede 風險。 可先對照 [Source of Truth](/backend/knowledge-cards/source-of-truth/)。

## 概念位置

Soft TTL 把過期分成可用刷新期與硬過期點。資料進入刷新期後仍可回應部分 request，並由背景流程重建；到達硬過期點後則停止使用該副本。 可先對照 [Source of Truth](/backend/knowledge-cards/source-of-truth/)。

## 可觀察訊號與例子

系統需要 soft TTL 的訊號是熱門資料過期時大量 request 同時打向正式來源。熱門排行榜可以在 soft TTL 到期後先回傳舊榜單，同時觸發背景刷新。

## 設計責任

Soft TTL 要定義最大 stale 時間、刷新 owner、失敗重試與使用者可接受程度。觀測上要看 stale response 次數、刷新耗時與刷新失敗率。
