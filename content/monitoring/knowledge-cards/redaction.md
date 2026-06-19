---
title: "Redaction"
date: 2026-06-19
description: "說明在事件資料離開 client 之前把敏感欄位的值替換成遮罩或移除的機制"
weight: 2
tags: ["monitoring", "security", "redaction", "knowledge-card"]
---

Redaction 的核心概念是「在事件資料離開 client 之前，把敏感欄位的值替換成遮罩或移除」。密碼、API key、個人識別資訊在送到 collector 之前就被處理，確保敏感資料不進入傳輸和儲存層。可先對照 [funnel analysis](/monitoring/knowledge-cards/funnel-analysis/)（去識別化是行為分析的入場條件）。

## 概念位置

Redaction 位在 SDK 端的事件產生和 collector 端的事件接收之間。它是監控資料安全的第一道防線 — 在資料離開使用者裝置之前處理，比 collector 端的 access control 更早介入。Redaction 和 transport 加密（HTTPS）互補：redaction 保護欄位內容，transport 加密保護傳輸過程。

## 可觀察訊號與例子

系統需要 redaction 的訊號是監控事件的 data 欄位可能包含使用者輸入。CLI 輸入可能含密碼（`mysql -p'secret'`）、API key（`Authorization: Bearer sk-...`）、連線字串（含帳密的 URL）。IME 個人化學習也是洩漏面 — 輸入框的內容被 IME 學習後跨 app 可見。

## 設計責任

Redaction 要定義預設規則（哪些欄位名稱自動 redact）、自訂 pattern（正則表達式比對敏感值）、執行時機（event 進入 buffer 前還是 flush 時）、以及 redaction 失敗的處理（丟棄整筆事件 vs 只移除敏感欄位）。
