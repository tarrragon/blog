---
title: "Confidence"
date: 2026-05-11
description: "說明證據包如何標示 confirmed、suspected 或 needs follow-up 的判讀信心"
weight: 321
tags: ["backend", "knowledge-card", "observability", "incident-response"]
---

Confidence 的核心概念是「標示目前證據能支持決策的信心等級」。它連接 [evidence package](/backend/knowledge-cards/evidence-package/)、[data quality](/backend/knowledge-cards/data-quality/) 與 [gate decision](/backend/knowledge-cards/gate-decision/)，讓團隊能區分 confirmed、suspected 與 needs follow-up。

## 概念位置

Confidence 位在 [query link](/backend/knowledge-cards/query-link/)、[known gap](/backend/knowledge-cards/known-gap/) 與 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 之間。它不是情緒性的「我覺得」，而是基於證據完整度、資料限制與反向驗證狀態的判讀欄位。

## 可觀察訊號

系統需要 confidence 的訊號是：

- evidence 足以支持繼續 backfill，但不足以支持使用者可見 cutover
- 事故中某個根因還在 suspected 狀態
- release gate 需要分辨可以放行、暫停或補證據
- stakeholder update 需要避免把未確認資訊說成事實

## 接近真實網路服務的例子

資料庫 migration 的 evidence package 可以把 `confidence` 標成 `suspected`：validation query 顯示 mismatch 低於門檻，但 manual refund repair path 尚未被抽樣，因此只放行下一批 backfill，不放行使用者可見讀取 cutover。

## 設計責任

Confidence 要定義等級、證據依據、限制與下一步。它要與 [known gap](/backend/knowledge-cards/known-gap/) 和 [rollback condition](/backend/knowledge-cards/rollback-condition/) 一起保存，避免團隊把暫時結論當成穩定事實。
