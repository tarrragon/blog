---
title: "SDK Redaction API 設計"
date: 2026-06-19
description: "預設 redaction rule 過濾已知敏感欄位、自訂 pattern 擴展應用特有的 secret 格式 — redaction 在 SDK 端執行，敏感資料不離開 client"
weight: 1
tags: ["monitoring", "security", "redaction", "sdk", "privacy"]
---

Redaction 是在事件資料離開 client 之前，把敏感欄位的值替換成遮罩或移除。Redaction 在 SDK 端執行的設計原則是「敏感資料不離開 client」— 一旦資料送到 collector，即使 collector 有 access control，資料已經在網路上傳輸過，多了一層洩漏面。

## 預設 Redaction Rule

SDK 內建的 redaction rule 覆蓋最常見的敏感欄位模式。開發者不需要設定就能獲得基本保護。

### 欄位名稱比對

以下欄位名稱（不分大小寫）的值自動替換為 `[REDACTED]`：

- `password`、`passwd`、`secret`、`token`、`api_key`、`apiKey`
- `authorization`、`auth`、`credential`
- `ssn`、`social_security`
- `credit_card`、`card_number`、`cvv`、`cvc`

欄位名稱比對用 substring match — `user_password` 包含 `password` 會被 redact，`password_reset_token` 包含 `password` 和 `token` 也會。

### 值格式比對

以下格式的值無論欄位名稱為何都自動替換：

- Email 地址格式（`user@domain.com` → `u***@domain.com`）
- 信用卡號碼格式（連續 13-19 位數字 → 保留末四碼）
- Bearer token 格式（`Bearer xxx` → `Bearer [REDACTED]`）

值格式比對用正則表達式。正則的效能影響在大量事件時需要注意 — 預設 rule 的正則保持簡單，避免 catastrophic backtracking。

## 自訂 Pattern

應用可能有自己的 secret 格式，預設 rule 覆蓋不到。SDK 提供 API 讓開發者註冊自訂 redaction pattern。

```text
monitor.addRedactionRule(
  name: 'internal-api-key',
  pattern: RegExp(r'sk_live_[a-zA-Z0-9]{24}'),
  replacement: '[REDACTED:api-key]',
)

monitor.addRedactionRule(
  name: 'database-url',
  fieldNames: ['database_url', 'db_url', 'connection_string'],
  replacement: '[REDACTED:db-url]',
)
```

自訂 pattern 的設計考量：

**Pattern 在 init 時註冊**。Redaction rule 在 SDK 初始化時設定，之後所有事件都通過這些 rule。不支援動態修改 — 避免「中途加 rule 導致之前的事件沒被 redact」的困惑。

**Pattern 順序無關**。所有 rule 獨立執行，不依賴順序。一個欄位可以匹配多個 rule，以第一個匹配的 replacement 為準。

**Replacement 可以保留部分資訊**。`[REDACTED]` 完全遮蔽，`[REDACTED:api-key]` 保留類型資訊，`u***@domain.com` 保留結構。保留類型資訊對 debug 有幫助 — 看到 `[REDACTED:api-key]` 至少知道這裡原本有一個 API key。

## Redaction 的適用範圍

Redaction 應用在 SDK 送出事件前的最後一步 — 在序列化（JSON encode）之前。適用範圍包括：

- Event 的 data 欄位（自由欄位，開發者可能放入任何內容）
- Error 的 stack trace（檔案路徑可能包含使用者名稱或部署路徑）
- Error 的 message（例外訊息可能包含 query string 或參數值）
- Lifecycle 的 metadata（連線 URL 可能包含認證資訊）

Redaction 不應用在 SDK 的內部欄位（timestamp、event type、session ID）— 這些是 SDK 自己產生的，不包含使用者資料。

## 下一步路由

- 資料離開 client 後的保護 → [Transport 安全](/monitoring/07-security-privacy/transport-security/)
- 去識別化策略 → [去識別化策略](/monitoring/07-security-privacy/anonymization-strategy/)
- IME 個人化學習的 secret 洩漏風險 → [ux-design 模組三 IME 安全 checklist](/ux-design/03-input-mechanism/ime-security-checklist/)
