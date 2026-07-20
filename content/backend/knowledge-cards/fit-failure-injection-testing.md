---
title: "FIT（Failure Injection Testing）"
date: 2026-07-20
description: "驗證應用層容錯邏輯是否生效時、在請求路徑注入 timeout / error / 延遲的故障注入粒度"
weight: 409
---

FIT 是 Netflix 開發的請求路徑層故障注入工具，對特定 API call、dependency request 或 service-to-service 通訊植入 timeout、error 或延遲。它跟 instance-level injection（如 Chaos Monkey，關閉整個節點）是同一個 [Chaos Test](/backend/knowledge-cards/chaos-test/) 光譜上不同粒度的兩端——instance-level 驗證基礎設施韌性（load balancer 能否切流、auto-scaling 能否補位），FIT 驗證的是應用韌性（fallback 是否生效、circuit breaker 是否觸發、retry 是否安全）。

## 概念位置

FIT 的粒度優勢是精準、[Blast Radius](/backend/knowledge-cards/blast-radius/) 小——只影響被注入故障的那條依賴路徑，不需要真的關掉整個節點。代價是需要更深的 instrumentation，建置成本比 instance-level injection 高。兩種粒度不互斥：團隊通常先用 instance-level 建立 chaos 習慣，再逐步引入 FIT 提升驗證精度。

## 可觀察訊號與例子

Netflix 把單輪 FIT 實驗結構化成 steady state（正常時應維持的行為）、hypothesis（故障發生後仍應維持什麼）、blast radius（實驗範圍限制）、abort condition（何時立即停止）四元素，讓故障注入從隨機破壞變成可重複的科學驗證循環（見 [Netflix：Steady State、Chaos 與 FIT](/backend/06-reliability/cases/netflix/steady-state-chaos-and-fit/)）。實驗輸出進一步結構化成四個決策欄位（steady-state impact、dependency drift、abort trigger record、fallback result），讓結果直接對應 release gate 的放行或凍結判斷，不再依賴主觀討論（見 [Netflix：FIT 證據交接](/backend/06-reliability/cases/netflix/fit-failure-injection-evidence-handoff/)）。

## 判讀方式

判斷該不該引入 FIT，看團隊已驗證過的是不是只有基礎設施層失效（節點掛掉、AZ 失效）——如果應用層的 fallback、circuit breaker 邏輯從沒被真實故障測過，instance-level injection 測不到這一層，這時才需要 FIT 的路徑層精度。缺 instrumentation 就上 FIT，通常先卡在建置成本，這時該回頭先用 instance-level 建立基本的 chaos 紀律。
