---
title: "Transport 安全"
date: 2026-06-19
description: "HTTPS / basic auth / 同區網也要加密的理由 — 監控資料在傳輸途中的保護機制"
weight: 2
tags: ["monitoring", "security", "transport", "https", "encryption"]
---

Transport 安全保護監控資料在從 SDK 傳送到 collector 的過程中不被竊聽或篡改。即使 SDK 端做了 redaction，傳輸中的資料仍然包含使用者行為、系統狀態、error 訊息等有價值的資訊 — 這些資訊在未加密的傳輸中可以被同網段的任何人攔截。

## 同區網也要加密的理由

自用工具的 SDK 和 collector 通常在同一台機器或同一個區域網路（LAN / Tailscale tailnet）。常見的假設是「同區網不需要加密，因為只有我自己在用」。

這個假設在以下情境不成立：

**共用網路**：咖啡廳、共享辦公室、飯店 WiFi — 同一個 AP 下的其他裝置可以用 ARP spoofing 或 WiFi sniffing 攔截未加密的 HTTP 流量。

**未來的網路拓撲變更**：目前在同一台機器上的 SDK 和 collector，可能之後拆到不同的機器或不同的網路段。如果一開始就用 HTTPS，拓撲變更不需要額外的安全調整。

**養成正確習慣**：在自用工具上用 HTTP 是因為「反正只有我」，但相同的開發者在商業專案中可能延續這個習慣。從自用工具開始就用 HTTPS，讓加密傳輸成為預設行為。

## HTTPS 設定

### 自簽憑證

自用工具和內部服務用自簽憑證（self-signed certificate）就足夠。不需要購買 CA 憑證 — 自簽憑證提供加密（防竊聽）和完整性（防篡改），只是不提供身份驗證（client 無法確認 server 是不是「官方的」）。在自用場景中 server 就是自己架的，身份驗證不是問題。

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

Go collector 使用自簽憑證：

```go
http.ListenAndServeTLS(":8443", "cert.pem", "key.pem", handler)
```

SDK 端需要信任自簽憑證。開發期可以在 HTTP client 設定 `badCertificateCallback` 接受自簽憑證；production 應該把自簽憑證加入系統的信任清單。

### Let's Encrypt

如果 collector 有公開的 domain name，用 Let's Encrypt 取得免費的 CA 憑證。自動續期、不需要手動管理。適合部署在 VPS 或雲端的 collector。

## Basic Auth

HTTPS 保護傳輸層（防竊聽），basic auth 保護 endpoint 層（防未授權存取）。兩者互補，缺一不可 — basic auth 在 HTTP 上傳送的是 base64 編碼的帳密，沒有 HTTPS 的加密保護等於明文傳送。

```text
Authorization: Basic base64(username:password)
```

SDK 在每個 HTTP POST request 的 header 中帶上 basic auth。Collector 端驗證帳密，不匹配則回傳 401。

Basic auth 的帳密管理：

- 帳密存在 SDK 的設定檔或環境變數中，不硬編碼在程式碼裡
- Collector 端的帳密用 bcrypt hash 儲存，不存明文
- 定期輪替帳密（自用工具半年到一年一次即可）

## API Key 替代方案

如果不需要 username/password 的雙因素，單一 API key 更簡單。

```text
X-API-Key: sk_monitor_abc123...
```

API key 的管理比 basic auth 簡單（一個字串而非帳密對），但安全性略低（只有一個 factor）。自用工具場景下 API key 通常足夠。

## 下一步路由

- SDK 端的 redaction → [SDK Redaction API 設計](/monitoring/07-security-privacy/sdk-redaction-api/)
- Collector 端的 access control → [Collector Access Control 實作](/monitoring/07-security-privacy/collector-access-control/)
- Server-side 的 secret management → [backend 07 資安](/backend/07-security-data-protection/)
