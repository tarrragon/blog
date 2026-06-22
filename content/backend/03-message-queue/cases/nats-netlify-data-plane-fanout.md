---
title: "3.C34 Netlify：NATS 當全球 metrics/logs 統一資料平面"
date: 2026-05-18
description: "Netlify 70K+ 網站、10 億 PV/月、跨多雲、NATS 當 all-purpose data plane fan-out bus、超 RabbitMQ 評估。"
weight: 34
tags: ["backend", "message-queue", "case-study", "nats"]
---

Netlify 的 NATS 選型示範了 subject-based fan-out 在跨雲觀測資料平面的優勢 — 協議極簡帶來的是部署簡單跟 client 整合成本低，代價是放棄持久化保證。

## 業務背景

Netlify 是靜態網站跟 serverless function 的部署平台，服務 70,000+ 網站、近月 10 億 page view。基礎設施橫跨 Rackspace、AWS、GCP、Digital Ocean 四個雲端供應商。每個服務節點都會產生 metrics 跟 logs，需要一條統一的資料路徑把這些訊號從各地收集到中央觀測系統。

## 技術挑戰

### 跨雲統一資料平面

四個雲的服務各自有不同的網路拓樸跟存取方式。觀測資料需要跨雲收集到同一個目的地（Elasticsearch），但直接讓每個服務 HTTP POST 到 Elasticsearch 會有連線管理、背壓、格式轉換的問題分散在每個服務裡。

Netlify 需要一個中介層 — 各服務把 metrics / logs 推到中介層，中介層負責 fan-out 到下游消費者（Elasticsearch、即時 dashboard、告警系統）。

### 選型：NATS vs RabbitMQ

Netlify 評估了 RabbitMQ 跟 NATS。RabbitMQ 在功能上更完整（持久化 queue、DLQ、ack 機制），但 Netlify 的觀測資料場景有三個特性讓 NATS 更合適：

- **資料可丟**：metrics 跟 logs 是 best-effort 的觀測資料，遺失幾秒的資料不影響業務 — 持久化保證帶來的運維成本大於收益
- **Fan-out 是主要模式**：同一份資料要被多個消費者訂閱（Elasticsearch、即時 tail、告警），NATS 的 subject-based pub/sub 天然支援，RabbitMQ 需要設 exchange + 多個 binding
- **部署極簡**：NATS server 是單一 binary、零依賴、幾秒鐘啟動，跨四個雲部署時每個雲跑一個 NATS node 的運維成本遠低於 RabbitMQ cluster

## 解法與取捨

### 架構

Netlify 用 Core NATS（非 JetStream）搭建觀測資料平面：

- **Producer 端**：用 logrus 的 NATS hook 讓所有 Go 服務的 structured log 自動推到 NATS subject；另用 log-tail 工具從 file-based log 讀取推送
- **Consumer 端**：一個 elastinats 消費者訂閱 NATS subject、批次寫入 Elasticsearch；其他消費者可以各自訂閱同一個 subject 做即時處理

Subject 的命名用階層式結構（例如 `logs.production.api`），讓消費者可以用 wildcard 訂閱整個子樹（`logs.production.*`）或特定服務。

### 取捨

| 面向          | 選擇                    | 代價                                                   |
| ------------- | ----------------------- | ------------------------------------------------------ |
| 持久化        | 放棄（Core NATS）       | NATS server 重啟時 in-flight 的訊息遺失                |
| Ack 機制      | 放棄（fire-and-forget） | Consumer 處理失敗的訊息不會被重送                      |
| 跨雲連接      | NATS cluster            | 需要跨雲的網路連線、延遲影響 cluster 一致性            |
| Consumer 擴展 | 多個訂閱者各自訂閱      | 每個消費者收到全量資料、沒有 consumer group 的分攤機制 |

Core NATS 的 fire-and-forget 語意在觀測資料場景是有意的選擇 — 觀測資料的價值隨時間快速衰減，遺失一秒鐘的 metrics 不影響趨勢判讀。如果場景需要持久化（例：audit log、交易事件），Core NATS 就不適合，需要 JetStream 或其他有持久化保證的 broker。

## 回寫教材的連結

- [3.1 broker basics](/backend/03-message-queue/broker-basics/)：Core NATS 的 fire-and-forget 是 broker 可靠性光譜的一端（at-most-once），Kafka 跟 RabbitMQ 在另一端（at-least-once / durable）
- [NATS vendor 頁](/backend/03-message-queue/vendors/nats/)：Core NATS vs JetStream 的選型判準 — 本案例是純 Core NATS 的代表場景
- [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/)：Netlify 的 NATS 資料平面在觀測 pipeline 架構中扮演 collector 跟 storage 之間的 transport 層

## 判讀徵兆

讀者在自己的系統看到以下訊號時，應該回讀本案例：

- 觀測資料（metrics / logs）需要跨多個雲或多個 datacenter 收集到中央系統
- 現有的 broker（RabbitMQ / Kafka）在觀測資料場景的運維成本跟資料價值不成比例
- Fan-out 是主要消費模式 — 同一份資料需要被多個下游系統訂閱
- 對 message delivery 的可靠性要求是 best-effort 而非 at-least-once

## 引用源

- [Why Netlify chose NATS](https://nats.io/blog/netlify-nats-blog/)
