---
title: "Collector Access Control 實作"
date: 2026-06-19
description: "認證（誰在送資料）/ 授權（允許送什麼）/ access log（誰在什麼時候送了什麼）— collector 端的三層存取控制"
weight: 3
tags: ["monitoring", "security", "access-control", "authentication", "authorization"]
---

Collector access control 管理「誰可以對 collector 做什麼操作」。三層控制各自回答不同的問題：認證回答「來源是誰」，授權回答「這個來源被允許做什麼」，access log 回答「誰在什麼時候實際做了什麼」。

## 認證：來源是誰

認證驗證送出資料的 client 是否合法。未認證的 request 應該被拒絕，避免任意來源向 collector 寫入資料。

### API Key 認證

每個合法的 SDK client 有一個 API key。Collector 檢查 request header 中的 API key 是否在合法清單中。

```go
func authMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        key := r.Header.Get("X-API-Key")
        if !isValidKey(key) {
            http.Error(w, "unauthorized", http.StatusUnauthorized)
            return
        }
        next.ServeHTTP(w, r)
    })
}
```

自用工具場景下，一個 API key 對應一個 client 通常就足夠。多個 client（例如同一個 app 的 iOS 和 Android 版本）可以用同一個 key，或每個平台一個 key 以便在 access log 中區分來源。

### mTLS（Mutual TLS）

Client 和 server 互相驗證對方的憑證。安全性比 API key 高 — 攻擊者即使取得 API key，沒有 client 憑證也無法連線。

mTLS 的設定成本較高（每個 client 需要產生和管理憑證），適合對安全性要求較高的環境。自用工具通常不需要 mTLS。

## 授權：允許做什麼

授權控制已認證的 client 可以執行哪些操作。Collector 的操作通常分為兩類：寫入事件和查詢事件。

### 角色分離

最簡單的授權模型是兩個角色：

- **Writer**：只能寫入事件（POST /events）。SDK client 使用這個角色。
- **Reader**：只能查詢事件（GET /events、GET /query）。開發者的 CLI 工具使用這個角色。

角色分離的價值在於限制洩漏的影響範圍。如果 SDK 的 API key 被洩漏，攻擊者只能寫入（產生垃圾事件），不能讀取（看到歷史事件中的敏感資訊）。

### 寫入限制

即使認證通過、角色正確，collector 也可以對寫入加上限制：

- **Rate limit**：每個 API key 每分鐘最多 N 個 request。防止 client 端 bug 導致事件風暴。
- **Payload size limit**：每個事件最大 M KB。防止異常大的 event data 消耗儲存。
- **Schema validation**：事件必須符合定義的 JSON schema。格式不正確的事件拒絕存入。

## Access Log：誰做了什麼

Access log 記錄每個到達 collector 的 request — 來源 IP、API key（或 key 的 hash）、操作類型、時間戳、response status。

Access log 的用途：

**安全審計**：發現異常行為 — 未知 IP 的大量寫入、非工作時間的讀取、連續的認證失敗。

**問題排查**：SDK 說事件送出成功但 collector 沒有收到 — access log 可以確認 request 是否到達、response 是什麼。

**用量統計**：每個 client 送了多少事件、佔多少儲存。

Access log 本身也是監控資料，但和業務事件分開儲存。Access log 存在 collector 本機的 log 檔中，用系統的 logrotate 管理輪替。

```text
2026-06-19T10:30:00Z POST /events key=sk_mon_ab...cd ip=192.168.1.50 status=200 size=1234
2026-06-19T10:30:01Z POST /events key=INVALID ip=10.0.0.99 status=401 size=0
2026-06-19T10:31:00Z GET /query key=sk_read_ef...gh ip=192.168.1.1 status=200 size=8901
```

## 下一步路由

- SDK 端的 redaction → [SDK Redaction API 設計](/monitoring/07-security-privacy/sdk-redaction-api/)
- Transport 層的加密 → [Transport 安全](/monitoring/07-security-privacy/transport-security/)
- 資料儲存後的去識別化 → [去識別化策略](/monitoring/07-security-privacy/anonymization-strategy/)
- Client-side credential 暴露的根本限制 → [Client-side SDK 認證](/monitoring/07-security-privacy/client-sdk-authentication/)
