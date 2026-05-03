---
title: "Discord"
date: 2026-05-01
description: "Discord Gateway scale-out 事故與容量驚奇"
weight: 13
---

Discord 是大規模長連線 gateway 的代表、事故多源自 capacity surprise（用戶行為意外觸發 fan-out 放大）。Discord engineering blog 揭露多次 scaling 事故。

## 規劃重點

- Long-lived WebSocket：與短連線 HTTP 服務的故障模式差異
- Fan-out 放大：單一訊息推播到大量連線的容量風險
- Sharding 與 cluster topology：超大型 guild 的特殊處理
- Gradual rollout 限制：長連線服務的 deploy 節奏

## 預計收錄事故

| 年份 | 事故                  | 教學重點                        |
| ---- | --------------------- | ------------------------------- |
| 2023 | Authentication outage | capacity surprise、reconnection |
| 2026 | Voice outage          | session state 規模化的失敗模式  |

## 案例定位

Discord 這個案例在講的是長連線與 session state 一旦失衡，事故就會直接反映在使用者連線體感上。讀者先看懂 Gateway、authentication 與 voice 這些路由的責任，再把 reconnection storm 視為核心風險。

## 判讀重點

當 gateway 或 session 基礎設施出現問題時，復原順序必須同時照顧連線穩定與服務容量。當流量重新接回來時，先保住重連與驗證，再處理後續聊天與 voice 路徑，能減少二次抖動。

## 可操作判準

- 能否看出問題在連線層還是 session state
- 能否把 capacity surprise 轉成可預測的壓力模型
- 能否讓 reconnection path 比一般流量更早恢復
- 能否把 gateway 事故寫成客戶體感可理解的時間線

## 與其他案例的關係

Discord 和 Slack 是兩種不同的長連線通訊平台，但都會遇到 reconnection 與 status communication 問題。它也可和 Heroku 一起讀，因為多租戶入口與 session state 一旦不穩，故障就會直接表現在使用者連線上。

## 代表樣本

- 2023 authentication outage 是連線層與驗證路徑失衡的樣本。
- 2026 voice outage 則展示 session state 與 voice path 的恢復難度。
- reconnect storm 是長連線平台事故的常見擴散器。
- gateway 與 voice path 的分工會直接影響恢復順序。
- shard topology 會決定大型 guild 的故障擴散方式。
- long-lived WebSocket 讓 gradual rollout 的風險比短連線服務更高。
- authentication 與 voice path 分層，讓不同失效能有不同恢復路徑。
- capacity surprise 讓平時看似正常的流量，在事故時突然失控。

## 引用源

- [Gateway](https://docs.discord.com/developers/events/gateway)：Discord Gateway 的官方文檔，補 long-lived WebSocket 語意。
- [25% or 6 to 4: The 11/6/23 Authentication Outage](https://discord.com/blog/authentication-outage)：Discord 服務中斷的技術回顧。
- [You’ve Got (Too Much) Mail: Behind the Scenes of the 3/25/26 Voice Outage](https://discord.com/blog/behind-the-scenes-of-the-3-25-26-voice-outage)：Discord 最近的 voice outage 回顧。
- [Discord Blog](https://discord.com/blog)：Discord engineering 與 outage 類文章總入口。
