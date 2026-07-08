---
title: "降級策略"
date: 2026-06-20
description: "系統超載時犧牲什麼保住什麼 — 動態取樣、事件優先級、功能降級、聚合前移四種策略"
weight: 2
tags: ["devops", "burst-traffic", "degradation", "sampling", "priority"]
---

降級策略的核心決策是「超載時犧牲什麼保住什麼」。犧牲的是精度、延遲或非核心功能；保住的是核心功能的可用性。沒有降級策略的系統在超載時整體崩潰 — 所有功能同時不可用。

## 動態取樣

流量超過閾值時自動降低取樣率。平時 100% 收集、超載時降到 10% — 仍有資料可分析，只是精度下降。

### 觸發條件

| 訊號                             | 動作               |
| -------------------------------- | ------------------ |
| Collector 回 429 次數 > N / 分鐘 | SDK 降低取樣率 50% |
| 連續 429 超過 M 分鐘             | SDK 再降到 10%     |
| 429 消失且 buffer 清空           | SDK 恢復 100%      |

### 取樣的公平性

動態取樣不應該只丟新事件保留舊事件（FIFO 丟棄）— 這會讓取樣偏向「burst 初期的事件」。更好的策略是隨機取樣（每個事件有 sampling_rate 的機率被保留），讓取樣後的資料仍然能代表整體分佈。

取樣後的事件帶 `_sampling_rate` 欄位，分析時用 `1 / sampling_rate` 做加權還原。

## 事件優先級

不同事件類型的 debug 價值不同。超載時先丟價值低的，保留價值高的。

| 優先級 | 事件類型  | 理由                             | 超載時處理       |
| ------ | --------- | -------------------------------- | ---------------- |
| 最高   | error     | debug 核心 — 丟了就查不到問題    | 全部保留         |
| 高     | lifecycle | session 邊界 — 影響 session 分析 | 全部保留         |
| 中     | metric    | 趨勢可從取樣還原                 | 降低取樣率       |
| 低     | event     | 行為分析可接受精度損失           | 降低取樣率或暫停 |

優先級的判斷原則：「這個事件丟了、要花多少時間從其他來源補回相同資訊」。Error 的 stack trace 丟了幾乎不可能從其他來源補回；event 的 click 計數可以從後續資料的趨勢推測。

## 功能降級

非核心功能暫時關閉或降低更新頻率，把資源留給核心功能。

| 功能               | 正常模式         | 降級模式              |
| ------------------ | ---------------- | --------------------- |
| Dashboard 即時刷新 | 每秒查詢         | 每 30 秒查詢          |
| Rule engine 評估   | 每筆事件即時評估 | 累積 10 筆批次評估    |
| JSONL 匯出         | 隨時可匯出       | 暫停（避免 I/O 競爭） |
| 降採樣 job         | 每小時跑         | 延後到流量恢復後補跑  |

降級的觸發和恢復應該自動化 — 用 collector 的內部 metric（goroutine pool 使用率、寫入延遲）作為訊號。

## 聚合前移

讓 SDK 端做預聚合，減少送到 collector 的事件數量。

平時：每次 click 送一筆 `button.clicked` 事件 → 100 次 click = 100 筆事件。
聚合前移：SDK 累積 10 秒內的 click → 送一筆 `button.clicked` 帶 `count: 17` → 100 次 click = ~10 筆事件。

聚合前移犧牲的是事件粒度（失去每次 click 的精確時間戳），換取的是 10x 的事件量減少。適用於高頻但單筆資訊量低的事件（click、scroll、mousemove）。

聚合前移的觸發也可以是動態的 — collector 回 429 時 SDK 自動啟用聚合前移，流量恢復後關閉。

## 下一步路由

- 突發流量的分類 → [突發流量的分類](/operations/07-burst-traffic/burst-classification/)
- Queue 做更大規模的緩衝 → [Queue 緩衝](/operations/07-burst-traffic/queue-buffering/)
- 不同規模的應對方案 → [規模分級應對表](/operations/07-burst-traffic/scale-tier-response/)
- 背壓和 rate limit 的基礎 → [模組三 流量管控](/operations/03-traffic-management/)
