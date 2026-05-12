---
title: "9.C15 拓元 Tixcraft：售票搶購的瞬間爆量架構"
date: 2026-05-12
description: "拓元用 DynamoDB 當寫入緩衝 + 傳統伺服器當慢速消費者、承受 100K+ 同時選位 + 30 秒從 6 台擴到 800 台"
weight: 15
tags: ["backend", "performance", "capacity", "case-study", "db-kv", "aws", "flash-sale-spike"]
---

這個案例的核心責任是說明「售票搶購型 flash-sale」的負載形狀 — 跟現有所有案例都不同的極端形狀。售票開賣在精確時間點（例如 12:00:00）瞬間湧入數十萬使用者、5 分鐘內賣完、之後流量歸零。這種「t=0 起跳、t=300 結束」的負載沒有「峰值預測」可言、只有「瞬間吸收」。

## 觀察

拓元 Tixcraft 在 AWS 的關鍵數字（引自 [tixCraft Case Study](https://aws.amazon.com/solutions/case-studies/tixcraft/) 與 [AWS re:Invent 2015 簡報](https://www.slideshare.net/slideshow/case-sharing-tixcraft-on-aws-reinvent-2015-recap/55681198)）：

| 指標                | 數字                                      |
| ------------------- | ----------------------------------------- |
| 同時選位用戶        | 100,000+                                  |
| 訂單峰值            | 每分鐘 70,000+ 訂單、單秒最高 2,500+ 訂單 |
| 3 分鐘內售出        | 30,000+ 張票                              |
| DynamoDB IOPS 範圍  | 20 → 135,000（2015/8/29 峰值）            |
| 資源擴張幅度        | 30 分鐘內從 6 台擴到 800 台（130x）       |
| 部署時間            | 1,600 工時 → 20 分鐘                      |
| 壓測規模            | 10,000 台 t2.micro、$130 / 小時           |
| 任務總成本          | < 2 台 MacBook Pro（約 $4,200）           |
| vs 傳統基礎設施成本 | 0.26%                                     |
| 成立年份            | 2013 年底（雲原生）                       |

服務組合（依用戶提供的架構圖）：

- **入口**：Amazon Route 53（DNS）+ CloudFront + S3（靜態資源 static.tixcraft.com）
- **UI 層**：Elastic Load Balancing → EC2 跨 3 個 Availability Zone（Tixcraft UI）
- **API 層**：ELB → EC2 跨 3 個 AZ（API）+ ElastiCache 加速 session
- **資料層**：DynamoDB 作為主要寫入目標（接 UI 寫入跟 API 寫入）
- **付款層**：獨立的 EC2 Payment、連到 traditional server（合作金流、跑於企業 data center）
- **同步層**：S3 Sync + EC2 Bridge 跟 corporate data center 的 backend 雙向同步

## 判讀

拓元案例最值得讀的、是它揭露三個 flash-sale 工程設計的非直覺事實。

1. **DynamoDB 作為寫入緩衝、不是 OLTP**：搶票時的「訂單」不是即時生效、而是先丟進 DynamoDB、傳統 server 用自己能承受的速度消費。架構上 DynamoDB 扮演 *durable queue* 的角色、不是傳統 OLTP DB。這層解耦讓「前端可以擴 130 倍、後端不用同步擴」、避免後端被前端拖垮。對應 [03 訊息佇列模組](/backend/03-message-queue/) 的 outbox / async delivery 概念、跟 [01 資料庫模組](/backend/01-database/) 的 transaction boundary 分離。
2. **DynamoDB IOPS 從 20 衝到 135,000 = partition 設計能撐**：這個 6,750 倍的彈性不是 DynamoDB 魔法、是 *partition key 設計均勻* 的結果。partition key 不均、IOPS 上限是「最熱 partition 上限」、不是「總和」。對應 [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) 的同一判讀重點、跟 [9.4 Saturation Discovery](/backend/09-performance-capacity/) 的 hot partition 識別。
3. **30 分鐘擴 130 倍 = 雲原生架構的存在證明**：6 台 → 800 台不是手動操作、是 Auto Scaling Group + AMI prebuild + load balancer warmup 的組合。傳統 IDC 做不到。這層彈性是「30 秒內」flash-sale 的前置條件。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 autoscaling 與 [9.6 容量規劃模型](/backend/09-performance-capacity/)。

需要警惕的判讀盲點：

- 「限流到底怎麼做」這個工程社群關心的問題、架構圖上看不到明確元件。可能是「DynamoDB 寫入排隊 = 隱性限流」、也可能是 ELB / WAF / 應用層限流。沒有公開資訊不要過度推測。
- 2015 年的數字、用的還是 t2.micro 跟舊版 DynamoDB throughput model。現在等效實作可能會用 DynamoDB on-demand、AWS WAF、CloudFront WAF rules、或 SeatGeek-style Virtual Waiting Room（見 [9.C16](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)）。
- 「30,000 張 / 3 分鐘」是 *票房成績*、不是 *系統極限*。系統能撐遠不止這個量、只是票本身賣完了。

## 策略

可重用的工程做法：

1. **flash-sale 的核心架構模式：寫入緩衝 + 慢速消費**：前端把訂單塞進可彈性擴容的儲存（DynamoDB / Redis Stream / Kafka）、後端按自己能力消費。這個模式讓「短時間吸收洪峰」跟「實際處理」解耦。對應 [03 訊息佇列模組](/backend/03-message-queue/) 與 [01 資料庫模組](/backend/01-database/)。
2. **partition key 設計是 flash-sale 的命脈**：搶票場景天然容易 hot partition（同一場演唱會 = 同一 event_id）、必須用 composite key（event_id + user_id_hash）或 write sharding（event_id + random_suffix）分散。對應 [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)。
3. **flash-sale 必須事先 ELB / Auto Scaling 預熱**：開賣前 30-60 分鐘 pre-warm ELB、預先啟動最低額度的 EC2、避免 t=0 時冷啟動。對應 AWS 官方 [Flash Sale 工程指引](https://aws.amazon.com/blogs/mt/top-considerations-for-flash-sale-events/)。
4. **付款層獨立、不被搶票流量影響**：拓元把 Payment EC2 拉出來、直連傳統金流 server。讓「選位 + 下單」的高頻流量不會塞爆「付款」的低頻流量。對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 的關鍵路徑切分。
5. **限流（rate limiting）通常是隱性的、不一定看得到 component**：DynamoDB 寫入排隊本身就是隱性限流；也可以加 WAF rate-based rule、ELB request throttling、或前置 Virtual Waiting Room 做明確限流（見 [9.C16](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)）。

跨平台等效：GCP Cloud Spanner / Bigtable + Cloud Pub/Sub 作 buffer + GKE autoscaling；Azure Cosmos DB + Service Bus + AKS；自建 PostgreSQL + Kafka + Kubernetes 都可以實作對等架構。差異是 vendor 整合度跟擴容速度。

## 下一步路由

- 想設計 flash-sale 緩衝架構 → [03 訊息佇列模組](/backend/03-message-queue/) + [01 資料庫模組](/backend/01-database/) + [9.6 容量規劃模型](/backend/09-performance-capacity/)
- 想做 partition key 設計 → [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) + [01.6 高併發資料存取](/backend/01-database/high-concurrency-access/)
- 想做明確限流 / 排隊機制 → [9.C16 SeatGeek Virtual Waiting Room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)
- 想預熱 ELB / Auto Scaling → [05 部署平台模組](/backend/05-deployment-platform/) + [9.11 高峰事件準備](/backend/09-performance-capacity/)
- 對照其他售票市場 → [9.C17 BookMyShow](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/)（印度市場、年售 2 億張）

## 引用源

- [tixCraft Case Study (AWS)](https://aws.amazon.com/solutions/case-studies/tixcraft/)
- [tixCraft on AWS re:Invent 2015 Recap (SlideShare)](https://www.slideshare.net/slideshow/case-sharing-tixcraft-on-aws-reinvent-2015-recap/55681198)
- [tixCraft: Handling Millions of Ticketing Requests with AWS (YouTube)](https://www.youtube.com/watch?v=Bi-1xjXvKgs)
- [Top considerations for Flash sale events (AWS Cloud Operations Blog)](https://aws.amazon.com/blogs/mt/top-considerations-for-flash-sale-events/)
- [Handle traffic spikes with Amazon DynamoDB provisioned capacity](https://aws.amazon.com/blogs/database/handle-traffic-spikes-with-amazon-dynamodb-provisioned-capacity/)
