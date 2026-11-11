---
title: "Read Compatibility"
date: 2026-05-11
description: "說明資料或服務演進期間讀取路徑如何同時支援新舊語意"
weight: 143
tags: ["backend", "knowledge-card", "database", "migration"]
---

Read compatibility 的核心概念是「讀取路徑在過渡期同時理解新舊資料語意」。它連接 [Expand / Contract](/backend/knowledge-cards/expand-contract/)、[schema migration](/backend/knowledge-cards/schema-migration/) 與 [fallback](/backend/knowledge-cards/fallback/)，讓新欄位或新資料模型可以先進入 production，再逐步切換讀取權。

## 跟其他概念的關係

Read compatibility 位在 [dual write](/backend/knowledge-cards/dual-write/)、[cutover / switchover](/backend/knowledge-cards/cutover-switchover/) 與 [migration gate](/backend/knowledge-cards/migration-gate/) 之間。雙寫處理寫入一致性，read compatibility 處理讀取方如何在缺值、延遲回填或版本混跑時仍能給出一致判讀。

## 可觀察訊號

系統需要 read compatibility 的訊號是：

- 新欄位已新增，但歷史資料尚未全部 backfill
- 新舊程式版本會同時服務流量
- rollback 後舊版本仍需要讀懂 production 資料
- 內部後台、對帳或報表的切換節奏不同於使用者可見路徑

## 接近真實網路服務的例子

訂單服務新增 `payment_state` 後，讀取時可先看新欄位，缺值時回到舊 `status` 的付款語意。客服後台可以先用這條相容讀取路徑驗證資料，再逐步讓使用者可見查詢改用新欄位。

## 判斷條件與後果

過渡期的讀取是否一致，看讀取方遇到缺值、延遲回填或版本混跑時，各路徑是否給出同一個判讀。讀取優先順序與 fallback read 條件沒有定義時，新舊欄位不一致的那幾筆資料在不同路徑上讀出不同的狀態；資料新鮮度限制沒有寫明時，fallback 讀到的舊值多舊還能用沒有依據。停止條件缺席時，相容讀取路徑一直留著，舊語意沒有退場的時間點。有 [validation query](/backend/knowledge-cards/validation-query/) 與 [rollback strategy](/backend/knowledge-cards/rollback-strategy/) 搭配時，cutover 之前就能確認新舊讀取的結果一致、rollback 之後舊版本仍讀得懂資料；缺了它們，舊版本或長尾讀取路徑判讀不了資料的情形在 cutover 之後才出現。
