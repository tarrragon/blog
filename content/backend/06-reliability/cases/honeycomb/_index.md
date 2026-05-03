---
title: "Honeycomb"
date: 2026-05-01
description: "Honeycomb Observability-driven SRE 與 SLO 實作"
weight: 12
---

Honeycomb 是 observability platform、由創辦人之一 Charity Majors 推動的 observability-driven SRE 是領域 thought leadership 來源。教學重點在「以 observability 為主軸的 SRE 工程文化」。

## 規劃重點

- High-cardinality observability：相對 metrics-first 的觀測哲學
- Service Level Objective 實作：SLO budget、burn rate alert
- Test in production：feature flag + observability 的 production testing
- [on-call](/backend/knowledge-cards/on-call/) 文化：Charity Majors 的 SRE / on-call 觀點

## 預計收錄實踐

| 議題                      | 教學重點                                |
| ------------------------- | --------------------------------------- |
| Observability Engineering | high-cardinality 與 unknown-unknowns    |
| SLO Burn Rate Alert       | error budget 速率告警設計               |
| Test in Production        | feature flag + observability 的安全推進 |
| Production Excellence     | Honeycomb 推動的 SRE 文化框架           |

## 案例定位

Honeycomb 這個案例在講的是 observability 如何變成工程決策，而不是只剩看板與指標。讀者先抓 high-cardinality、burn rate 與 test in production 這三個原語，再把它們看成觀測能力如何支撐 SRE 文化。

## 判讀重點

當訊號維度開始膨脹時，重點不是增加更多圖表，而是先判斷資料還能不能回答問題。當 SLO 進入 burn 速率區間時，觀測系統要能直接幫團隊看見風險，而不是等事故發生後才補證據。

## 可操作判準

- 能否辨認 high cardinality 何時讓查詢與告警失真
- 能否把 SLO burn rate 轉成當下可行動的訊號
- 能否在 production testing 中保住 blast radius
- 能否把 observability 當成工程責任，而不是 ops 專屬工作

## 與其他案例的關係

Honeycomb 把觀測責任直接拉到每個工程團隊，這和 Google 的 SLO 制度、Datadog 的自我觀測、Slack 的狀態揭露形成一組互補視角。當讀者先懂這頁，就比較容易看懂為什麼高 cardinality 與 burn rate 不是報表細節，而是決策前提。

## 代表樣本

- high cardinality 讓問題能按 tenant、feature、path 切開，而不是只看總平均。
- burn rate alert 直接把 SLO 消耗速度變成行動訊號。
- test in production 讓觀測訊號在真實流量下被驗證。
- observability engineering 把看板轉成工程決策入口。
- unknown-unknowns 讓觀測系統要先能回答「不知道要查什麼」的問題。
- production excellence 讓 observability 成為每個工程師的日常責任。
- query latency 會反過來告訴你資料建模是否已經失真。
- feature flag 配合觀測訊號，讓 production testing 可以安全推進。

## 引用源

- [What Is Observability Engineering?](https://www.honeycomb.io/resources/getting-started/what-is-observability-engineering)：Honeycomb 對 observability engineering 的核心定義。
- [High Cardinality](https://docs.honeycomb.io/get-started/basics/observability/concepts/high-cardinality)：高 cardinality / dimensionality 的官方說明。
- [SLO Detail View](https://docs.honeycomb.io/reference/honeycomb-ui/slos/slo-detail-view/)：burn rate 與 budget burndown 的產品視角。
- [Observability: It's Every Engineer’s Job, Not Just Ops’ Problem](https://www.honeycomb.io/blog/observability-every-engineers-job-not-just-ops-problem)：觀測責任不只在 ops 的實踐論述。
