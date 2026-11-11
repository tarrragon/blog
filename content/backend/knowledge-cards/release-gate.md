---
title: "Release Gate"
tags: ["發布關卡", "Release Gate"]
date: 2026-04-24
description: "說明變更在正式釋出前如何通過或阻擋"
weight: 254
---

Release Gate 的核心概念是「在變更進入正式環境前，用明確條件決定能不能放行」。 可先對照 [Rollback Rehearsal](/backend/knowledge-cards/rollback-rehearsal/)。

## 跟其他概念的關係

Release Gate 位在 migration、schema change、deployment、error budget 與 incident policy 之間。它把驗證結果轉成可執行的放行決策，並常搭配 [Rollback Rehearsal](/backend/knowledge-cards/rollback-rehearsal/) 確認放行前後都能回復。

## 可觀察訊號

系統需要 release gate 的訊號是：

- 變更會影響使用者可用性或資料正確性
- 新舊版本會並存一段時間
- 團隊需要在 release 前確認檢查項都過關
- 發版失敗時要有明確阻擋條件

## 接近真實網路服務的例子

Schema migration 要先確認相容性與 backfill 結果再放行；高風險設定變更要通過 security review 與 drift check；error budget 快耗盡時，團隊可以暫停高風險變更，直到風險恢復到可接受範圍。

## 判斷條件與後果

Release gate 的放行決策是否一致，取決於它的條件有沒有寫明。檢查項與通過條件沒有寫明時，放行與否由當下審核的人判斷，gate 等同一個批准按鈕，同一個變更換人審可能得到不同結果；沒有阻擋條件時，檢查失敗也不會停下發版。沒有擁有者時，檢查項過時之後沒有人更新；沒有例外流程時，急件只能繞過 gate，而繞過的紀錄不存在。
