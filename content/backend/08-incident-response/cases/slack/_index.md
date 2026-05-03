---
title: "Slack"
date: 2026-05-01
description: "Slack 通訊服務事故與外部狀態頁設計"
weight: 11
---

Slack 是即時通訊服務、事故時通訊管道本身受影響、是「monitor your own monitor」議題的代表。Slack engineering blog 公開度高、status page 設計細緻。

## 規劃重點

- 通訊管道自身故障：客戶用 Slack 通報 Slack 事故的 paradox
- 外部狀態頁設計：細粒度 region / feature 揭露
- WebSocket 連線風暴：reconnection storm 在大規模長連線服務的特殊風險
- 跨 workspace 隔離：multi-tenant 事故的部分擴散模式

## 預計收錄事故

| 年份 | 事故             | 教學重點                        |
| ---- | ---------------- | ------------------------------- |
| 2022 | Jan 全球登入失效 | 配置變更、跨服務依賴            |
| 2022 | 2-22 事故        | reconnection storm、status 揭露 |

## 案例定位

Slack 這個案例在講的是通訊平台本身失效時，事故通訊也會一起受影響。讀者先抓 Slack status API、service delivery index 與 incident blog 的責任，再把這類事件看成「監控自己的監控」問題。

## 判讀重點

當登入或連線異常出現時，使用者需要的不是更多術語，而是清楚知道狀態頁、回復進度與替代通訊方式。當 reconnection storm 發生時，恢復節奏也要先保住連線，再回頭處理狀態同步。

## 可操作判準

- 能否讓 status page 與實際事故節奏同步
- 能否把通訊工具失效當成獨立風險
- 能否清楚說出哪些 workspace 受影響
- 能否在恢復時先控制 reconnection 壓力

## 與其他案例的關係

Slack 和 Discord、Microsoft 365 一起看，最能理解通訊工具本身失效時的 IR 難點。它也和 Datadog 有關，因為當你連通訊都不能穩定時，監控與狀態揭露就必須先變成對外的第一路由。

## 代表樣本

- 2-22 事故顯示通訊平台本身失效時，status 與 incident blog 也會成為核心資產。
- Slack Status API 則是讓客戶能獨立查詢事故與歷史狀態的樣本。
- reconnection storm 讓通訊平台的容量問題直接變成客戶體感。
- service delivery index 反映的是可靠性與對外揭露如何一起運作。
- workspace 層的部分失效讓多租戶通訊平台必須做細粒度揭露。
- monitor your own monitor 是 Slack 這類平台最直接的 IR 警示。
- incident blog 讓對外敘事與對內修復節奏保持一致。
- multi-workspace failure 會把對外通訊也一起拖進事故。

## 引用源

- [Checking up on Slack with the Slack Status API](https://api.slack.com/apis/slack-status)：Slack 狀態與歷史 incident 的官方 API。
- [Slack’s Incident on 2-22-22](https://slack.engineering/slacks-incident-on-2-22-22/)：Slack 事故技術復盤。
- [A Terrible, Horrible, No-Good, Very Bad Day at Slack](https://slack.engineering/a-terrible-horrible-no-good-very-bad-day-at-slack/)：另一篇詳細事故回顧。
- [Service Delivery Index: A Driver for Reliability](https://slack.engineering/service-delivery-index-a-driver-for-reliability/)：Slack 的可靠性指標與 status 文化。
