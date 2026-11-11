---
title: "Consistency Level"
date: 2026-05-13
description: "資料系統對讀寫一致性語意的可選擇層級"
weight: 253
---

Consistency level 的核心概念是「系統對同一筆資料在不同節點可見性的承諾強度」。它的責任是把一致性從抽象口號轉成可配置語意，常用於 [eventual-consistency](/backend/knowledge-cards/eventual-consistency/)、[session-consistency](/backend/knowledge-cards/session-consistency/) 與 [linearizability](/backend/knowledge-cards/linearizability/) 之間的取捨。

## 跟其他概念的關係

Consistency level 通常出現在多區域資料庫、快取同步與讀寫分離架構。它會直接影響延遲、可用性與資料新鮮度，因此要和 [latency-budget](/backend/knowledge-cards/latency-budget/) 一起設計。

## 可觀察訊號與例子

需要 consistency level 判讀的訊號是「同一條業務路徑同時要求低延遲與強一致，但沒有分層策略」。例如把結帳交易與商品瀏覽套同一一致性設定，常會讓其中一邊承受不必要成本。

## 判斷條件與後果

同一個系統裡的業務路徑對資料新鮮度的要求不同，consistency level 是否按路徑分層，決定哪一條路徑付多餘的成本。全系統套同一個設定時，設定只能取兩個極端之一：取最保守的，商品瀏覽這類容忍短暫舊資料的路徑也付強一致的延遲；取最冒險的，結帳這類必須讀到最新狀態的路徑會讀到舊資料。按路徑分層時，每一層各自定好延遲超標時降級到哪一級。
