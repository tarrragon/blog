---
title: "Release Gate"
tags: ["發布關卡", "Release Gate"]
date: 2026-04-24
description: "說明變更在正式釋出前如何通過或阻擋"
weight: 253
---

Release Gate 的核心概念是「在變更進入正式環境前，用明確條件決定能不能放行」。

## 概念位置

Release Gate 位在 migration、schema change、deployment、error budget 與 incident policy 之間。它把驗證結果轉成可執行的放行決策，並常搭配 [Rollback Rehearsal](rollback-rehearsal/) 確認放行前後都能回復。

## 可觀察訊號

系統需要 release gate 的訊號是：

- 變更會影響使用者可用性或資料正確性
- 新舊版本會並存一段時間
- 團隊需要在 release 前確認檢查項都過關
- 發版失敗時要有明確阻擋條件

## 接近真實網路服務的例子

Schema migration 要先確認相容性與 backfill 結果再放行；高風險設定變更要通過 security review 與 drift check；error budget 快耗盡時，團隊可以暫停高風險變更，直到風險恢復到可接受範圍。

## 設計責任

Release Gate 要定義檢查項、擁有者、通過條件、阻擋條件與例外流程。它不是單純的批准按鈕，而是把風險控制流程標準化。
