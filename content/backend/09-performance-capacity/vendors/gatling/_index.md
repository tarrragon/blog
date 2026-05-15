---
title: "Gatling"
date: 2026-05-15
description: "用 JVM DSL、simulation 與 injection profile 表達複雜 scenario 的效能工程工具"
weight: 3
tags: ["backend", "performance", "capacity", "vendor", "gatling", "load-test"]
---

Gatling 的核心責任是把複雜使用者流程寫成可維護的 JVM simulation。它適合 JVM 生態團隊、強型別 DSL、HTTP / WebSocket / JMS / MQTT 等 scenario，以及需要把 injection profile、assertion、report 與 CI pipeline 綁在一起的壓測流程。

## 定位

Gatling 適合 code-first 且 JVM 能力強的團隊。當 workload model 需要多步驟 flow、資料 feeder、條件分支、session state 與明確 injection profile，Gatling 能用 simulation 把這些行為寫成工程 artifact。

這個定位讓 Gatling 接到 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 與 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)。它的價值在於把 traffic shape 寫進 injection profile，讓 ramp-up、constant users、stress peak 與 soak test 都能被版本化。

## 適用場景

JVM 團隊適合用 Gatling 承接壓測。Java、Scala 或 Kotlin 團隊能把 simulation 當成一般程式碼 review，並用既有 build、dependency、CI 與 artifact 流程維護。

複雜 scenario 適合用 Gatling 表達。登入、搜尋、加入購物車、checkout、payment mock、order query 這類 multi-step flow 可以用 session 與 feeder 管理資料。

高品質 report 適合 release review。Gatling 的 report 能幫 reviewer 看到 response time distribution、request group、error 與 injection profile，適合在 release gate 中保留可讀證據。

## 選型判準

| 判準              | Gatling 的價值            | 需要補的能力                        |
| ----------------- | ------------------------- | ----------------------------------- |
| JVM DSL           | simulation 可 code review | Scala / Java / Kotlin 維護能力      |
| Injection profile | 負載階段可精準表達        | production traffic shape 校正       |
| Session / feeder  | 多步驟資料與狀態容易管理  | 測試資料治理與敏感資料遮罩          |
| Report            | release review 可讀性高   | 長期趨勢儲存與 cross-run comparison |

JVM DSL 價值來自可維護性。壓測 scenario 如果需要被長期 review、重構、抽 helper 或接 build pipeline，Gatling 的 code-first workflow 會比 GUI test plan 更適合工程團隊。

Injection profile 價值來自負載形狀精準。團隊可以把 steady load、spike、ramp、open model 與 closed model 放到 simulation 中，讓 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 的 knee point 判讀更可重現。

## 跟其他工具的取捨

Gatling 和 k6 的主要差異是語言與生態。Gatling 適合 JVM 團隊與強型別 simulation；k6 適合 JavaScript-style scripting、CLI workflow 與 Grafana 生態。

Gatling 和 JMeter 的主要差異是維護模式。Gatling 偏 code review、build pipeline 與 simulation abstraction；JMeter 偏 GUI、plugin 與跨角色測試資產。

Gatling 和 Locust 的主要差異是自訂語言。Locust 適合 Python 團隊與任意 Python client；Gatling 適合 JVM 團隊與 report / injection profile 的結構化壓測。

Gatling 和 Vegeta 的主要差異是 scenario 深度。Vegeta 適合快速 HTTP pressure test；Gatling 適合需要 session、feeder、assertion 與多 request group 的長期測試。

## 操作成本

Gatling 的主要成本是 JVM 團隊能力。非 JVM 團隊要承擔語言、build tool、dependency 與 simulation pattern 的學習成本；這個成本只有在 scenario 複雜度夠高時才划算。

測試資料成本來自 feeder 與 session。多步驟 flow 需要 account、cart、order、token、region 與 tenant 資料，資料過期或分布偏差會讓壓測結果失真。

Enterprise / distributed 成本要提前評估。單機 Gatling 適合中小型 baseline；跨 region、大型活動前驗證或長時間 soak test 需要 runner topology、結果集中與雲端成本治理。

## Evidence Package

Gatling 結果應回寫到 evidence package。最小欄位包括 simulation version、injection profile、feeder source、target environment、assertion、response time distribution、error rate、throughput、target service saturation metric、known gap 與 owner。

| 欄位         | Gatling 證據來源                             |
| ------------ | -------------------------------------------- |
| Source       | simulation code、HTML report、dashboard link |
| Time range   | test start / end                             |
| Query link   | APM / metrics / logs 查詢連結                |
| Data quality | feeder freshness、scenario coverage          |
| Confidence   | production similarity、runner capacity       |
| Known gap    | 未覆蓋 flow、資料偏差、下游 mock 限制        |

Evidence package 的核心用途是讓 simulation 可回放。Reviewer 要能從 report 回到 injection profile、scenario code、feeder 與目標環境，才有辦法判斷一次壓測是容量訊號還是測試設計偏差。

## 案例回寫

Gatling 適合回寫多步驟與多負載模型案例。它可接 [FanDuel 雙峰 workload](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 的直播與投注雙模型、[SeatGeek waiting room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 的 token / admission flow，以及 [BookMyShow ticketing](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/) 的售票流程壓力。

這些案例的重點是 scenario 與 injection profile。Gatling 頁引用案例時，要把業務流程拆成 request group、session state、feeder、assertion 與 stop condition。

## 下一步路由

- 上游：[9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)
- 上游：[9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)
- 上游：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)
- 平行：[k6](/backend/09-performance-capacity/vendors/k6/)、[JMeter](/backend/09-performance-capacity/vendors/jmeter/)、[Locust](/backend/09-performance-capacity/vendors/locust/)
- 官方：[Gatling documentation](https://docs.gatling.io/)
