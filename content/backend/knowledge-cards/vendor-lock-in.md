---
title: "Vendor Lock-In"
date: 2026-05-22
description: "說明採用供應商產品後，其 API 與格式滲入程式碼造成的退出成本"
weight: 345
---

Vendor Lock-In 的核心概念是採用某個供應商的產品後，它的 API、資料格式或平台行為逐漸滲入核心程式碼，使得日後要換掉它的成本變得很高。它讓「現在好接」與「日後難退」成為要一起評估的取捨。降低它的手段要接回 [Provider Adapter](/backend/knowledge-cards/provider-adapter/) 與 [Repository Adapter](/backend/knowledge-cards/repository-adapter/)。

## 概念位置

Vendor Lock-In 位在選型決策的長期成本面。它本身是風險概念，[Provider Adapter](/backend/knowledge-cards/provider-adapter/) 與 [Integration Adapter](/backend/knowledge-cards/adapter/) 則是緩解它的設計手段 — 把供應商特定的介面包在 adapter 後面，讓 domain 程式碼不直接依賴它。退出時的搬遷要接回 [Migration](/backend/knowledge-cards/migration/)。

## 可觀察訊號與例子

需要正視 vendor lock-in 的訊號是供應商特定的 driver API、查詢語法或資料格式出現在 domain 邏輯裡。低採用成本的產品（特別是 edge 或 serverless 類）常把成本藏在退出端：接的時候很快，要換的時候發現整個 codebase 都綁住了。一個務實的檢查是「能不能說清楚退出路徑」。

## 設計責任

設計時要把供應商特定的介面收斂到 adapter 層，並明確記錄退出路徑：要換掉這個供應商，需要動哪些地方。對關鍵依賴，退出路徑應該被實際演練過，而不是只存在文件上。是否接受某個 lock-in 是有效的決策，前提是在採用當下就把成本看清楚。
