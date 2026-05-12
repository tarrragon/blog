---
title: "9.C27 Disney+：DynamoDB 撐每日數十億動作的觀看歷史"
date: 2026-05-12
description: "Disney+ 用 DynamoDB 撐每日數十億動作的觀看歷史、watchlist、播放進度等串流 metadata"
weight: 27
tags: ["backend", "performance", "capacity", "case-study", "db-kv", "aws", "predictable-peak"]
---

這個案例的核心責任是說明「串流平台 metadata 層」的工作負載 — 跟 [9.C13 Hotstar IPL](/backend/09-performance-capacity/cases/hotstar-ipl-eighteen-million-concurrent/) 的「live streaming 直播容量」是同產業不同議題。Disney+ 的 metadata 層處理「播了什麼、看到哪、下次推薦什麼」、是串流平台的「control plane」、不是「data plane」。

## 觀察

Disney+ 在 DynamoDB 的關鍵敘述（引自 [DynamoDB Customers](https://aws.amazon.com/dynamodb/customers/)）：

| 指標         | 數字                                     |
| ------------ | ---------------------------------------- |
| 每日動作量   | billions of actions daily                |
| 主要工作負載 | content metadata + watch list management |
| 服務組合     | Amazon DynamoDB                          |
| 服務地理     | global                                   |

每個用戶動作（播放、暫停、跳過、加入 watchlist、評分）都是一次 DynamoDB 寫入。每次打開 app 又是多次讀（自己的 watchlist、最近播放、繼續觀看）。

## 判讀

Disney+ 案例揭露三個串流平台 metadata 層的工程重點。

1. **「每日數十億動作」= read + write 都要撐**：跟 [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) 的 18:1 讀寫比不同、串流 metadata 通常接近 5:1 read-heavy（每動作 1 寫、每 session 5 讀）。partition key 設計通常用 user_id、天然均勻、不會 hot partition。對應 [01 資料庫模組](/backend/01-database/) 的 schema design。
2. **新片發布是 predictable-peak**：Marvel / Star Wars / Disney 動畫 新片上線首日、metadata 流量可衝 3-5 倍 — 因為「全平台用戶同時打開該片頁面」。這比一般 Black Friday 集中、像 [9.C13 Hotstar IPL](/backend/09-performance-capacity/cases/hotstar-ipl-eighteen-million-concurrent/) 的集中型流量。對應 [9.11 高峰事件準備](/backend/09-performance-capacity/) 的內容發布事件容量規劃。
3. **watchlist + 播放進度需要跨裝置即時同步**：用戶在手機看到一半、晚上回家用電視繼續、進度必須跨裝置同步。這層需求對 DynamoDB Global Tables（multi-region active-active）特別適合。對應 [01.5 transaction boundary](/backend/01-database/transaction-boundary/) 的最終一致性可接受場景。

需要警惕：「billions of actions daily」沒指明具體數字（10 億、100 億 還是 數十億？）。讀此類短篇案例只能取「量級對標」、不能套用具體數字。

## 策略

可重用的工程做法：

1. **串流平台分「metadata 層」「content delivery 層」**：metadata（watchlist、播放進度、推薦）用 DynamoDB / Cosmos DB；content（video file）用 CDN + S3 / object storage。兩者完全分開、互不影響。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 control plane vs data plane、跟 [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) 的同類思維。
2. **新片發布像 mini Black Friday、要 pre-scaling**：發布時間已知、流量倍數可預估（根據前幾部）、可以提前 1-2 天 pre-scale DynamoDB capacity。對應 [9.11 高峰事件準備](/backend/09-performance-capacity/)。
3. **DynamoDB Global Tables 是跨裝置同步的有效方案**：用戶在不同 region 登入同帳號、寫入會自動同步到其他 region。對應 [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) 的 multi-region active-active。

跨平台等效：Netflix 同類 metadata 用 Cassandra + EVCache（[9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 提及）、HBO Max 用 Aurora、Apple TV+ 用 FoundationDB + Cassandra — 各家串流的 metadata 技術棧不同、但「分層解耦」的工程哲學一致。

## 下一步路由

- 對照其他串流案例 → [9.C13 Hotstar IPL](/backend/09-performance-capacity/cases/hotstar-ipl-eighteen-million-concurrent/)（live）/ [9.C29 NTT DOCOMO Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)
- 想理解 metadata 層 → [01 資料庫模組](/backend/01-database/) + [9.5 瓶頸定位流程](/backend/09-performance-capacity/)
- 想做內容發布 pre-scaling → [9.11 高峰事件準備](/backend/09-performance-capacity/) + [9.C1 Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)
- 想做跨裝置同步設計 → [9.C24 Genesys multi-region](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)

## 引用源

- [Amazon DynamoDB Customers](https://aws.amazon.com/dynamodb/customers/)
- [Amazon DynamoDB use cases for media and entertainment customers](https://aws.amazon.com/blogs/database/amazon-dynamodb-use-cases-for-media-and-entertainment-customers/)
