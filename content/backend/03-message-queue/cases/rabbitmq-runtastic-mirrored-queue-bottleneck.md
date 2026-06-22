---
title: "3.C30 Runtastic：Mirrored queue 網路負載瓶頸"
date: 2026-05-18
description: "Runtastic 2020 lockdown 流量暴增、performance test 揭露 mirroring 邏輯把網路元件壓垮、調整 mirroring 配置消除瓶頸。"
weight: 30
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

Runtastic 的案例暴露了 RabbitMQ mirrored queue 的網路成本被嚴重低估。Mirrored queue 的可靠性提升代價是 message 在 cluster 內的網路複製量跟 mirror 數成正比，而這個成本在日常流量下可能不可見、只在壓力測試或突發流量時才暴露。

## 業務背景

Runtastic 是 Adidas 旗下的健身追蹤平台，使用者透過 app 記錄跑步、騎車、重訓等運動資料。2020 年 COVID-19 lockdown 期間，居家運動需求爆增，平台的 concurrent user 數量在數週內翻倍。

Runtastic 的後端架構是 microservice 架構，RabbitMQ 是服務間訊息傳遞的核心。運動資料記錄、通知推送、社交功能（好友排行、挑戰）、analytics 事件都透過 RabbitMQ 的 queue 串接。

## 技術挑戰：Mirroring 的隱藏網路成本

Runtastic 的 RabbitMQ cluster 使用 mirrored queue（`ha-mode: all`）確保訊息在 broker 故障時不遺失。Mirrored queue 把每條訊息同步複製到 cluster 中所有 node — 3 node cluster 代表每條訊息的網路傳輸量是原始大小的 3 倍。

日常流量下，mirroring 的額外網路負載在 cluster 的頻寬容量之內，效能影響不明顯。但 lockdown 後流量翻倍時，mirroring 的網路負載跟著翻倍 — 更準確地說是翻 2×N 倍（流量 2 倍 × mirror 數 N）。

Runtastic 的 cluster 使用了共享的網路元件（network switch / load balancer），mirroring 的流量把共享網路元件的頻寬壓到極限。表現是 broker 間的 mirroring 延遲上升 → publisher confirm 延遲上升 → producer 端的 publish latency 從毫秒跳到秒級 → 上游服務開始 timeout。

問題的隱蔽性在於：日常監控只看 broker 的 CPU、memory、disk，沒有把 inter-node network throughput 作為關鍵指標。網路瓶頸在 broker-level metric 上的表現是「publish confirm 變慢」，容易被誤判為 broker 過載而非網路飽和。

## 解法

### Performance test 定位瓶頸

Runtastic 在事件發生後用 performance test 重現問題。測試揭露了 mirroring 流量跟 broker 間網路頻寬的關係 — 把 message rate 從日常的 X 推到 2X 時，inter-node traffic 超過 switch 容量，publish confirm latency 開始非線性增長。

Performance test 的關鍵是把 inter-node network throughput 加入監控維度。RabbitMQ 3.8 的 Prometheus integration 提供了 `rabbitmq_raft_term_total`、`rabbitmq_channel_messages_published_total` 等指標，但 inter-node bandwidth 需要從 OS 層（`node_exporter` 的 network bytes）或 switch 層取得。

### 調整 mirroring 配置

Runtastic 從 `ha-mode: all`（所有 node 都 mirror）調整為 `ha-mode: exactly, ha-params: 2`（只 mirror 到 2 個 node）。這把每條訊息的網路複製量從 N 倍降到 2 倍，在可靠性（2 個 copy 可以容忍 1 node failure）跟網路成本之間取得平衡。

對可靠性要求最高的 queue（交易相關），維持 `ha-mode: all` 但把這些 queue 移到頻寬更高的專屬 network segment。

### 遷移到 Quorum queue 的動機

Mirrored queue 的另一個問題是同步機制 — 新 mirror 加入時需要全量同步（sync），sync 期間 queue 可能暫停接受新訊息。RabbitMQ 3.8 引入的 Quorum queue 用 Raft consensus 取代 mirrored queue 的 GM（Guaranteed Multicast），在網路效率跟故障恢復上都有改進。

Runtastic 的案例是「為什麼應該評估從 mirrored queue 遷到 quorum queue」的典型動機 — mirrored queue 的網路成本跟同步行為在規模化時成為瓶頸。

## 取捨

| 面向         | ha-mode: all               | ha-mode: exactly 2   | Quorum queue            |
| ------------ | -------------------------- | -------------------- | ----------------------- |
| 網路成本     | 每條訊息 × N node          | 每條訊息 × 2 node    | 每條訊息 × majority     |
| 可容忍的故障 | N-1 node failure           | 1 node failure       | minority node failure   |
| 新 node 加入 | 全量同步（可能暫停 queue） | 全量同步（影響面小） | Raft log replay（漸進） |
| 適合場景     | 小 cluster、低流量         | 中 cluster、中流量   | 中大 cluster、推薦路徑  |

## 回寫教材的連結

- [3.1 broker basics](/backend/03-message-queue/broker-basics/)：broker 的 replication 跟 network 成本的關係
- [RabbitMQ vendor 頁](/backend/03-message-queue/vendors/rabbitmq/)：mirrored queue vs quorum queue 的詳細比較
- [RabbitMQ queue types](/backend/03-message-queue/vendors/rabbitmq/queue-types-classic-quorum-stream/)：Classic / Mirrored / Quorum / Stream 四種 queue type 的取捨
- [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/)：broker 的 inter-node 網路作為 pipeline 健康指標

## 判讀徵兆

以下訊號出現時，應該回讀本案例：

- RabbitMQ cluster 使用 `ha-mode: all` 且 node 數量 > 3
- Publish confirm latency 在流量上升時非線性增長
- Broker 的 CPU / memory / disk 指標正常但 publish 變慢
- Broker 間的 network traffic 佔比超過 cluster 總頻寬的 50%
- 新 mirror 加入時 queue 出現暫停或大量延遲

## 引用源

- [Runtastic RabbitMQ Performance Case Study](https://seventhstate.io/portfolio/portfolio-runtastic/)
