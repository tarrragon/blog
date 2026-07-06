---
title: "模組三：Sheets 當資料庫"
date: 2026-07-06
description: "用 Google Sheet 存流量資料時，怎麼處理多個 beacon 同時寫入的並發、設計資料模型、以及判斷資料量到哪會撐不住"
weight: 4
tags: ["automation", "google-sheets", "appendrow", "lockservice", "concurrency"]
---

回答「Sheet 當資料庫可以撐到什麼程度、什麼時候會出問題」。Sheets 當儲存體的最大好處是它同時是儀表板——資料進去就能直接看、排序、畫圖。但它畢竟不是為高併發資料庫設計的，這一章處理三件會實際遇到的事：多個 beacon 同時 `appendRow` 會不會互相覆蓋、資料欄位怎麼設計才好彙總、以及列數累積到多少會開始變慢。

Sheets 適合的場景是資料量小到中等、需要人直接讀寫的流量統計。它撐不住的訊號很明確：列數到數萬列後讀寫變慢、瞬間併發逼近 30 時出現寫入衝突。碰到這些訊號時的判斷與遷移路徑，見[模組五](/automation/05-deploy-quota-security/)。

## 章節文章

| 文章                                                                                             | 主題                                                                     |
| ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| [寫入與並發：appendRow 與 LockService](/automation/03-sheet-as-database/append-and-concurrency/) | 單筆 `appendRow`、並發競態何時發生、`LockService` 序列化的時機判斷       |
| [資料模型與容量邊界](/automation/03-sheet-as-database/data-model-and-capacity/)                  | raw log 的欄位設計、Sheets 的 cell 與效能上限、撐不住的訊號與分表 / 遷移 |

## 跨分類引用

- → [模組二：接收端 handler](/automation/02-analytics-beacon/receiver-handler/)：資料怎麼進到 Sheet 的
- → [模組四：觸發器與排程](/automation/04-triggers-automation/)：把 raw log 彙總成報表
- → [模組五：部署、配額與安全](/automation/05-deploy-quota-security/)：Sheets 撐不住時怎麼判斷與遷移
