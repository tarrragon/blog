---
title: "從 collector 資料做基礎 funnel 分析"
date: 2026-06-19
description: "自架 collector 的 JSONL 資料能做到什麼程度的 funnel 分析 — grep + jq 的能力邊界和商業方案的差距"
weight: 8
tags: ["monitoring", "analytics", "funnel", "self-hosted", "collector"]
---

自架 collector 收集的事件資料可以做基礎的 funnel 分析，不需要商業方案。分析的深度取決於事件設計的品質和查詢工具的能力。grep + jq 能處理的規模和複雜度有明確邊界，超過邊界時需要升級工具鏈。

## 自架 funnel 分析的基本流程

Funnel 分析的本質是「計算每一步有多少使用者完成，多少使用者流失」。從 JSONL 資料做 funnel 分析的步驟：

### 定義 funnel 步驟

列出 funnel 的每一步和對應的事件名稱。以一個透過 WebSocket 連接遠端終端機的 app 連線流程為例：

| 步驟 | 事件名稱               | 意義               |
| ---- | ---------------------- | ------------------ |
| 1    | terminal.connect.start | 使用者點擊連線     |
| 2    | auth.biometric.success | 生物辨識通過       |
| 3    | terminal.connect.done  | WebSocket 連線成功 |
| 4    | terminal.input.submit  | 使用者開始打字     |

### 從 JSONL 提取計數

```bash
# 每步的事件數量
for step in terminal.connect.start auth.biometric.success terminal.connect.done terminal.input.submit; do
  count=$(grep "\"name\":\"$step\"" events-2026-06-19.jsonl | wc -l)
  echo "$step: $count"
done
```

### 計算轉換率

步驟 N 的轉換率 = 步驟 N 的事件數 / 步驟 N-1 的事件數。流失率 = 1 - 轉換率。

## 按 session 分析

上述的事件計數假設「每筆事件獨立」，但 funnel 分析通常需要按 session 分組 — 同一個 session 中使用者是否完成了所有步驟。

按 session 分析需要的查詢複雜度比單純計數高：

```bash
# 提取每個 session 觸發過的事件集合
jq -s 'group_by(.session.id) | map({
  session: .[0].session.id,
  events: [.[].name] | unique
})' events-2026-06-19.jsonl
```

jq 能處理這個查詢，但前提是單日的 JSONL 檔案能完整載入記憶體。數萬筆事件（數 MB）沒有問題；數百萬筆事件（數百 MB）會讓 jq 記憶體不足。

## grep + jq 的能力邊界

### 能做的

- 單步事件計數（grep + wc）
- 單日的 session 分組分析（jq -s）
- 簡單的轉換率計算（shell 腳本）
- 按 source.version 或 source.platform 分群（grep + jq filter）

### 做不到或做得很慢的

- **跨天的 session 分析**：使用者的 session 跨越午夜時，事件分散在兩個 JSONL 檔案。需要合併多個檔案再分析。
- **時間窗口分析**：「使用者在步驟 1 和步驟 2 之間等了多久」需要 join 兩筆事件的 timestamp。grep 無法做 join。
- **即時更新**：grep 是批次查詢，無法即時更新 funnel 數字。需要串流處理。
- **大規模資料**：超過百萬筆事件時 jq -s 記憶體不足，grep 查詢秒級變成分鐘級。

## 超過邊界時的升級路徑

| 需求               | 工具升級                        | 複雜度     |
| ------------------ | ------------------------------- | ---------- |
| 跨天 session 分析  | 合併 JSONL + jq，或 SQLite      | 低         |
| 時間窗口分析       | SQLite（JOIN on session_id）    | 中         |
| 即時更新 dashboard | SQLite + 定期重算 + 簡單 web UI | 中         |
| 百萬級事件         | PostgreSQL / ClickHouse         | 高         |
| 商業級 funnel UI   | 接入 Mixpanel / Amplitude       | 高（成本） |

自用工具場景下，grep + jq 通常足夠 — 使用者數量為 1（開發者本人），事件量在數千級，分析頻率低（debug 時才查）。商業產品場景下，SQLite 是合理的第一步升級，提供 SQL 查詢能力而不引入外部服務依賴。

## 下一步路由

- Funnel 分析的完整方法論 → [Funnel analysis](/monitoring/08-business-analytics/funnel-analysis/)
- 事件設計如何影響分析品質 → [行為事件設計](/monitoring/08-business-analytics/behavior-event-design/)
- Collector 的儲存設計 → [模組四 Collector 設計](/monitoring/04-collector/)
- 去識別化是分析的入場條件 → [模組七 資安與隱私](/monitoring/07-security-privacy/)
