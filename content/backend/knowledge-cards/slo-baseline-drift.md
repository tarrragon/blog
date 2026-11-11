---
title: "SLO Baseline Drift"
date: 2026-05-12
description: "SLO baseline 因業務變化 / surge / 架構改動而需要重新校準的現象"
weight: 242
---

SLO baseline drift 的核心概念是「SLO 訂了不是永遠不動 — 業務變化、用戶習慣演變、架構升級都會讓 baseline 必須重新校準」。沒有 drift 意識、SLO 可能「太鬆失去意義」或「太緊每天 alert」。可先對照 [SLI / SLO](/backend/knowledge-cards/sli-slo/)。

## 跟其他概念的關係

SLO drift 來源：structural surge（COVID 類外部衝擊讓 baseline 永久上移）、product change（新 feature 改變用戶 journey）、architectural improvement（DB 換型、cache 加強、CDN 擴點）、user behavior（mobile share 上升、跨 region 比例變化）。drift 是 *新常態*，而不是 anomaly。可先對照 [SLI / SLO](/backend/knowledge-cards/sli-slo/)。

## 可觀察訊號與例子

需要重新校準 SLO 的訊號是「最近 N 個月 burn rate 持續低於 baseline」或「持續高於 baseline 但無 incident」。對應案例：[Zoom 30x COVID surge](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) — baseline 從 1000 萬 DAU 永久升到 3 億、SLO threshold 跟著重新校準。

## 判斷條件與後果

SLO 設定之後沒有再檢視時，它跟實際 SLI 分布之間的差距隨 baseline 移動而擴大，往哪一側擴大決定 SLO 失效的方式。實際表現遠好於 SLO 時（架構升級之後），burn rate 持續低於 baseline，SLO 分不出正常與退化；實際負載結構性上升而 SLO 沒有跟著調整時，burn rate 持續偏高卻沒有對應的 incident，alert 頻繁觸發而沒有事故，失去訊號的作用。所以 SLO 每季 review 一次：拉過去 90 天的 SLI 分布，比對 percentile 分布跟 SLO 是否對應。確認是 drift 之後，以 baseline 為輸入的設定一起過時，包括 alert threshold、autoscaler trigger、[performance budget](/backend/knowledge-cards/performance-budget/) 額度與容量規劃 baseline，只改 SLO 而沒改它們時，這些設定仍依舊的 baseline 觸發；[error budget](/backend/knowledge-cards/error-budget/) 以 SLO 為基準計算，也跟著重算。
