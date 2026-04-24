---
title: "Shadow Read"
date: 2026-04-23
description: "說明正式讀取仍走舊路徑時如何暗中讀新路徑比對結果"
weight: 84
---

Shadow read 的核心概念是「正式結果仍使用舊路徑，同時暗中讀新路徑做比對」。它讓團隊在 cutover 前驗證新系統的正確性與延遲。

## 概念位置

Shadow read 是 migration 與服務替換的驗證工具。它能在不影響使用者結果的前提下收集新舊差異，但會增加下游流量與資料存取成本。

## 可觀察訊號與例子

系統需要 shadow read 的訊號是新讀取路徑即將接正式流量。搜尋服務換新索引前，可以用正式查詢同時查新索引，記錄結果差異但仍回傳舊索引結果。

## 設計責任

Shadow read 要控制採樣率、timeout、資料遮罩、差異記錄與成本。它的結果應進入 correctness dashboard，並作為 [Migration Gate](../migration-gate/) 的依據。
