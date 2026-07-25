---
title: "Error Fingerprint 與去重分群"
date: 2026-06-24
description: "把大量 error 事件歸組成可管理的 issue 列表 — fingerprint 演算法、message normalization、error_groups 表設計、自架方案的務實邊界"
weight: 16
tags: ["monitoring", "collector", "error", "fingerprint", "grouping", "dedup"]
---

[Error fingerprint](/monitoring/knowledge-cards/error-fingerprint/) 把相同根因的 error 事件歸為同一組（error group），讓 dashboard 從「每筆 error 獨立一行」變成「同因 error 歸組、顯示 count / first_seen / last_seen / affected_sessions」。這是 error tracking 從「有記錄」演進到「可管理」的關鍵能力。

Collector 搭配的 [Developer Dashboard](/monitoring/04-collector/dashboard-developer/) 在 Error 列表中用 `GROUP BY name` 做分群 — 同名的 error 歸為一行。這在 error name 設計良好時（`terminal.connect.failed` / `auth.biometric.timeout`）可以運作，但在以下情境會失效：

- 同一個 name 對應多個不同的 root cause — `app.exception` 的 stack trace 指向完全不同的程式碼位置
- 不同 name 其實是同一個 root cause — `ws.connect.failed` 和 `ws.reconnect.failed` 都是同一個 server 下線造成

Fingerprint 提供比 name 更精確的分群維度。

## Fingerprint 演算法

Fingerprint 從 error 事件中提取關鍵欄位、計算 hash，相同 hash 的事件歸為同一組。欄位的選擇決定分群的粒度。

### 基礎版：type + message

```text
fingerprint = SHA256(error_type + ":" + error_message)
```

用 `error_type`（`NullPointerException` / `TypeError` / `ConnectionError`）加上 `error_message` 做 hash。實作最簡單，大多數情況下能正確分群。

問題在 error message 包含動態值時。同一個 bug 產生的 error 因為動態值不同而分裂成多組：

```text
"User 12345 not found"  → fingerprint A
"User 67890 not found"  → fingerprint B
```

這兩筆是同一個 bug（查無使用者），但 message 中的 user ID 不同導致 fingerprint 不同。動態值的處理見下方 [message normalization](#message-normalization)。

### 進階版：type + stack trace top frames

```text
fingerprint = SHA256(error_type + ":" + top_3_frames)
```

用 error_type 加上 stack trace 最頂端的 N 個 frame（函式名 + 檔案名 + 行號）做 hash。Stack trace 的頂端通常是 error 發生的直接位置，相同位置的 error 歸為同組。

```text
// 兩筆 error 的 stack trace 頂端相同 → 同一個 fingerprint
TypeError: Cannot read property 'name' of null
  at UserProfile.render (UserProfile.js:42)    ← frame 1
  at Component.update (framework.js:108)       ← frame 2
  at scheduler.flush (framework.js:203)        ← frame 3
```

N 的選擇是粒度 vs 穩定性的取捨。N=1 過粗（不同 bug 可能在同一個函式裡），N=5 過細（重構移動程式碼後行號改變，同一個 bug 的 fingerprint 分裂）。N=3 是常見的預設值。

Stack trace 版本的前提是 error 事件帶有結構化的 stack trace。如果 SDK 只送 error message 不送 stack trace，只能用基礎版。

### Sentry 的做法

Sentry 的策略核心是只用應用程式自身的 frame 做 hash，排除 framework / library 的 frame，並 normalize message 中的動態值。具體做法：

1. **取 in-app frame**：忽略 framework / library 的 frame（`framework.js`、`node_modules/`），只用應用程式自身的 frame。同一個 bug 在不同版本的 framework 上觸發時，framework frame 可能不同，但 app frame 相同。
2. **Normalize message**：移除動態值（數字、UUID、email）後再 hash。
3. **取最後一個 in-app frame 的函式名**：而非取前 N 個 frame。最後一個 in-app frame 是「error 在應用程式碼中實際發生的位置」。

Sentry 的策略對 web 前端（大量 framework frame）和行動 app（大量 OS / runtime frame）的分群效果好，但實作複雜度高 — 需要維護「什麼算 in-app frame」的規則。

### SDK 端自定義 fingerprint

SDK 端可以手動指定 fingerprint，覆蓋 collector 的自動計算。用途是讓開發者把「技術上不同但業務上同因」的 error 歸為同組。

```python
monitor.error("API timeout", data={
    "fingerprint": "api-gateway-timeout",
    "endpoint": "/v1/users",
    "duration_ms": 30000
})
```

所有帶 `fingerprint: "api-gateway-timeout"` 的 error，無論 message 和 stack trace 是否相同，都歸入同一組。

自定義 fingerprint 的處理邏輯：collector 收到事件時，先檢查 `data.fingerprint` 欄位是否存在。存在則直接用這個值做 hash（或直接用作 fingerprint），不走自動計算。

## Message normalization

動態值讓相同 bug 的 message 不同，導致 fingerprint 分裂。Normalization 在計算 fingerprint 前把動態值替換成 placeholder。

### 替換規則

| Pattern                      | 替換為     | 範例                                                                      |
| ---------------------------- | ---------- | ------------------------------------------------------------------------- |
| 連續數字（3 位以上）         | `{N}`      | `"User 12345 not found"` → `"User {N} not found"`                         |
| UUID                         | `{uuid}`   | `"Session a1b2...7890 expired"` → `"Session {uuid} expired"`              |
| Email                        | `{email}`  | `"Invalid email foo@bar.com"` → `"Invalid email {email}"`                 |
| IPv4 / IPv6                  | `{ip}`     | `"Connection to 192.168.1.100 refused"` → `"Connection to {ip} refused"`  |
| 引號內的字串（超過 20 字元） | `{string}` | `"Key 'very-long-dynamic-key...' not found"` → `"Key {string} not found"` |
| 絕對路徑的使用者目錄         | `{path}`   | `"/Users/john/project/app.js"` → `"{path}/project/app.js"`                |
| ISO 8601 timestamp           | `{ts}`     | `"Error at 2026-06-24T14:30:00"` → `"Error at {ts}"`                      |

後兩個屬進階規則 — 基礎五個（數字 / UUID / email / IP / 長字串）在多數場景足夠，file path 和 timestamp 在 error group 分裂嚴重時再加。

```go
var normalizers = []struct {
    pattern *regexp.Regexp
    replace string
}{
    {regexp.MustCompile(`\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b`), "{uuid}"},
    {regexp.MustCompile(`\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`), "{email}"},
    {regexp.MustCompile(`\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b`), "{ip}"},
    {regexp.MustCompile(`\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}`), "{ts}"},
    {regexp.MustCompile(`(?:/Users/|/home/|C:\\Users\\)[^/\\]+`), "{path}"},
    {regexp.MustCompile(`\d{3,}`), "{N}"},
}

func normalizeMessage(msg string) string {
    for _, n := range normalizers {
        msg = n.pattern.ReplaceAllString(msg, n.replace)
    }
    return msg
}
```

### Normalization 的風險

**過度 normalize**：把實際不同的 error 歸為同組。例如 HTTP status code `404` 和 `500` 都被替換成 `{N}`，導致 `"HTTP {N}"` 把 404 和 500 混在一起。對策：HTTP status code 等已知語意數字用具名 pattern 優先保留（`(\b[1-5]\d{2}\b)` → 不替換），再跑通用數字替換。Normalizer 的規則順序決定優先級 — 具名 pattern 放在 `\d{3,}` 之前，匹配到的數字跳過後續替換。

**不足 normalize**：遺漏動態值導致同因 error 分裂。例如 message 中包含時間戳 `"Error at 2026-06-24T14:30:00"` 但 normalization 沒有覆蓋 ISO 8601 格式。對策：先用基礎規則上線，根據 error group 的分裂狀況逐步補規則 — 同一個 error 名稱下有大量 group 且 stack trace 相同，通常代表 normalization 不足。

## Storage 設計

Fingerprint 的儲存分兩部分：events 表加 fingerprint 欄位、新建 error_groups 表追蹤每組的摘要。

### Events 表擴充

在[現有的 events 表](/monitoring/04-collector/scaling-evolution/)加 `fingerprint` 欄位：

```sql
ALTER TABLE events ADD COLUMN fingerprint TEXT;
CREATE INDEX idx_fingerprint ON events(fingerprint);
```

`fingerprint` 存 hash 值（SHA256 hex 的前 16 字元足夠 — 自架場景的 error 種類不會多到 collision）。索引加速「查看某個 error group 的所有事件」查詢。

### error_groups 表

```sql
CREATE TABLE error_groups (
    fingerprint TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    error_type TEXT,
    normalized_message TEXT,
    count INTEGER NOT NULL DEFAULT 1,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    last_event_id INTEGER REFERENCES events(id),
    session_count INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'open'
);

CREATE INDEX idx_error_groups_last_seen ON error_groups(last_seen);
CREATE INDEX idx_error_groups_count ON error_groups(count);
```

`status` 支援基本的 issue 管理 — `open`（待處理）、`resolved`（已修復）、`ignored`（已知、不處理）。Resolved 的 group 如果又收到新事件，自動 reopen。

### 寫入流程

Collector 的寫入 pipeline 在 schema validation 之後、storage 寫入之前，加一步 fingerprint 計算。下方的 UPSERT 邏輯引用 events 表的 `session_id` 欄位 — 該欄位定義在 [Events 主表 DDL](/monitoring/04-collector/scaling-evolution/) 中（從 `session.id` 攤平而來）：

```text
HTTP → Schema validation → Fingerprint 計算 → Events INSERT → error_groups UPSERT
```

```go
func processErrorEvent(event Event) {
    fp := calculateFingerprint(event)
    event.Fingerprint = fp

    // 1. INSERT event
    db.InsertEvent(event)

    // 2. UPSERT error_group
    db.Exec(`
        INSERT INTO error_groups (fingerprint, name, error_type, normalized_message,
                                  count, first_seen, last_seen, last_event_id, session_count)
        VALUES (?, ?, ?, ?, 1, ?, ?, ?, 1)
        ON CONFLICT(fingerprint) DO UPDATE SET
            count = count + 1,
            last_seen = excluded.last_seen,
            last_event_id = excluded.last_event_id,
            session_count = session_count + CASE
                WHEN ? NOT IN (SELECT DISTINCT session_id FROM events WHERE fingerprint = ?)
                THEN 1 ELSE 0 END,
            status = CASE WHEN status = 'resolved' THEN 'open' ELSE status END
    `, fp, event.Name, event.ErrorType, normalizeMessage(event.ErrorMessage),
       event.Timestamp, event.Timestamp, event.ID, event.SessionID, fp)
}
```

`session_count` 的子查詢在高寫入量下可能成為瓶頸。務實的替代是在 UPSERT 時不算 session_count，改為定期 job 重新計算（每小時一次）。

### 查詢模式

Dashboard 的 Error 列表從 `GROUP BY name` 改為查 error_groups 表：

```sql
-- 之前：按 name 分群（粗略）
SELECT name, COUNT(*) FROM events WHERE type = 'error' GROUP BY name;

-- 之後：按 fingerprint 分群（精確）
SELECT fingerprint, name, error_type, normalized_message,
       count, first_seen, last_seen, session_count, status
FROM error_groups
WHERE status != 'ignored'
ORDER BY last_seen DESC;
```

error_groups 表的查詢是 index scan，不需要掃描 events 表。Dashboard 刷新頻率高的場景下（每 30 秒），查 error_groups 比 `GROUP BY` 全表掃描快幾個數量級。

點擊某個 group 進入詳情時，再用 fingerprint 從 events 表撈最近 N 筆事件：

```sql
SELECT * FROM events WHERE fingerprint = ? ORDER BY ts DESC LIMIT 20;
```

## Dashboard 整合

Error fingerprint 改變了 [Developer Dashboard](/monitoring/04-collector/dashboard-developer/) 的 Error 列表和詳情視圖。

### Error 列表升級

從按 name 分群升級為按 fingerprint 分群：

| 欄位               | 之前（name 分群）       | 之後（fingerprint 分群）    |
| ------------------ | ----------------------- | --------------------------- |
| 分群維度           | error.name              | fingerprint hash            |
| 同名不同因的 error | 混在同一行              | 各自獨立一行                |
| 不同名同因的 error | 分開兩行                | 可用自定義 fingerprint 合併 |
| 影響 session 數    | 每次查詢都做 DISTINCT   | error_groups 表預計算       |
| Status 管理        | 無                      | open / resolved / ignored   |
| 查詢效能           | GROUP BY 掃描 events 表 | 直接查 error_groups 表      |

### Error 詳情升級

點擊某個 error group 進入詳情，顯示：

- **代表性 stack trace**：最近一次事件的 stack trace，讓開發者看到 error 的具體位置
- **Normalized message**：去除動態值後的 error message，一目了然這個 group 代表什麼問題
- **趨勢**：這個 group 的事件量隨時間的變化（上升 = 越來越多使用者遇到、下降 = 可能自行恢復）
- **受影響版本**：按 `source.version` 分佈 — 新版本出現的 group 通常是 regression
- **受影響平台**：按 `source.platform` 分佈 — 只影響特定平台的 group 通常是平台特定 bug

## 自架方案的務實邊界

自架 collector 的 fingerprint 機制和 [Sentry](/monitoring/06-commercial-comparison/sentry-deep-dive/) 等商業方案有明確的能力差距。

### Stack trace 可讀性

Stack trace 分群的前提是 stack trace 可讀 — frame 的函式名和檔名對應原始碼。兩種情境下 stack trace 會變成不可讀：

**Minified JS**：production 環境的 JS 經過 minify 後，stack trace 變成 `a.js:1:2345`，無法定位原始碼位置。Sentry 支援上傳 source map，在 server 端自動反解。自架方案的對策：開發期使用未 minify 的 JS（stack trace 直接對應原始碼）；production 環境如果用 minify，需要自建 source map server 或放棄 JS 的 stack trace 分群、改用 error name + message 做 fingerprint。

**Android ProGuard / R8 混淆**：混淆後 stack trace 的類名和方法名是 `a.b.c()`。Sentry 和 Crashlytics 支援上傳 mapping file 反混淆。自架方案如果目標平台包含 Android native（非 Flutter），需要自建 mapping 反混淆流程。

Flutter 和 Python 不受上述影響 — Flutter 的 debug / profile build 保留完整 stack trace，Dart 有自己的 stack trace 格式不經過 ProGuard；Python 的 stack trace 永遠包含原始檔名和行號。

### ML-based grouping

Sentry 的進階 grouping 使用機器學習判斷「語意相同但結構不同」的 error 是否該歸為同組。例如同一個 bug 因為 async/await 的 call chain 不同而產生不同的 stack trace，ML 模型能辨識它們是同一個 root cause。

自架方案用規則（fingerprint 演算法 + normalization）做 grouping。規則的覆蓋率低於 ML — 遇到規則沒覆蓋的情境時，需要手動加 normalization 規則或用 SDK 端自定義 fingerprint 修正。

### 能力定位

| 能力               | 自架方案                         | Sentry                                    |
| ------------------ | -------------------------------- | ----------------------------------------- |
| 基礎分群           | type + normalized message        | type + in-app frame + ML                  |
| Stack trace 分群   | top N frames（明文 stack trace） | in-app frame + source map + deobfuscation |
| 自定義 fingerprint | SDK 端 `data.fingerprint`        | SDK 端 + server-side rule                 |
| Message normalize  | regex 替換                       | regex + ML                                |
| Issue 管理         | open / resolved / ignored        | + assign / merge / snooze / trend         |

基礎分群和 message normalization 覆蓋自架場景的多數需求。Stack trace 分群在明文 stack trace 的場景下（Python / Flutter / 未 minify 的 JS）和 Sentry 效果相當。差距主要在 minified / obfuscated 環境和 ML-based grouping — 這兩者恰好是商業方案的核心付費價值。

## 下一步路由

- Error 列表和趨勢的日常監控 → [Developer Dashboard 設計](/monitoring/04-collector/dashboard-developer/)
- Collector 的處理鏈路 → [Collector 架構](/monitoring/04-collector/architecture/)
- 偽造 error 的辨識 → [Client-side SDK 認證](/monitoring/07-security-privacy/client-sdk-authentication/)
- Sentry 的 error tracking 架構 → [Sentry 深入](/monitoring/06-commercial-comparison/sentry-deep-dive/)
- Error 事件的端到端完整性 → [端到端資料完整性](/monitoring/04-collector/data-integrity/)
