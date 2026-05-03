---
title: "7.23 資安與可靠性的共同控制面"
tags: ["Security", "Reliability", "Shared Controls", "Operations"]
date: 2026-04-30
description: "建立資安與可靠性共同控制面的交集，整合 rollback、containment、degradation 與 evidence"
---

本篇的責任是建立資安與可靠性的共同控制面。讀者讀完後，能用同一組控制語言處理風險收斂與服務穩定。

## 核心論點

共同控制面的核心概念是同一項能力同時承擔安全與穩定責任。共同控制面明確後，團隊能避免重複建設與交接斷層。

## 共同控制項

| 控制項         | 資安責任           | 可靠性責任         |
| -------------- | ------------------ | ------------------ |
| Containment    | 收斂攻擊或曝險擴散 | 限制故障擴散範圍   |
| Rollback       | 回退高風險變更     | 恢復服務穩定狀態   |
| Degradation    | 保留核心服務能力   | 降低系統壓力與損耗 |
| Evidence chain | 保留回查與審計資料 | 保留故障與修復證據 |
| Runbook        | 固定安全處置步驟   | 固定運維處置步驟   |

## 控制欄位對齊

控制欄位對齊的責任是讓兩個模組共享決策資料。共同欄位可包含 trigger、owner、action、validation、rollback condition 與 write-back target。

## 演練與驗證

演練與驗證的責任是讓控制在壓力情境保持可用。共同演練可同時驗證安全處置與可靠性恢復，並記錄雙方指標。

## 交接路由

交接路由的責任是把控制決策推進到 06 模組。交接資料可包含風險分級、處置結果、回退證據與後續改善任務。

## 與 04 / 06 / 08 的組合路由

組合路由的責任是讓共同控制面同時接上訊號、驗證與事故流程。7.23 不只把資安控制交給可靠性驗證，也把證據需求交給 04、把處置節奏交給 08。

| 組合點         | 04 可觀測性承接             | 06 可靠性承接                 | 08 事故處理承接           |
| -------------- | --------------------------- | ----------------------------- | ------------------------- |
| Evidence chain | audit log、trace、證據保留  | evidence replay、演練驗證     | 事故 timeline 與復盤證據  |
| Detection gap  | alert rule、dashboard、SLO  | chaos hypothesis、SLO gate    | severity trigger、runbook |
| Containment    | blast radius 訊號與拓撲關係 | 隔離演練、降級驗證            | 指揮、隔離與恢復排序      |
| Rollback       | rollback 前後健康訊號       | rollback rehearsal、DR drill  | rollback decision log     |
| Degradation    | 容量、latency、queue 指標   | load test、capacity rehearsal | 降級公告與恢復節點        |

Evidence chain 在真實服務中會落到誰在什麼時間看過什麼資料、哪個 token 被使用、哪個服務產生異常輸出。04 承接資料可觀測性，06 驗證 evidence replay 是否可重播，08 在事故 timeline 中使用同一組證據做決策與復盤。

Detection gap 在真實服務中通常表現為資安事件被客訴、成本異常或下游故障先發現。04 補 alert 與 dashboard，06 把缺口轉成 chaos hypothesis 或 release gate，08 把觸發條件寫進 severity 與 runbook。

Containment 在真實服務中同時是資安隔離與可靠性限縮。04 提供 blast radius 與 service topology，06 驗證隔離後核心服務是否維持，08 決定封鎖、切流、降級與恢復順序。

Rollback 在真實服務中需要把風險變更退回到穩定狀態。04 提供 rollback 前後的健康訊號，06 定期演練回退路徑，08 記錄誰在什麼條件下做出 rollback 決策。

Degradation 在真實服務中是保留核心功能、放棄次要能力。04 觀察容量與延遲訊號，06 驗證 degraded mode 的承載能力，08 負責對內外說明目前服務狀態與恢復節點。

## 判讀訊號與路由

| 判讀訊號                   | 代表需求                    | 下一步路由  |
| -------------------------- | --------------------------- | ----------- |
| 安全處置造成服務不穩定     | 需要補 shared rollback 策略 | 7.23 → 06   |
| 可靠性演練未覆蓋安全情境   | 需要補共同 scenario         | 7.23 → 7.B9 |
| 事件復盤只記錄單一面向     | 需要補 shared evidence      | 7.23 → 7.24 |
| 控制 owner 在兩模組不一致  | 需要補共同控制欄位          | 7.23 → 7.B1 |
| 偵測訊號不足以支持資安判讀 | 需要補 observability 訊號   | 7.23 → 04   |
| 處置決策沒有事故節奏       | 需要補 incident route       | 7.23 → 08   |

## 必連章節

- [7.B3 資安控制驗證](/backend/07-security-data-protection/blue-team/security-control-validation/)
- [7.B6 Incident Triage Loop](/backend/07-security-data-protection/blue-team/incident-triage-loop/)
- [7.18 資安控制面如何交接到部署與事故流程](/backend/07-security-data-protection/security-control-handoff-to-delivery-and-incident/)
- [04 模組：可觀測性](/backend/04-observability/)
- [06 模組：可靠性](/backend/06-reliability/)
- [08 模組：事故處理](/backend/08-incident-response/)

## 完稿判準

完稿時要讓讀者能列出共同控制面與交接欄位。輸出至少包含控制項、雙責任、驗證方式與交接路由。
