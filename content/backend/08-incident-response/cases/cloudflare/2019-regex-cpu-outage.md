---
title: "Cloudflare 2019 Regex CPU Outage"
date: 2026-05-07
description: "2019-07-02 Cloudflare WAF 規則更新導致全球 CPU 飆升的事故解析：觸發條件、擴散機制、止血決策與可回寫控制面。"
weight: 1
tags: ["backend", "incident-response", "case-study", "cloudflare"]
---

2019 年 Cloudflare regex 事故的核心教訓是：控制面配置錯誤可以在秒級擴散成全球可用性事故。這類事故的第一責任不是「加機器」，而是迅速切斷擴散路徑，讓錯誤停止被新流量放大。

## 事故摘要

Cloudflare 在 2019-07-02 發布新的 WAF Managed Rule 後，規則中的 regex 觸發 catastrophic backtracking，導致 edge CPU 快速打滿。事故影響約 27 分鐘，症狀是大量 502/503 與延遲激增。

這起事件屬於典型「控制面配置推送 → data plane 全網受影響」模式。錯誤並非單點節點故障，而是由一致推送機制把同一錯誤同步擴散到整個 edge 網路。

## 判讀訊號

| 訊號                          | 事故中代表什麼                   | 第一波決策價值                           |
| ----------------------------- | -------------------------------- | ---------------------------------------- |
| 全球 CPU 同步飆升             | 問題來自共用規則或共用執行路徑   | 優先檢查最新全域配置變更                 |
| 5xx 與延遲同時惡化            | 非單純容量尖峰，更像執行成本突增 | 優先撤回新規則，避免持續放大             |
| 多區域同時報警                | 事故已跨區域，屬全網級控制面風險 | 啟動全域指揮節奏與高頻通訊               |
| 回滾後指標快速回穩            | 根因與近期變更高度相關           | 立即凍結同批規則推送，改走分區驗證       |
| 事件期間 rule path 命中異常增 | 單一規則造成 CPU 熱點            | 補 rule-level profiling 與上線前成本檢查 |

## 事故路徑

1. 控制面推送新 WAF 規則到全球 edge。
2. 規則 regex 在特定輸入下產生高計算成本。
3. edge CPU 被規則執行成本吃滿，請求處理能力下降。
4. 5xx 與延遲擴散成全球可見症狀。
5. 回滾規則後，CPU 與可用性逐步恢復。

這條路徑顯示：事故擴散速度主要由「推送覆蓋範圍」決定，而不是由「單機故障率」決定。

## 可回寫控制面

| 控制面              | 這次事故暴露的缺口               | 回寫方向                                                          |
| ------------------- | -------------------------------- | ----------------------------------------------------------------- |
| 規則上線前靜態檢查  | regex 風險模式未被擋下           | 補 regex 風險 lint 與拒絕規則（高 backtracking 風險直接阻擋）     |
| 上線前效能測試      | 缺少 rule-level CPU 成本基線     | 補 rule replay 測試，用代表性 payload 驗證執行成本                |
| 推送策略            | 全域一次推送讓 blast radius 過大 | 改成分區/分群 staged rollout，設回滾閘門                          |
| 事故啟動門檻        | 全網症狀出現後才完整升級         | 以「跨區 CPU 同步異常 + 5xx 上升」作為自動升級條件                |
| Decision log        | 事中決策若缺時間線，復盤成本高   | 在事故期間即時記錄假設、回滾條件、責任人與驗證結果                |
| Evidence write-back | 事故教訓易停在 PIR 文本          | 回寫到 `04` 觀測規則與 `06` 實驗安全邊界，形成下次推送前硬性 gate |

## 下一步路由

- 回寫訊號治理： [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)  
- 回寫規則推送閘門： [6.24 Rule Rollout Safety Gate](/backend/06-reliability/rule-rollout-safety-gate/)
- 回寫驗證與安全邊界： [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)  
- 回寫事中決策與證據： [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)  
- 回寫跨模組閉環： [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)

## 引用源

- [Details of the Cloudflare outage on July 2, 2019](https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019)
