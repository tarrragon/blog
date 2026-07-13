---
title: "Adapter"
tags: ["adapter", "hexagonal-architecture"]
date: 2026-07-13
description: "把領域需求翻譯成具體技術操作的實作該放哪、跟領域的邊界在哪時使用。adapter 是 port 的具體實作——技術細節被擋在六角形之外的位置。"
weight: 8
---

adapter 是 [port](/ddd/knowledge-cards/port/) 的具體實作：把領域宣告的需求翻譯成某項技術的操作——SQLite 的查詢、HTTP 的請求、檔案系統的讀寫。技術細節被擋在六角形之外的位置就是這裡：領域只看得見 port、看不見 adapter。adapter 在 [composition root](/ddd/knowledge-cards/composition-root/) 被插上 port；測試裡的 mock 是 adapter 的替身。

## 概念位置

adapter 有兩側。driven adapter 被領域呼叫（資料庫、外部服務的實作）；driving adapter 呼叫領域（UI 事件處理、API handler）。兩側的共同責任是翻譯：領域語言與技術語言在這裡互換、不讓任何一邊的詞彙滲到對面。

## 可觀察訊號

實作類 import 框架套件、以技術命名（SqliteBookRepository），是 adapter 各安其位的訊號。領域規則出現在 adapter 裡（折扣計算寫在 repository、狀態判斷寫在 handler）是反向滲透——規則離開了領域模型、[invariant](/ddd/knowledge-cards/invariant/) 的強制位置跟著失守。

## 設計責任

adapter 寫完、測試通過，只證明它自己行為正確；它有沒有被插上 port、插的是不是它，是組裝層的問題。接線的證言與強制層選擇見 [組裝層的可達性](/ddd/composition-root-reachability/)。
