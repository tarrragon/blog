---
title: "Rollback Rehearsal"
tags: ["回滾演練", "Rollback Rehearsal"]
date: 2026-04-24
description: "說明如何在正式事故前演練回滾流程"
weight: 157
---

Rollback Rehearsal 的核心概念是「在低風險環境實際走一次回滾流程，確認步驟、權限與耗時都符合預期」。 可先對照 [Rollback Strategy](/backend/knowledge-cards/rollback-strategy/)。

## 跟其他概念的關係

Rollback Rehearsal 位在 release gate、rollback strategy、migration 與 disaster recovery 之間。它是把回滾步驟實際走過一次的演練，文件審查無法替代實機驗證。 可先對照 [Rollback Strategy](/backend/knowledge-cards/rollback-strategy/)。

## 可觀察訊號

系統需要 rollback rehearsal 的訊號是：

- 變更失敗時回復速度會直接影響使用者影響
- 團隊不確定回滾步驟是否真的可執行
- 高風險 migration 或 release 會同時影響資料與流量
- 權限、腳本、順序或相容性可能成為回復瓶頸

## 接近真實網路服務的例子

資料表結構變更前先在接近正式環境演練 rollback，可以確認舊欄位是否還能恢復、資料補回是否可逆、以及切回舊版本後是否還能接流量。服務替換前做 rollback rehearsal，也能驗證 DNS、load balancer 與設定切換的回復時間。

## 判斷條件與後果

回滾流程裡只寫在文件上、沒有實際執行過的步驟，是 Rollback Rehearsal 要找的對象。權限、腳本、執行順序與新舊版本的相容性，都可能到真正回滾時才發現不可行：執行者沒有權限、舊版本讀不懂新欄位、DNS 或 load balancer 的切換時間比預期長，這些就是「看似可回滾、實際回不去」的缺口。演練的環境與資料範圍跟正式環境差得越多，演練通過能證明的越少，因為缺口多半出在正式環境才有的資料與設定上。演練沒有記下實際耗時與失敗的步驟時，下一次回滾的時間預估仍然沒有依據。
