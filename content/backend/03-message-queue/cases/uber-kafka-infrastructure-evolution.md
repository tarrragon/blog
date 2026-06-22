---
title: "3.C6 Uber：Kafka 事件平台演進"
date: 2026-05-07
description: "事件平台從團隊自管走向多租戶共享基礎設施。"
weight: 6
tags: ["backend", "message-queue", "case-study"]
---

Uber 的 Kafka 演進案例揭露了 MQ 從「幾個團隊自管的 broker」到「全公司共享的事件平台」的治理轉折點。轉折的核心判斷是：規模化之後，broker 容量擴展的成本小於 workload 治理缺失的成本。

## 業務背景

Uber 的事件流涵蓋行程追蹤、司機定位、計費事件、推播通知、即時定價、ETA 計算跟 analytics。早期各團隊各自架設 Kafka 叢集，隨著 Kafka 在 Uber 內部的採用率上升，叢集數量跟 topic 數量快速增長，但沒有統一的治理。

Uber 的 Kafka 規模峰值達到每秒數百萬筆訊息、數十個叢集、數千個 topic。在這個規模下，管理壓力從「單一叢集的 broker 夠不夠」轉到「誰在用、用多少、怎麼收費、故障時誰負責」。

## 技術挑戰

### 團隊自管的碎片化

各團隊各自架設 Kafka 時，每個叢集的版本、配置、監控、備份策略都不同。運維知識散落在各團隊，沒有共享的 runbook 或值班流程。某個團隊的 Kafka 出問題時，其他團隊幫不上忙；知識在人員流動時遺失。

碎片化的另一個後果是資源浪費。每個團隊各自預留的容量加總起來遠大於集中管理所需。低流量團隊的叢集常年使用率低於 10%，但因為自管模式下沒有共享容量的機制，資源無法調配。

### Topic 爆炸與無主 topic

沒有 topic 建立的治理流程時，任何人都可以建 topic。Topic 的命名不一致、retention 設定不一致、owner 不明。離職的工程師建立的 topic 仍在接收資料、佔用 broker 資源，但沒人知道這些 topic 服務什麼業務。

LinkedIn 後來也遇到同樣的問題並開發了 [TopicGC](/backend/03-message-queue/cases/linkedin-topicgc-kafka-governance/) 做 topic 生命週期管理。Uber 的解法路線類似 — 把 topic 建立變成需要 owner、retention policy 跟業務標籤的審核流程。

### 故障排查的責任不清

叢集內的故障（broker OOM、partition leader 不均衡、consumer lag spike）需要 Kafka 專業知識排查。團隊自管模式下，每個團隊都需要一定程度的 Kafka 運維能力，但多數團隊的核心能力是業務邏輯而非 MQ 運維。

故障排查的慣性是「先問 Kafka 團隊有沒有人可以幫忙」— 但沒有正式的 Kafka 團隊，所以問的是「上次修過 Kafka 的那個人」。

## 解法：平台化

Uber 的解法是把 Kafka 從分散自管收斂到集中平台 — 一個專責的 Kafka platform team 統一管理所有叢集、提供標準化的使用介面。

### 多租戶治理

平台化的核心是多租戶模型 — 每個業務團隊是一個 tenant，tenant 有 quota（ingestion rate、partition 數量上限、retention 上限）跟 cost attribution。

Quota 的目的是防止單一 tenant 的爆量拖累整個平台。Cost attribution 的目的是讓 tenant 看到自己的用量跟成本，驅動合理使用。

### 標準化 topic 管理

Topic 的建立走 self-service portal — 團隊填寫 owner、業務用途、預估流量、retention 需求，portal 自動配置 topic 並建立監控。沒有 owner 的 topic 不允許建立；owner 離職時 topic 需要交接或標記為候選淘汰。

### 統一監控與值班

Platform team 統一監控所有叢集的 broker 健康（replication lag、under-replicated partitions、disk usage、CPU），提供共用的 dashboard 跟 alert。值班由 platform team 負責 broker 層面的問題，業務層面的問題（consumer 設計錯誤、message 格式不對）由各 tenant team 自行處理。

## 取捨

| 面向         | 團隊自管                        | 平台化                               |
| ------------ | ------------------------------- | ------------------------------------ |
| 自主性       | 高（團隊想怎麼配就怎麼配）      | 低到中（受 quota 跟 policy 約束）    |
| 運維負擔分配 | 分散（每個團隊各自負擔）        | 集中（platform team 吸收 broker 層） |
| 資源利用率   | 低（各自預留、無法共用）        | 高（共享容量、動態分配）             |
| 治理一致性   | 低（版本、配置、命名各自為政）  | 高（統一版本、統一配置標準）         |
| 故障影響面   | 小（自管叢集只影響自己的團隊）  | 大（共享平台故障影響所有 tenant）    |
| 專業知識需求 | 每個團隊都要一些 Kafka 運維知識 | 集中在 platform team                 |

平台化的最大風險是共享平台成為單點 — broker 故障影響所有 tenant。Uber 用跟 LinkedIn 類似的分層叢集策略（critical vs best-effort）降低共享風險，但這也讓平台的運維複雜度上升。

## 回寫教材的連結

- [3.1 broker basics](/backend/03-message-queue/broker-basics/)：broker 容量規劃跟 topic 管理的基礎。
- [6.14 dependency reliability budget](/backend/06-reliability/dependency-reliability-budget/)：共享 Kafka 平台作為 dependency，tenant team 的 reliability budget 怎麼計算。
- [3.4 consumer design](/backend/03-message-queue/consumer-design/)：平台化後 consumer 設計的規範跟限制。
- [4.15 cost attribution](/backend/04-observability/cost-attribution/)：平台成本歸因到 tenant 的做法。

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- 組織內有 3 個以上團隊各自架設 Kafka、版本跟配置不統一
- Topic 數量持續增長但沒人能說清楚哪些 topic 還在用
- 故障排查依賴特定個人而非共用的 runbook
- 叢集資源利用率低但各團隊仍要求擴容
- 管理層問「Kafka 總共花多少錢、誰在用」但沒人能回答

## 引用源

- [Building Uber's Kafka Infrastructure](https://www.uber.com/en-TW/blog/kafka/)
