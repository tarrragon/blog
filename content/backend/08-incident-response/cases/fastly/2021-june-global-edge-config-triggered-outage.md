---
title: "Fastly 2021 June Global Edge Config-triggered Outage"
date: 2026-05-07
description: "2021-06-08 Fastly 全球 edge 事故解析：有效客戶配置觸發潛藏 bug、分鐘級擴散與快速隔離恢復。"
weight: 1
tags: ["backend", "incident-response", "case-study", "fastly"]
---

Fastly 2021 事故的核心教訓是：在全球 edge 平台中，一個有效配置也可能觸發平台潛藏 bug，造成分鐘級全球擴散。

## 事故摘要

Fastly 官方摘要指出，2021-06-08 的全球 outage 由平台既有軟體 bug 觸發，觸發條件來自一個有效的客戶配置變更。故障在短時間內影響大範圍 edge 節點，並在隔離配置後逐步恢復。

這類事故不是「客戶配置錯誤」或「平台單點故障」的二選一，而是配置與平台行為交互下的系統性風險。

## 判讀訊號

| 訊號                   | 事故中代表什麼               | 第一波決策價值                    |
| ---------------------- | ---------------------------- | --------------------------------- |
| 全球 503 快速上升      | edge 平台共同執行路徑失效    | 立即轉全域 incident，不走單區排障 |
| 偵測時間短但影響面巨大 | 擴散速度高於人工逐站處理能力 | 優先做全域隔離與停傳播動作        |
| 關閉觸發配置後快速回線 | 觸發路徑明確、回退有效       | 建立配置觸發型事故的快速回退標準  |
| 事故前已有潛藏 bug     | 變更驗證對交互條件覆蓋不足   | 回寫配置驗證與灰度策略            |

## 事故路徑

1. 平台先前部署引入可被特定條件觸發的 bug。
2. 客戶推送有效配置，觸發 bug。
3. 大範圍 edge 節點回應錯誤，形成全球 outage。
4. 團隊定位並隔離觸發配置，服務逐步恢復。
5. 事後回寫驗證、隔離與恢復流程。

## 可回寫控制面

| 控制面                        | 這次事故暴露的缺口             | 回寫方向                              |
| ----------------------------- | ------------------------------ | ------------------------------------- |
| Config-trigger safety gate    | 有效配置也可觸發平台 bug       | 對配置與平台交互條件增加回放測試      |
| Global propagation brake      | 擴散速度遠快於局部人工止血     | 建立全域停傳播與快速隔離機制          |
| Canary and staged rollout     | 交互條件在前期驗證未被涵蓋     | 強化灰度策略與跨場景驗證              |
| Incident communication timing | 影響廣但恢復快，對外節奏需精準 | 以固定 cadence 說明影響範圍與恢復進度 |

## 下一步路由

- 規則/配置成本訊號： [4.21 Rule-level CPU Signal Governance](/backend/04-observability/rule-level-cpu-signal-governance/)
- 證據包： [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
- 規則推送閘門： [6.24 Rule Rollout Safety Gate](/backend/06-reliability/rule-rollout-safety-gate/)
- 事故通訊： [8.4 Incident Communication](/backend/08-incident-response/incident-communication/)
- 證據回寫流程： [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)

## 引用源

- [Summary of June 8 outage](https://www.fastly.com/blog/summary-of-june-8-outage)
