---
title: "Confidence"
date: 2026-05-11
description: "要在證據包、事故候選紀錄或決策紀錄上標示證據可信到什麼程度，或遇到 needs follow-up 與 external-only 兩種值不知道怎麼對應時，查各等級的意思與兩套值域的關係"
weight: 322
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

## 兩套值域

站內有兩套值域。證據包與決策紀錄用 confirmed / suspected / needs follow-up，標的是證據能支持決策到什麼程度，needs follow-up 代表還缺的查證已經指派、在補上之前不據此做決定。事故候選的 intake 紀錄（[8.18 Incident Intake & Evidence Triage](/backend/08-incident-response/incident-intake-evidence-triage/)）用 confirmed / suspected / external-only，external-only 標的是證據的來源：目前只來自客戶、供應商或第三方，還沒有內部證據。external-only 與 suspected 不在同一條軸上，一筆只有外部來源的紀錄也可能強到足以啟動事故。

兩套並存時，intake 紀錄的值在找到內部證據之後改成 confirmed 或 suspected；證據包上的 needs follow-up 可以出現在任何一筆 intake 紀錄的值之下，要和 [known gap](/backend/knowledge-cards/known-gap/) 一起寫明缺的是什麼。外洩事件的 confidence 與外洩來源的歸屬判定分開記：多個客戶的回報讓判定指向平台時，confidence 仍是 external-only，見 [8.26 資料外洩時對商家的通知〈confidence 欄位與判定的紀錄〉](/backend/08-incident-response/security-incident-customer-notification/#confidence-欄位與判定的紀錄)。

## 設計責任

Confidence 要定義等級、證據依據、限制與下一步。它要與 [known gap](/backend/knowledge-cards/known-gap/) 和 [rollback condition](/backend/knowledge-cards/rollback-condition/) 一起保存，避免團隊把暫時結論當成穩定事實。
