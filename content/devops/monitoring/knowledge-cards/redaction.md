---
title: "Redaction"
date: 2026-06-19
description: "說明在事件資料離開 client 之前把敏感欄位的值替換成遮罩或移除的機制"
weight: 2
tags: ["monitoring", "security", "redaction", "knowledge-card"]
aliases: ["/monitoring/knowledge-cards/redaction/"]
---

Redaction 的核心概念是「在事件資料離開 client 之前，把敏感欄位的值替換成遮罩或移除」。密碼、API key、個人識別資訊在送到 collector 之前就被處理，確保敏感資料不進入傳輸和儲存層。可先對照 [funnel analysis](/devops/monitoring/knowledge-cards/funnel-analysis/)（去識別化是行為分析的入場條件）。

## 跟其他概念的關係

Redaction 位在 SDK 端的事件產生和 collector 端的事件接收之間。它是監控資料安全的第一道防線 — 在資料離開使用者裝置之前處理，比 collector 端的 access control 更早介入。Redaction 和 transport 加密（HTTPS）互補：redaction 保護欄位內容，transport 加密保護傳輸過程。與 [error fingerprint](/devops/monitoring/knowledge-cards/error-fingerprint/) 相比，兩者都在資料落地前處理，但 redaction 防止敏感內容外洩、fingerprint 防止同因錯誤重複灌爆列表。

## 可觀察訊號與例子

系統需要 redaction 的訊號是監控事件的 data 欄位可能包含使用者輸入。CLI 輸入可能含密碼（`mysql -p'secret'`）、API key（`Authorization: Bearer sk-...`）、連線字串（含帳密的 URL）。IME 個人化學習也是洩漏面 — 輸入框的內容被 IME 學習後跨 app 可見。

## 判斷條件與後果

Redaction 的規則決定哪些敏感值在離開 client 之前被處理。只有依欄位名稱比對的預設規則時，寫在一般欄位裡的敏感值（CLI 輸入裡的 `mysql -p'secret'`、含帳密的連線字串）照樣送出，原因是欄位名稱沒有透露它的內容；自訂 pattern 用正則表達式比對值本身，涵蓋這一類，代價是 pattern 寫得太窄會漏、太寬會把正常內容也遮掉。redaction 在 event 進入 buffer 之前執行時，buffer 裡只有處理過的值；到 flush 時才執行，buffer 在這段期間暫存的是原值。redaction 處理失敗時，丟棄整筆事件的結果是少一筆監控資料而沒有外洩；只移除已知的敏感欄位時事件保留下來，代價是沒完成的那一段比對原本要抓的值可能還在事件裡。這些規則只管得到網站自己 SDK 送出的事件；同一個頁面上的商業追蹤碼由 vendor 的 script 直接送出，遮蔽要用 vendor 提供的設定，見 [Autocapture（自動事件收集）](/devops/monitoring/knowledge-cards/autocapture/)。
