---
title: "Cache Aside"
date: 2026-04-23
description: "說明 application 如何在讀取時自行管理快取與正式資料來源"
weight: 20
---

Cache aside 的核心概念是「application 先查快取，miss 時查正式來源，再把結果寫回快取」。這個模式讓 application 控制讀取流程、key 設計、TTL 與失效策略。

## 概念位置

Cache aside 適合可重建的讀取資料。商品詳情、權限摘要、設定檔與熱門內容常用這種方式加速讀取；正式資料仍然在資料庫或下游服務，快取只是副本。

## 可觀察訊號與例子

系統適合 cache aside 的訊號是讀多寫少、資料可重建、讀取成本高。商品頁查詢頻繁時，cache aside 可以降低資料庫壓力；結帳確認價格時仍應回到正式來源或使用更嚴格一致性策略。

## 設計責任

Cache aside 要定義 cache miss、資料載入、寫回、失效、錯誤 fallback 與防止 stampede 的方式。測試要覆蓋 hit、miss、正式來源失敗、快取寫入失敗與過期資料情境。
