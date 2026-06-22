---
title: "3.C23 Bloomberg：多租戶 vhost + 自助平台化"
date: 2026-05-18
description: "Bloomberg 從幾個團隊推到上百個團隊、靠自助 vhost 註冊跟專用叢集分離應用與 broker。"
weight: 23
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

Bloomberg 的 RabbitMQ 平台化案例揭露了 broker 從幾個團隊的工具演變成上百個團隊的共享基礎設施時，治理責任邊界應該前置設計，而非在規模化之後補救。

## 業務背景

Bloomberg 有 5000+ 工程師，內部系統涵蓋金融資料處理、交易系統、新聞分發與分析平台。RabbitMQ 的使用從最初幾個團隊的 microservice 解耦開始，逐步擴展到上百個團隊。到 2019 年，Bloomberg 的 RabbitMQ 基礎設施每週處理超過 2 億條訊息，尖峰每秒數萬條。

這個規模下，原本由平台團隊手動配置的 queue / exchange / binding 模式無法持續 — 上百個團隊各自有不同的 queue 需求，平台團隊成為所有變更的人工瓶頸。

## 技術挑戰

### 多租戶隔離

多個團隊共用同一個 RabbitMQ cluster 時，一個團隊的 queue 爆量或 consumer 故障可能影響其他團隊的訊息處理。RabbitMQ 的 Erlang scheduler 是共用的 — 一個 queue 的 message accumulation 會消耗 broker 的記憶體跟 CPU，影響同 cluster 上所有 queue 的效能。

隔離需要在 broker 層實作，client 端的 best practice（限制 message size、設定 TTL）只能降低風險但無法保證隔離。

### 自助配置的安全邊界

讓上百個團隊自助建立 queue / exchange / binding 需要明確的安全邊界 — 團隊 A 能在自己的 namespace 建立資源，但不能存取團隊 B 的 queue。RabbitMQ 的 vhost 機制提供了這個隔離單位，但 vhost 的建立跟權限配置本身需要自動化。

### 容量規劃與配額

共享 cluster 的容量被所有租戶分攤。沒有配額機制時，一個團隊的 queue 可以無限增長直到 broker 記憶體告警、觸發 flow control、影響全部租戶。配額需要在 queue 層面設定上限（max-length、max-length-bytes），同時提供超出配額時的降級策略而非直接拒絕。

## 解法：vhost 分層 + 自助平台

### Vhost 作為租戶邊界

Bloomberg 把 vhost 作為多租戶隔離的基本單位。每個團隊（或每個應用）分配一個 vhost，vhost 內的 queue / exchange / binding 只對該團隊可見。跨 vhost 的訊息傳遞透過 shovel 或 federation plugin，需要顯式配置，預設不互通。

Vhost 的隔離粒度是「資源可見性 + 權限」而非「硬體資源」。同 cluster 上的 vhost 仍然共用 Erlang runtime 跟記憶體。完全的硬體隔離需要獨立 cluster — Bloomberg 對高敏感度的工作負載（交易相關）使用專用 cluster，一般業務共用大 cluster + vhost 隔離。

### 自助 vhost 註冊

Bloomberg 建立了內部自助平台，團隊透過 API 或內部 portal 申請 vhost。申請時需要提供：應用名稱、預期的 message rate、保留期限、是否需要 HA（mirrored / quorum queue）。平台自動建立 vhost、設定權限、分配連線端點。

自助流程的價值是去除平台團隊的人工瓶頸。新團隊從申請到拿到可用的 RabbitMQ 端點，時間從「提 ticket 等平台團隊排程」縮短到「填表 → 自動配置 → 立即可用」。

### 配額與監控

每個 vhost 有預設配額（max-length、max-connections）。超出配額時 broker 行為可配 — drop-head（丟最舊的訊息）或 reject-publish（拒絕新訊息）。配額不是懲罰機制，是保護共享 cluster 的防線。

監控用 RabbitMQ 的 management plugin + Prometheus exporter，按 vhost 維度匯出 queue depth、message rate、connection count。每個 vhost 的 dashboard 對應到 owner 團隊，讓團隊自行判讀自己的使用狀況。

## 取捨

**Vhost 隔離 vs 硬體隔離**：vhost 隔離成本低（不需要額外 cluster），但隔離程度有限 — Erlang scheduler 跟記憶體仍然共用。Bloomberg 的做法是多數團隊用 vhost 隔離、高敏感度工作負載用專用 cluster，兩者共存。

**自助配置 vs 中央管控**：自助配置加速團隊迭代，但也增加了 configuration drift 的風險。Bloomberg 透過配額跟自動化審計（定期掃描 vhost 的 queue 狀態、alert 異常 pattern）平衡自助跟管控。

## 回寫教材的連結

- [3.1 broker basics](/backend/03-message-queue/broker-basics/)：broker 的多租戶治理責任
- [3.C6 Uber Kafka 平台](/backend/03-message-queue/cases/uber-kafka-infrastructure-evolution/)：Kafka 生態的多租戶治理比較 — Kafka 用 topic-level ACL + quota，RabbitMQ 用 vhost
- [4.18 operating model](/backend/04-observability/observability-operating-model/)：平台團隊跟服務團隊的 ownership 邊界

## 判讀徵兆

以下訊號出現時，應該回讀本案例：

- RabbitMQ 的使用團隊數從個位數增長到雙位數、平台團隊成為配置瓶頸
- 單一 cluster 上的 queue 數量超過數百個、owner 不明
- 某個團隊的 queue 爆量影響了其他團隊的 consumer 效能
- 新團隊要用 RabbitMQ 但平台團隊的 ticket 要排隊數天
- 沒有 per-team 的 message rate 或 queue depth 監控

## 引用源

- [Growing a Farm of Rabbits at Bloomberg](https://www.cloudamqp.com/blog/growing-a-farm-of-rabbits.html)
