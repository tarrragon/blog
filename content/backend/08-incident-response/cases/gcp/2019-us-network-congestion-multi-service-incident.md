---
title: "GCP 2019 US Network Congestion Multi-service Incident"
date: 2026-05-07
description: "2019-06-02 Google Cloud 因美國區域網路壅塞造成多服務退化的事故解析：跨產品依賴、流量控制與區域隔離判讀。"
weight: 1
tags: ["backend", "incident-response", "case-study", "gcp"]
---

2019 年 GCP 網路壅塞事故的核心教訓是：當共享網路容量被打滿，影響會跨越產品邊界，同一時間出現在 compute、storage、observability 與管理面。

## 事故摘要

Google Cloud 在 2019-06-02 發生美國多區域 network congestion，官方摘要指出多個 US region 出現 elevated packet loss，影響持續約 3 至 4 小時以上，並牽動多個 GCP 與非 Cloud 服務。

這類事故本質不是單一服務壞掉，而是共享網路資源退化造成的跨產品連鎖事件。

## 判讀訊號

| 訊號                                 | 事故中代表什麼                 | 第一波決策價值                           |
| ------------------------------------ | ------------------------------ | ---------------------------------------- |
| 多區域 packet loss 同時上升          | 共享網路層失衡，不是單服務 bug | 優先走區域隔離與流量調整路徑             |
| 多產品錯誤率一起上升                 | 事故已跨產品依賴鏈擴散         | 事故分級以跨產品影響為主，而非單團隊視角 |
| 部分 region 正常、部分 region 退化   | 區域差異可用來做流量重新分配   | 啟動 region-aware mitigation             |
| status page 更新中提到 varied impact | 影響面非均勻分布               | 對外更新要分 region / service 粒度       |

## 事故路徑

1. 美國多區域網路容量在高壓下出現壅塞與丟包。
2. 多個 GCP 產品受同一網路瓶頸影響，出現延遲與錯誤。
3. 工程團隊進行流量與容量調整，逐區域回復。
4. 狀態頁持續更新受影響範圍與恢復進度。
5. 事後回寫區域隔離、容量保留與跨產品協調流程。

## 可回寫控制面

| 控制面                           | 這次事故暴露的缺口               | 回寫方向                              |
| -------------------------------- | -------------------------------- | ------------------------------------- |
| Region-aware traffic control     | 區域壅塞時流量轉移策略不夠快     | 建立區域流量切換的預設策略與演練      |
| Cross-product incident command   | 多產品同時受影響時協調成本高     | 強化跨產品指揮節奏與共享 decision log |
| Network dependency mapping       | 服務依賴共享網路層但判讀入口分散 | 補跨產品依賴圖與共同告警面板          |
| Status communication granularity | 對外說明若只寫全域狀態會失真     | 更新按 region 與 service 分層揭露     |

## 下一步路由

- 觀測證據包： [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)
- 事故通訊： [8.4 Incident Communication](/backend/08-incident-response/incident-communication/)
- 事中決策紀錄： [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- 證據回寫流程： [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
- 實驗安全邊界： [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)

## 引用源

- [Google Cloud Networking Incident #19009](https://status.cloud.google.com/incident/cloud-networking/19009)
- [An update on Sunday’s service disruption](https://cloud.google.com/blog/topics/inside-google-cloud/an-update-on-sundays-service-disruption)
