---
title: "Per-Connection Memory"
date: 2026-05-22
description: "說明每條連線或每個操作的記憶體用量如何隨並發數放大"
weight: 343
---

Per-Connection Memory 的核心概念是某些記憶體是「每條連線」或「每個操作」各自配置的 — sort buffer、join buffer、連線本身的開銷 — 它的總量等於單份用量乘上並發連線數。它讓並發尖峰時的記憶體用量可能遠超直覺。它和全域共用的 [Buffer Pool](/backend/knowledge-cards/buffer-pool/) 是兩種不同的記憶體，並和 [Connection Pool](/backend/knowledge-cards/connection-pool/) 直接相關。

## 概念位置

Per-Connection Memory 位在資料庫記憶體模型中、與全域記憶體相對的一側。全域記憶體（例如 [Buffer Pool](/backend/knowledge-cards/buffer-pool/)）由所有連線共用、調一次影響全體；per-connection 記憶體每條連線各配一份，調大單份設定會被並發數放大。連線數的上限由 [Connection Pool](/backend/knowledge-cards/connection-pool/) 與資料庫設定共同決定。

## 可觀察訊號與例子

需要注意 per-connection memory 的訊號是資料庫在尖峰並發時記憶體吃緊、OOM 或被容器重啟，但平時看起來有餘裕。常見的反直覺陷阱是為了讓某個查詢更快而調大 sort / join buffer，結果在高並發時這個「單份」設定乘上幾百條連線，把記憶體撐爆。

## 設計責任

設計時要把記憶體預算拆成全域與 per-connection 兩部分，並用最大並發連線數去乘 per-connection 設定，確認尖峰仍在容量內。調校順序通常是先把全域記憶體調穩，再針對特定查詢調 session 層設定，並同時限制連線數。observability 要看連線數、記憶體用量與 OOM / swap 訊號。
