---
title: "Known Gap"
date: 2026-05-11
description: "說明證據包如何明確保存已知缺口，避免下游高估證據完整性"
weight: 322
tags: ["backend", "knowledge-card", "observability", "incident-response"]
---

Known gap 的核心概念是「把已知但尚未覆蓋的證據缺口寫進 artifact」。它連接 [evidence package](/backend/knowledge-cards/evidence-package/)、[data quality](/backend/knowledge-cards/data-quality/) 與 [action item closure](/backend/knowledge-cards/action-item-closure/)，讓缺口能被追蹤、交班與回寫。

## 概念位置

Known gap 位在 [confidence](/backend/knowledge-cards/confidence/)、[query link](/backend/knowledge-cards/query-link/) 與 [post-incident review](/backend/knowledge-cards/post-incident-review/) 之間。Data quality 說明資料限制，known gap 則列出目前尚未被證據覆蓋的具體範圍。

## 可觀察訊號

系統需要 known gap 的訊號是：

- 某些 tenant、region、callback path 或 manual repair path 未被抽樣
- trace 或 log 缺少關鍵 span / field
- release gate 放行時仍有需要 follow-up 的證據缺口
- PIR 需要把缺口回寫成 readiness 或 observability 改善項

## 接近真實網路服務的例子

資料庫 migration evidence package 可以記錄 `manual refund repair path not yet sampled`。這個 known gap 會限制 cutover decision，並回寫成後續 validation query 或 audit log coverage 的改善項。

## 設計責任

Known gap 要描述缺口內容、影響範圍、目前風險、owner 與 follow-up。它要支援 [confidence](/backend/knowledge-cards/confidence/) 分級，避免 evidence package 看起來完整，但實際漏掉高風險路徑。
