---
title: "AWS 2021 US-EAST-1 Control Plane Degradation"
date: 2026-05-07
description: "2021-12-07 AWS us-east-1 控制面退化案例：內部網路壅塞、API 錯誤率升高、跨服務依賴連鎖與通訊節奏調整。"
weight: 2
tags: ["backend", "incident-response", "case-study", "aws"]
---

2021 年 AWS us-east-1 事件的核心教訓是：控制面退化不一定來自服務程式錯誤，內部網路壓力也能讓 API 與依賴鏈條同時失真。這類事故要先確認控制面健康，再決定是否進行服務層回退。

## 事故摘要

AWS 在 2021-12-07 發生 us-east-1 多服務退化事件。官方資訊指出，內部網路裝置的異常行為導致這個區域的 API 請求與內部服務通訊壅塞，進而造成多個服務管理與控制面能力受影響。部分資料面能力可用，但控制面操作、狀態回報與恢復節奏出現延遲。

這類事故的難點在於，使用者看到的是「很多服務一起怪」，而工程上真正要先判斷的是：共同依賴是否先失真。

## 判讀訊號

| 訊號                       | 事故中代表什麼                 | 第一波決策價值                           |
| -------------------------- | ------------------------------ | ---------------------------------------- |
| 多服務 API 錯誤率同時上升  | 共享控制面或內部網路層可能失真 | 優先調查共用控制平面，不先分散逐服務排障 |
| 控制操作延遲遠高於資料讀寫 | 控制面與資料面可用性不同步     | 對外通訊要分清 control/data plane 差異   |
| 區域集中異常（us-east-1）  | 區域依賴與路由聚集形成單點風險 | 啟動跨區降載或備援策略                   |
| 狀態更新節奏出現抖動       | 事故資訊供應鏈本身受影響       | 建立固定 cadence 與替代更新通道          |

## 事故路徑

1. 區域內部網路層出現異常與壅塞。
2. 控制面 API 與內部依賴通訊受阻。
3. 多服務管理能力與狀態回報受到影響。
4. 部分服務資料面仍可運作，但操作與恢復節奏失真。
5. 團隊逐步收斂網路壓力並恢復控制面可用性。

這條路徑顯示：真正的擴散點在 shared internal network + control plane，不是某個單一服務程式。

## 可回寫控制面

| 控制面                         | 這次事故暴露的缺口               | 回寫方向                                                |
| ------------------------------ | -------------------------------- | ------------------------------------------------------- |
| Control/Data plane 分離判讀    | 對外敘述常把兩者混在一起         | 在通訊與 runbook 明確區分控制面與資料面狀態             |
| 區域依賴治理                   | 單區域控制面異常可牽動多服務     | 把跨區備援與降載條件納入 release 與 incident gate       |
| Shared network health 訊號治理 | 內部網路異常訊號未被快速上提     | 補 shared infrastructure 指標到 [4.20 evidence package] |
| Incident communication cadence | 事故中更新節奏易受狀態不完整影響 | 固定 cadence，並保留「已知 / 未知 / 下一更新時間」欄位  |

## 下一步路由

- 觀測證據包： [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
- 可觀測性 operating model： [4.18 Observability Operating Model](/backend/04-observability/observability-operating-model/)
- 可靠性準備度： [6.19 Reliability Readiness Review](/backend/06-reliability/reliability-readiness-review/)
- 止血與回復： [8.3 Containment / Recovery Strategy](/backend/08-incident-response/containment-recovery-strategy/)
- 事故通訊： [8.4 Incident Communication](/backend/08-incident-response/incident-communication/)
- 影響評估： [8.20 Customer Impact Assessment](/backend/08-incident-response/customer-impact-assessment/)

## 引用源

- [Summary of the AWS service event in the Northern Virginia (US-EAST-1) Region](https://aws.amazon.com/message/12721/)
