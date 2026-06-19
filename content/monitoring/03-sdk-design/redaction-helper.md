---
title: "SDK redaction helper"
date: 2026-06-19
description: "在事件離開 SDK 前移除敏感資訊 — 預設 redaction rule 處理常見 pattern，自訂 rule 處理業務特定的 secret"
weight: 5
tags: ["monitoring", "sdk", "redaction", "security", "privacy"]
---

SDK [redaction](/monitoring/knowledge-cards/redaction/) helper 在事件離開 SDK（進入 HTTP POST payload）前掃描事件內容，把匹配敏感資訊 pattern 的欄位值替換為 `[REDACTED]`。Redaction 在 SDK 端執行，確保敏感資訊不會經過網路傳輸到 collector — 即使 transport 層被攔截，攻擊者看到的也是脫敏後的資料。

## 預設 redaction rule

SDK 內建一組預設 rule，處理常見的敏感資訊 pattern：

### 密碼欄位

匹配 data 物件中 key 包含 `password`、`passwd`、`secret`、`token`、`api_key`、`apiKey`、`authorization` 的欄位。匹配方式是 key 名稱的子字串比對（case-insensitive）。

### URL 中的認證資訊

匹配 `https://user:password@host` 格式的 URL，把 `user:password` 部分替換為 `[REDACTED]`。

### Stack trace 中的檔案路徑

匹配 stack trace 字串中的使用者目錄路徑（`/Users/username/`、`/home/username/`、`C:\Users\username\`），替換為 `[USER_HOME]/`。避免使用者名稱從 stack trace 洩漏。

## 自訂 redaction rule

業務特定的敏感資訊（信用卡號、身分證字號、醫療資料）不在預設 rule 的範圍內。SDK 提供 API 讓開發者在 init 時註冊自訂 rule。

```text
Monitor.init({
  redactionRules: [
    { pattern: /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/, replace: '[CARD]' },
    { keyPattern: /^ssn$/i, replace: '[REDACTED]' },
  ],
})
```

自訂 rule 和預設 rule 一起執行。如果同一個值被多個 rule 匹配，第一個匹配的 rule 生效（rule 的執行順序：預設 rule 先，自訂 rule 後）。

## Redaction 的執行時機

Redaction 在事件進入 flush payload 的那一刻執行 — buffer 中的事件保持原始內容，flush 時複製一份並在複製上執行 redaction。

在 buffer 中保持原始內容的理由是 debug：開發者在本地 console 看到的 log 應該包含完整資訊（開發環境不需要脫敏），只有離開 SDK 時才脫敏。SDK 可以提供 `debugMode` flag — debugMode 開啟時 console log 印出原始內容，HTTP POST 仍送出脫敏後的內容。

## Redaction 和模組七的關係

SDK redaction helper 是[模組七 資安與隱私](/monitoring/07-security-privacy/)中 redaction 策略的實作層。模組七定義「什麼資訊需要被保護」（策略），本章定義「SDK 如何在程式碼中實現這個保護」（實作）。

兩者的分工：

| 層級   | 職責                                      | 定義在       |
| ------ | ----------------------------------------- | ------------ |
| 策略層 | 哪些欄位需要 redaction、哪些 pattern 敏感 | 模組七       |
| 實作層 | 預設 rule、自訂 rule API、執行時機        | 本章         |
| 驗證層 | 確認脫敏後的事件不包含敏感資訊            | collector 端 |

Collector 端可以做第二道檢查（re-scan 收到的事件是否仍包含敏感 pattern），作為 SDK 端 redaction 的備援。但主要的脫敏責任在 SDK 端 — 資料離開 SDK 後經過網路，已經暴露在傳輸風險中。

## 下一步路由

- SDK 公開 API → [SDK 公開 API 設計](/monitoring/03-sdk-design/public-api/)
- 資安與隱私的完整策略 → [模組七 資安與隱私](/monitoring/07-security-privacy/)
- 自動攔截的 error 也需要 redaction → [自動攔截機制](/monitoring/03-sdk-design/auto-intercept/)
