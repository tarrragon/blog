---
title: "Pagination Cursor（分頁游標）"
date: 2026-07-20
description: "分頁狀態的表示權該留在誰手上——cursor 的不透明性是介面演化自由度的承諾還是逃生門"
weight: 414
---

Pagination cursor 跟 [Keyset Pagination](/backend/knowledge-cards/keyset-pagination/) 談的是同一個分頁機制的不同切面：keyset pagination 卡描述的是伺服器內部怎麼用 `WHERE id > last_seen_id` 這類條件把查詢複雜度壓到跟 offset 大小無關；pagination cursor 卡描述的是這個內部狀態要不要對消費者不透明——cursor 內容用 Base64 編碼、消費者不能解析，是服務端保留自由改動底層分頁策略的契約承諾，不只是實作細節。

## 概念位置

Cursor 不透明性的核心價值是把分頁狀態的表示權留在伺服器端。消費者不能解析 cursor，就不能依賴它的內部格式，伺服器因此可以自由更換底層策略（keyset、shard 位置、甚至在單一 cursor 內編多個 shard 的位置）而不需要動介面。這個承諾要從第一版就成立——先給透明 cursor 再收緊成不透明，本身就是一次破壞相容性的變更，等於自己踩了 [Deprecation Lifecycle](/backend/knowledge-cards/deprecation-lifecycle/) 要處理的問題。

## 可觀察訊號與例子

Slack 從 offset 分頁遷移到 opaque cursor 時明列了付出的代價：失去 total count 與跳頁能力，這是明示的產品決策而非技術妥協——選 cursor 前要先跟產品端確認「第 N 頁」跟「共幾筆」是不是真需求，而不是遷移完才發現這兩個功能回不來了。判準是資料量小、寫入頻率低、產品要跳頁時 offset 分頁合理且便宜；資料量大或寫入頻繁時該用 cursor。

## 判讀方式

看到消費者端在 decode cursor 內容並依賴裡面的欄位時，這是設計缺口的訊號——底層策略一旦換掉，這些依賴會立即斷裂。判讀既有系統是否符合不透明契約，檢查 cursor 是不是純粹的隨機或加密字串，而不是可被肉眼辨識出結構的字串（例如可辨識的遞增數字或明文欄位拼接）。
