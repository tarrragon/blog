---
title: "Shopify：BFCM 容量治理與 Game Day 驗證節奏"
date: 2026-05-07
description: "把季節性流量峰值轉成年度可靠性流程，透過容量模型、演練與隔離策略提前吸收風險。"
weight: 51
tags: ["backend", "reliability", "case-study"]
---

Shopify 案例的核心責任是把可預期峰值轉成可預演流程。當流量高峰是年度固定事件，可靠性工作重點不是臨場救火，而是提前把容量與失效路徑變成可驗證資產。

## 問題場景

BFCM 類型高峰會同時放大三種壓力：流量突增、資料層寫入壓力、跨服務依賴抖動。若只在活動前做單次壓測，團隊通常只能看到系統上限，無法看到恢復節奏與指揮負載。

Shopify 的做法是把容量規劃、隔離邊界與演練節奏綁成同一條年度路線。

## 決策機制

| 機制                       | 核心問題               | 交付結果   |
| -------------------------- | ---------------------- | ---------- |
| Capacity planning baseline | 高峰前可承受上限是多少 | 容量預算   |
| Pod/isolation boundary     | 故障影響如何限制在局部 | 擴散邊界   |
| Game Day                   | 高峰前如何驗證假設     | 演練證據   |
| Resiliency matrix          | 服務與失效模式如何對齊 | 控制面清單 |

這個機制的價值是讓高峰風險在活動前被分批消化，而不是在活動中一次承擔。

## 可觀測訊號

| 訊號                    | 判讀重點               | 對應章節                                                        |
| ----------------------- | ---------------------- | --------------------------------------------------------------- |
| peak-load headroom      | 高峰前安全緩衝是否充足 | [6.9](/backend/06-reliability/capacity-cost/)                   |
| game-day action closure | 演練缺口是否完成回寫   | [6.21](/backend/06-reliability/reliability-debt-backlog/)       |
| pod-level degradation   | 退化是否被限制在局部   | [6.22](/backend/06-reliability/steady-state-definition/)        |
| command handoff latency | 高峰日交接節奏是否穩定 | [8.12](/backend/08-incident-response/ic-handoff-long-incident/) |

## 常見陷阱

把高峰準備當成一次性專案會讓知識斷層快速累積。可靠做法是把每輪活動輸出的缺口回寫成固定資產：runbook、matrix、驗證腳本與放行門檻。這讓下一輪準備從更高基準開始，而不是重來。

## 下一步路由

若要落地本案例，先從 [6.9](/backend/06-reliability/capacity-cost/) 建容量模型，再在 [6.22](/backend/06-reliability/steady-state-definition/) 定義高峰穩態。演練證據回寫 [6.23](/backend/06-reliability/verification-evidence-handoff/) 與 [8.6](/backend/08-incident-response/drills-and-oncall-readiness/)。
