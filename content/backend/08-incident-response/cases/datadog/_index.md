---
title: "Datadog"
date: 2026-05-01
description: "Datadog 監控服務事故、客戶觀測落差"
weight: 12
---

Datadog 2023 multi-region 事故是「監控供應商自己掛」的代表案例。當客戶依賴的 observability 平台失效、客戶失去判讀自己服務的能力、IR 流程出現 second-order 影響。

## 規劃重點

- 監控失效的 second-order 影響：客戶失去判讀工具、無法自我評估事故規模
- Multi-region 同時失效：region 隔離假設破裂時的全面失明
- 客戶溝通：監控廠商如何向「正在 blind 的客戶」溝通
- 自我監控：observability 廠商的 self-observability 設計

## 預計收錄事故

| 年份    | 事故                  | 教學重點                      |
| ------- | --------------------- | ----------------------------- |
| 2023-03 | Multi-region 全球停擺 | region 隔離破裂、客戶觀測落差 |

## 案例定位

Datadog 這個案例在講的是監控供應商自己失效時，客戶會同時失去判讀與協作能力。讀者先抓 multi-region、status page 與 incident management 的責任，再把 observability outage 看成 second-order 風險。

## 判讀重點

當監控平台自己出現連線或區域問題時，最先失去的不是資料，而是判讀服務健康的能力。當客戶仍在 blind 狀態時，對外溝通與備援觀測通道就要先回來，否則事故會因資訊不足而延長。

## 可操作判準

- 能否辨認 observability 平台本身就是依賴
- 能否把 multi-region 隔離失效視為核心風險
- 能否提供客戶替代觀測路徑
- 能否把 self-observability 放進平台設計

## 與其他案例的關係

Datadog 這頁最適合和 Honeycomb、Slack 一起看：前者是觀測平台本身，後者是事故通訊路徑。三者放在一起時，讀者會更清楚地看到「當你看不見系統時，連協作也會失明」這件事怎麼發生。

## 代表樣本

- 2023 multi-region 事故說明監控廠商自己也會失明。
- status page 與 incident management 的銜接，決定客戶能否持續觀測自己服務。
- 客戶在 blind 狀態時需要備援觀測路徑。
- self-observability 是 observability 廠商自己的基本要求。
- multi-region 同時失效會讓區域隔離假設失靈。
- incident response 的第一優先是把客戶從盲區拉回來。
- observability 平台失效會造成 second-order 事故。
- status page 與 incident workflow 需要維持同一條節奏。

## 引用源

- [2023-03-08 Incident: Infrastructure connectivity issue affecting multiple regions](https://www.datadoghq.com/blog/2023-03-08-multiregion-infrastructure-connectivity-issue/)：Datadog 2023 多區事故的官方回顧。
- [How we manage incidents at Datadog](https://www.datadoghq.com/blog/how-datadog-manages-incidents/)：Datadog incident response 與 postmortem 的流程。
- [Status Pages](https://docs.datadoghq.com/incident_response/status_pages/)：Datadog status page 的官方文件。
- [Integrate Atlassian Statuspage with Datadog Incident Management](https://docs.datadoghq.com/incident_response/incident_management/integrations/statuspage/)：Statuspage 與 incident management 的交接。
