---
title: "查詢消費模式"
date: 2026-06-20
description: "Debug / Alerting / 產品決策 / 安全審計 / 效能監控 — 五種查詢場景各需要什麼事件、什麼欄位、什麼查詢模式"
weight: 7
tags: ["monitoring", "collector", "query", "consumption", "debug", "alerting", "audit"]
---

事件的價值在於被查詢消費。設計事件時反過來想：查詢需要什麼欄位 → 事件需要帶什麼 data → 感測器需要在什麼時機觸發。從消費端反推設計，避免「收了一堆事件但查不到想要的答案」。

五種查詢場景各自需要不同的事件類型、欄位和查詢模式。每種場景的查詢模式也決定了需要 SQLite 層還是 PostgreSQL 層（見 [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)）。

## Debug 查詢

Debug 查詢回答「問題出在哪」。觸發時機是使用者回報問題或 error alert 觸發後，開發者需要還原問題的 context。

### 查詢場景

#### 剛才使用者回報的問題

查詢模式：用 session_id 過濾，拉出該 session 的全部事件，按時間排序。

```sql
-- SQLite
SELECT type, name, ts, data
FROM events
WHERE session_id = 'abc-123'
ORDER BY ts;
```

需要的事件欄位：session_id（關聯同次使用的事件）、ts（排序）、error 的 stack trace 和 step（定位失敗點）。

#### 這個 error 多常發生

查詢模式：按 error name 分群計數，看時間趨勢。

```sql
-- SQLite
SELECT name, COUNT(*) as count,
       strftime('%Y-%m-%d', ts) as day
FROM events
WHERE type = 'error'
  AND ts >= datetime('now', '-7 days')
GROUP BY name, day
ORDER BY day, count DESC;
```

需要的事件欄位：type='error'、name（分群鍵）、ts（時間分桶）。

### 需要的事件

| 事件類型  | 必要欄位                      | 用途                      |
| --------- | ----------------------------- | ------------------------- |
| error     | stack_trace, step, session_id | 定位失敗點 + 關聯 session |
| event     | name, session_id              | 還原使用者操作路徑        |
| lifecycle | name, session_id              | 還原系統狀態轉換          |

## Alerting 查詢

Alerting 查詢回答「需要注意嗎」。分兩種機制：rule engine 的即時評估（事件到達時逐筆比對規則）和事後查詢的趨勢分析。

### 查詢場景

#### Error 數量突然上升

查詢模式：最近 1 小時的 error 計數 vs 前一天同時段，偏差超過閾值則告警。

```sql
-- SQLite
SELECT COUNT(*) as recent_count
FROM events
WHERE type = 'error'
  AND ts >= datetime('now', '-1 hour');
```

Rule engine 的即時版：每收到一筆 error 事件，遞增計數器，計數器超過閾值觸發動作。

#### 特定 error 首次出現

查詢模式：收到 error 時查是否有歷史記錄。

```sql
-- SQLite
SELECT COUNT(*) FROM events
WHERE type = 'error' AND name = ?
  AND ts < ?;
```

結果為 0 代表首次出現 — 觸發「新 error 類型」告警。Sentry 的核心功能之一就是這個查詢。

### Rule engine vs 事後查詢

Rule engine 逐筆評估，延遲在毫秒級，適合「error 出現就通知」。事後查詢用 SQL 聚合，延遲在秒到分鐘級，適合「過去一小時的 error 趨勢」。兩者互補 — rule engine 做即時告警、SQL 查詢做事後分析。

### 需要的事件

| 事件類型 | 必要欄位       | 用途                       |
| -------- | -------------- | -------------------------- |
| error    | name, ts       | 計數 + 時間趨勢            |
| error    | source.version | 按版本分群看是否新版本引入 |

## 產品決策查詢

產品決策查詢回答「使用者怎麼用產品」。從簡單的功能使用率到複雜的 funnel 分析。

### 查詢場景

#### 新功能有多少人用

查詢模式：按 event name 計數。SQLite 層即可。

```sql
-- SQLite
SELECT name, COUNT(*) as count,
       COUNT(DISTINCT session_id) as unique_sessions
FROM events
WHERE type = 'event'
  AND name LIKE 'new_feature.%'
  AND ts >= datetime('now', '-7 days')
GROUP BY name;
```

#### 註冊流程在哪流失

查詢模式：session 級 funnel JOIN。需要 PostgreSQL 層。

```sql
-- PostgreSQL
WITH session_steps AS (
  SELECT session_id, name,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY ts) as step_order
  FROM events
  WHERE name IN ('signup.start', 'signup.email', 'signup.verify', 'signup.complete')
    AND ts >= NOW() - INTERVAL '30 days'
)
SELECT name, COUNT(DISTINCT session_id) as sessions
FROM session_steps
GROUP BY name
ORDER BY MIN(step_order);
```

完整的 funnel 分析方法論見 [從 collector 資料做基礎 funnel 分析](/monitoring/08-business-analytics/self-hosted-funnel/)。

### 需要的事件

| 事件類型  | 必要欄位             | 用途               |
| --------- | -------------------- | ------------------ |
| event     | name, session_id, ts | 漏斗步驟計數和排序 |
| lifecycle | session.start, ts    | session 邊界定義   |

## 安全審計查詢

安全審計查詢回答「有沒有非預期的存取」。重點是偵測異常模式而非單筆事件。

### 查詢場景

#### 有沒有異常登入

查詢模式：auth 失敗事件按 session 分群計數，短時間內大量失敗 = 暴力破解嘗試。

```sql
-- SQLite
SELECT session_id, COUNT(*) as fail_count,
       MIN(ts) as first_attempt, MAX(ts) as last_attempt
FROM events
WHERE type = 'error' AND name = 'auth.login.failed'
  AND ts >= datetime('now', '-1 hour')
GROUP BY session_id
HAVING fail_count > 5;
```

#### 誰存取了什麼敏感資料

查詢模式：敏感操作的 audit trail — 按時間列出所有敏感操作事件。

```sql
-- SQLite
SELECT ts, session_id, name, data
FROM events
WHERE type = 'event'
  AND name IN ('data.export', 'admin.user_lookup', 'config.secret_read')
ORDER BY ts DESC;
```

### 需要的事件

| 事件類型 | 必要欄位                         | 用途         |
| -------- | -------------------------------- | ------------ |
| error    | name='auth.*.failed', session_id | 偵測暴力破解 |
| event    | 敏感操作的 name, session_id      | audit trail  |
| event    | data 中的操作目標（哪筆資料）    | 存取範圍追溯 |

安全事件的取樣率必須是 1.0（全收）— 取樣會讓攻擊嘗試在統計上隱形。見 [感測器生命週期管理](/monitoring/03-sdk-design/sensor-lifecycle-management/) 的取樣率設計段。

## 效能查詢

效能查詢回答「系統有多快」和「哪裡變慢了」。

### 查詢場景

#### P95 回應時間趨勢

查詢模式：時間分桶 + percentile 聚合。需要 PostgreSQL 層。

```sql
-- PostgreSQL
SELECT date_trunc('hour', ts) as hour,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY (data->>'duration_ms')::int) as p95
FROM events
WHERE type = 'metric' AND name = 'api.response.duration'
  AND ts >= NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour;
```

SQLite 沒有內建 percentile 函數。SQLite 層的替代方案是排序後取第 95% 位置的值，但在大資料量時效能差。

#### 哪個版本變慢了

查詢模式：按 source.version 分群比較效能。

```sql
-- SQLite / PostgreSQL
SELECT source_version, AVG((data->>'duration_ms')::int) as avg_ms,
       COUNT(*) as sample_count
FROM events
WHERE type = 'metric' AND name = 'api.response.duration'
  AND ts >= datetime('now', '-7 days')
GROUP BY source_version;
```

### 需要的事件

| 事件類型 | 必要欄位                         | 用途         |
| -------- | -------------------------------- | ------------ |
| metric   | name, data.duration_ms, ts       | 延遲趨勢     |
| metric   | source.version                   | 按版本比較   |
| metric   | data.memory_mb, data.cpu_percent | 資源使用趨勢 |

## 查詢 → 事件反推表

設計事件時用這張表反向確認：每種查詢場景需要什麼事件、什麼欄位、什麼 storage 層級。

| 查詢場景       | 事件類型 | 必要欄位                  | Storage 層級 | 保留需求     |
| -------------- | -------- | ------------------------- | ------------ | ------------ |
| Session 回放   | 全部     | session_id, ts            | SQLite       | 原始 7d      |
| Error 計數趨勢 | error    | name, ts                  | SQLite       | 小時聚合 90d |
| 功能使用率     | event    | name                      | SQLite       | 天聚合 365d  |
| Funnel 分析    | event    | name, session_id, ts      | PostgreSQL   | 原始 30d     |
| 暴力破解偵測   | error    | auth name, session_id     | SQLite       | 原始 30d     |
| Audit trail    | event    | 敏感操作 name, session_id | SQLite       | 原始 365d    |
| P95 趨勢       | metric   | duration_ms, ts           | PostgreSQL   | 小時聚合 90d |
| 版本比較       | metric   | duration_ms, version      | SQLite       | 天聚合 365d  |

這張表和 [事件枚舉與補齊檢查](/monitoring/01-mental-model/event-enumeration-method/) 的事件表互補 — 事件枚舉從操作端正向推導「要收什麼」，本表從查詢端反向確認「收的夠不夠」。

## 下一步路由

- 從操作端正向推導事件 → [事件枚舉與補齊檢查](/monitoring/01-mental-model/event-enumeration-method/)
- 動機和事件的對應關係 → [動機驅動的事件設計](/monitoring/01-mental-model/motivation-to-event-mapping/)
- SQLite vs PostgreSQL 的查詢能力分界 → [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)
- Rule engine 的即時評估 → [Rule engine 設計](/monitoring/04-collector/rule-engine/)
