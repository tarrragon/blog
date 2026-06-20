---
title: "從 collector 資料做基礎 funnel 分析"
date: 2026-06-19
description: "SQLite 層能做什麼程度的 funnel、PostgreSQL 層提供什麼進階能力、JSONL 匯出後的臨時分析"
weight: 8
tags: ["monitoring", "analytics", "funnel", "self-hosted", "collector", "sqlite", "postgresql"]
---

自架 collector 收集的事件資料可以做基礎的 funnel 分析，不需要商業方案。分析的深度取決於 storage backend 的查詢能力 — SQLite 層能做每步事件計數，PostgreSQL 層能做 session 級轉換率分析。功能分層的完整定義見 [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)。

## 定義 funnel 步驟

Funnel 分析的第一步是列出每一步和對應的事件名稱。以一個透過 WebSocket 連接遠端終端機的 app 連線流程為例：

| 步驟 | 事件名稱               | 意義               |
| ---- | ---------------------- | ------------------ |
| 1    | terminal.connect.start | 使用者點擊連線     |
| 2    | auth.biometric.success | 生物辨識通過       |
| 3    | terminal.connect.done  | WebSocket 連線成功 |
| 4    | terminal.input.submit  | 使用者開始打字     |

## SQLite 層：每步事件計數

SQLite backend 能做的 funnel 是「每步有多少事件觸發」— 單表 GROUP BY，不需要跨事件 JOIN。

```sql
SELECT name, COUNT(*) as count
FROM events
WHERE name IN ('terminal.connect.start', 'auth.biometric.success',
               'terminal.connect.done', 'terminal.input.submit')
  AND ts >= datetime('now', '-7 days')
GROUP BY name;
```

步驟 N 的轉換率 = 步驟 N 的事件數 / 步驟 N-1 的事件數。流失率 = 1 - 轉換率。

### 能做的

- 每步事件計數（單表 GROUP BY）
- 按 source.version 或 source.platform 分群（加 WHERE 條件）
- 按天/按週看趨勢（strftime 分桶 + GROUP BY）

### 做不到的

- **Session 級轉換率**：「同一個 session 完成步驟 1 到步驟 4 的比例」需要 JOIN 同 session 的多個事件、跨所有 session 聚合。SQLite 能做這個 JOIN，但在大量 session 時效能不足。
- **步驟間耗時**：「使用者在步驟 1 和步驟 2 之間等了多久」需要 self-join on session_id + timestamp 差值計算。
- **漏斗順序驗證**：確認使用者是按 1→2→3→4 順序完成、不是跳步。

## PostgreSQL 層：Session 級 funnel

PostgreSQL backend 提供 window function 和高效 JOIN，能做完整的 session 級 funnel 分析。

```sql
WITH session_steps AS (
  SELECT session_id, name,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY ts) as step_order
  FROM events
  WHERE name IN ('terminal.connect.start', 'auth.biometric.success',
                 'terminal.connect.done', 'terminal.input.submit')
    AND ts >= NOW() - INTERVAL '7 days'
),
session_max_step AS (
  SELECT session_id, MAX(step_order) as reached
  FROM session_steps
  GROUP BY session_id
)
SELECT reached, COUNT(*) as sessions
FROM session_max_step
GROUP BY reached
ORDER BY reached;
```

### 新增能力

- **Session 級轉換率**：每個 session 到達了哪一步、在哪一步流失
- **步驟間耗時**：LAG window function 計算相鄰步驟的 timestamp 差值
- **漏斗順序驗證**：用 ROW_NUMBER + CASE 確認步驟順序
- **Cohort 分群的 funnel**：按使用者註冊日期 / 版本 / 平台分群看不同 cohort 的 funnel 差異

## JSONL 匯出後的臨時分析

Collector 的 `monitor export --format=jsonl` 可以匯出事件為 JSONL 格式。匯出後用 grep + jq 做一次性的臨時分析：

```bash
for step in terminal.connect.start auth.biometric.success terminal.connect.done terminal.input.submit; do
  count=$(grep "\"name\":\"$step\"" exported-events.jsonl | wc -l)
  echo "$step: $count"
done
```

JSONL 臨時分析適合「快速看一眼大概數字」的場景。持續性的 funnel 監控應該用 SQLite 或 PostgreSQL 的 SQL 查詢，結果穩定且可重現。

## 自架 vs 商業方案

| 需求                 | 自架能力                   | 商業方案                       |
| -------------------- | -------------------------- | ------------------------------ |
| 每步事件計數         | SQLite GROUP BY            | Mixpanel / Amplitude 內建      |
| Session 級轉換率     | PostgreSQL window function | Mixpanel / Amplitude 內建      |
| 視覺化 funnel 漏斗圖 | 自建 dashboard             | 商業方案內建、拖拉設定         |
| 即時更新             | 定期重算 + dashboard 刷新  | 商業方案即時                   |
| A/B test 分群 funnel | PostgreSQL + feature flag  | Optimizely / LaunchDarkly 整合 |

自用工具場景下，SQLite 層的每步事件計數通常足夠。商業產品需要 session 級分析時，PostgreSQL 層的 SQL 能力和商業方案的分析能力在功能上對等，差異在 UI 和設定便利性。

## 下一步路由

- Funnel 分析的完整方法論 → [Funnel analysis](/monitoring/08-business-analytics/funnel-analysis/)
- 事件設計如何影響分析品質 → [行為事件設計](/monitoring/08-business-analytics/behavior-event-design/)
- 功能分層定義 → [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)
- 去識別化是分析的入場條件 → [模組七 資安與隱私](/monitoring/07-security-privacy/)
