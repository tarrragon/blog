---
title: "Developer Dashboard 設計"
date: 2026-06-20
description: "Bug 在哪、多嚴重、怎麼重現 — Error 列表和趨勢的日常監控、Session 回放和 Stack trace 的深入 debug"
weight: 9
tags: ["monitoring", "collector", "dashboard", "developer", "error-tracking", "debug"]
---

Developer dashboard 聚焦 error 追蹤和 debug。開發者的核心問題是「哪裡壞了、影響多少人、怎麼重現」。這個 dashboard 的所有視圖都圍繞 error 事件展開，其他三類事件（event / metric / lifecycle）作為 debug context 輔助。

和 [DevOps dashboard](/monitoring/04-collector/dashboard-devops/) 的差異：DevOps 看「基礎設施是否健康」，Developer 看「程式碼是否正確」。Error 趨勢上升在 DevOps 眼中是「事件量異常」，在 Developer 眼中是「程式碼 bug」。

## 日常監控視圖

### Error 摘要

一個數字卡顯示最近 24 小時的 error 總數 + 和前一天的比較（上升 / 下降 / 持平）。旁邊標注「新 error」數量 — 過去 24 小時首次出現的 error name。

新 error 的偵測邏輯：`error.name` 在最近 24 小時的事件中存在、但在更早的事件中不存在。這是開發者最需要立即注意的 — 新版本引入的 bug 通常表現為「之前沒見過的 error name」。

### Error 列表

表格按 `error.name` 分群，每行顯示：error 名稱、最近 24 小時出現次數、影響的 session 數、首次出現時間、最近出現時間。按出現次數降序排列。

點擊某行進入 Error 詳情視圖。

```sql
-- SQLite 層可用
SELECT name,
       COUNT(*) as count,
       COUNT(DISTINCT session_id) as sessions,
       MIN(ts) as first_seen,
       MAX(ts) as last_seen
FROM events
WHERE type = 'error'
  AND ts >= datetime('now', '-1 day')
GROUP BY name
ORDER BY count DESC;
```

### Error 趨勢

折線圖顯示過去 7 天每天的 error 數量。可選按 `error.name` 過濾看單一 error 的趨勢，或看全部 error 的總趨勢。

趨勢的判讀訊號：

- 穩定持平 → 已知的 recurring error，排優先處理
- 新版本部署後突然上升 → 該版本引入的 regression
- 逐漸上升 → 累積性問題（記憶體洩漏、資源耗盡）

### 版本健康

按 `source.version` 分群的 error 率比較。每個版本顯示：error 數量、error rate（error / 總事件比）、最常見的 error name。

版本健康視圖幫助判斷「這個版本該不該 rollback」— 如果新版本的 error rate 顯著高於前一版，rollback 決策有數字依據。

## Debug 深入視圖

從日常監控的 Error 列表點擊某個 error 進入深入視圖。

### Error 詳情

單個 error name 的完整資訊：

- Stack trace（最近一次出現的 `error.data.stack_trace`）
- 首次出現時間和總出現次數
- 影響的 session 數和佔比
- 按版本分佈（哪些版本有、哪些沒有）
- 按平台分佈（iOS / Android / Web）
- 最近 10 次出現的時間軸

### Session 回放

選擇一個受影響的 session，顯示該 session 的完整事件序列。事件按時間排列，每筆事件顯示類型、名稱、時間、data 摘要。Error 事件用顯眼的樣式標記，讓開發者快速定位「error 發生前使用者做了什麼」。

Session 回放需要同一個 session_id 的所有四類事件。這是 event-enumeration-method 中「Debug — 最近操作」事件的核心消費場景。

```sql
-- SQLite 層可用
SELECT type, name, ts, data
FROM events
WHERE session_id = ?
ORDER BY ts;
```

### 平台分佈

某個 error name 在不同平台和 OS 版本的分佈圖。幫助判斷「這個 error 是全平台問題、還是特定平台的 bug」。

```sql
-- SQLite 層可用
SELECT json_extract(source, '$.platform') as platform,
       json_extract(source, '$.os') as os_version,
       COUNT(*) as count
FROM events
WHERE type = 'error' AND name = ?
GROUP BY platform, os_version;
```

## 事件覆蓋確認

Developer dashboard 需要的所有事件在目前的事件設計中已完整覆蓋：

| 視圖         | 需要的事件                    | 對應的事件名稱                  | 覆蓋狀態 |
| ------------ | ----------------------------- | ------------------------------- | -------- |
| Error 列表   | error GROUP BY name           | `app.exception`                 | 已覆蓋   |
| Error 趨勢   | error 時間序列                | `app.exception`                 | 已覆蓋   |
| 版本比較     | error GROUP BY source.version | `app.exception` + source schema | 已覆蓋   |
| Session 回放 | 同 session 全部事件           | 四類事件 + session_id           | 已覆蓋   |
| Stack trace  | error.data.stack_trace        | `app.exception` data 欄位       | 已覆蓋   |
| 影響範圍     | COUNT DISTINCT session_id     | session_id schema               | 已覆蓋   |
| 平台分佈     | GROUP BY source.platform      | source schema                   | 已覆蓋   |

## SQLite 層 vs PostgreSQL 層

Developer dashboard 的多數視圖在 SQLite 層就能運作 — 都是單表 GROUP BY 和 WHERE 過濾。

| 視圖            | SQLite 層        | PostgreSQL 層新增     |
| --------------- | ---------------- | --------------------- |
| Error 列表      | 可用             |                       |
| Error 趨勢      | 可用（7 天以內） | 長期趨勢（30 天以上） |
| 版本比較        | 可用             |                       |
| Session 回放    | 可用             |                       |
| 平台分佈        | 可用             |                       |
| Error 詳情      | 可用             |                       |
| 跨版本 P95 回應 | 不可用           | percentile 函數       |

開發者 debug 場景不需要 PostgreSQL — SQLite 層的查詢能力已涵蓋所有核心視圖。PostgreSQL 的需求來自效能指標的高級分析（P95 趨勢），但這屬於效能監控動機而非 debug 動機。

## 下一步路由

- DevOps dashboard 設計 → [DevOps Dashboard 設計](/monitoring/04-collector/dashboard-devops/)
- 中台 dashboard 設計 → [中台 Dashboard 設計](/monitoring/04-collector/dashboard-business/)
- Error 事件的枚舉方法 → [事件枚舉與補齊檢查](/monitoring/01-mental-model/event-enumeration-method/)
- 功能分層與 Backend 選擇 → [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)
