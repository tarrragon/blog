---
title: "Soft TTL"
date: 2026-04-23
description: "說明資料進入刷新期後仍可短暫使用以降低 stampede"
weight: 97
---

Soft TTL 的核心概念是「資料過了建議刷新時間後仍可短暫使用，同時觸發背景刷新」。它讓系統在資料需要更新時仍保留可用結果，降低 cache stampede 風險。 可先對照 [Source of Truth](/backend/knowledge-cards/source-of-truth/)。

## 跟其他概念的關係

Soft TTL 把過期分成可用刷新期與硬過期點。資料進入刷新期後仍可回應部分 request，並由背景流程重建；到達硬過期點後則停止使用該副本。 可先對照 [Source of Truth](/backend/knowledge-cards/source-of-truth/)。

## 可觀察訊號與例子

系統需要 soft TTL 的訊號是熱門資料過期時大量 request 同時打向正式來源。熱門排行榜可以在 soft TTL 到期後先回傳舊榜單，同時觸發背景刷新。

## 判斷條件與後果

Soft TTL 讓過期資料在刷新期內繼續被使用，這段寬限換到的可用性付出多少代價，取決於最大 stale 時間、刷新 owner 與失敗重試。最大 stale 時間（soft TTL 到硬過期點的距離）超過使用者可接受的程度時，使用者看到的舊資料在業務上已經算錯；刷新沒有指定 owner 時，刷新期內每個 request 都可能各自觸發刷新，回到 cache stampede 的情形；刷新失敗而沒有重試時，資料一直舊到硬過期點，之後的 request 直接打向正式來源。Stale response 次數、刷新耗時與刷新失敗率分別反映舊資料被使用的量、刷新是否跟得上過期的速度，以及資料是否正朝硬過期點前進。
