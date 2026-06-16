---
title: "Firestore"
date: 2026-06-16
description: "Firebase / Google Cloud 的 serverless document database、collection / document 模型、client 直連 + Security Rules、realtime listener 與 offline 同步、BaaS bundle 的資料層面"
weight: 10
tags: ["backend", "database", "vendor", "firestore", "document", "baas"]
---

Firestore 是 Google 的 serverless document database、承擔 mobile app 與 SPA 的正式狀態與多裝置即時同步責任。它的資料形狀是 collection 下的 document、存取模型是 client 端用 SDK 直連、授權靠 Security Rules，而不是經過自己寫的後端服務。Firestore 同時是 [Firebase](/backend/knowledge-cards/baas/) bundle 的資料層、也能在 Google Cloud 上單獨使用；本頁從**資料層 vendor 視角**說明它承擔什麼狀態責任、為哪種查詢付成本、何時撞牆該遷往自建。要不要採用 BaaS 這種交付形態本身、是更上層的決策，見 [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/) 與 [0.22 能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/)。

官方文件路由：[Firestore documentation](https://firebase.google.com/docs/firestore)、[Firestore data model](https://firebase.google.com/docs/firestore/data-model)、[Firestore pricing](https://firebase.google.com/docs/firestore/pricing)；本頁時間敏感的計費與限制 claim 以官方為準、最後檢查日 2026-06-16。

## 教學路線：client 直連的 document 正式狀態

Firestore 服務頁的教學目標是把「前端直接讀寫資料庫」這個存取模型的責任說清楚。讀者讀完後要能判斷 Firestore 何時是合適的正式狀態，何時因為查詢形狀、成本曲線或授權複雜度該轉向自建後端配 [PostgreSQL](/backend/01-database/vendors/postgresql/) 或留在 document model 換 [MongoDB](/backend/01-database/vendors/mongodb/)。

| 學習段              | 核心問題                                                           | 對應段落                       |
| ------------------- | ------------------------------------------------------------------ | ------------------------------ |
| Client-direct state | 前端用 SDK 直連、授權下沉到 Security Rules 後責任邊界在哪          | 定位、存取模型                 |
| Document shape      | collection / document / subcollection 如何決定查詢能力             | 資料形狀、適用場景             |
| Query boundary      | 為什麼跨 collection 報表查不出來、index 與查詢限制如何約束建模     | 不適用場景、常見陷阱           |
| Realtime / offline  | snapshot listener 與 offline persistence 解哪類多裝置同步問題      | 適用場景、跟其他 vendor 的取捨 |
| 替代路由            | 撞到報表、成本或授權牆時、遷往自建 relational 或換 document vendor | 下一步路由、遷移 playbook      |

## 定位：serverless document store + BaaS 資料層

Firestore 跟 [MongoDB](/backend/01-database/vendors/mongodb/)、[DynamoDB](/backend/01-database/vendors/dynamodb/) 同屬 NoSQL document / KV 家族，但承擔的責任層級不同：

- 資料組織成 collection 下的 document，document 可巢狀 subcollection，單 document 上限 1 MiB
- 沒有 server 端 JOIN，跨 collection 的關聯要靠 application 多次查詢自己組、或在寫入時反正規化
- 存取模型以 client SDK 直連為主，授權寫在 Security Rules（一套規則 DSL），而不是後端 API 的權限中介層
- 兩種營運模式：Firestore Native mode（行動 / web、含 realtime 與 offline）與 Datastore mode（server 端、相容舊 Datastore）

傳統定位：Firebase 行動 app 與 SPA 的後端資料層、MVP 快速驗證期、多裝置即時同步的產品。

資料層視角的定位：一塊 *managed serverless document store*，把 capacity、replication、failover、scaling 全部交給平台，代價是查詢能力與資料模型沿平台特性生長。

## 資料形狀與查詢邊界

Firestore 為「已知路徑的 document 讀寫」付成本，不為「任意欄位的 ad-hoc 查詢」付成本。這個取向決定了它的甜蜜區與牆：

- 單 document 與單 collection 內的 key-based / 條件查詢高效，且每筆查詢都要有對應 index（單欄 index 自動建立、複合查詢要建 composite index）
- 查詢結果集的計費與大小跟「讀了幾筆 document」成正比，不是跟「掃了多少」— 一次回 10,000 筆就計 10,000 次 read
- 缺少 server 端 aggregation pipeline 與 JOIN；跨集合報表（例如「本月各地區訂單金額」）在 Firestore 上要嘛預先把彙總寫成一份 document、要嘛把資料複製到分析系統
- 沒有原生全文搜尋，全文需求要接專門的 [search index](/backend/knowledge-cards/search-index/)（Algolia、Elasticsearch / OpenSearch）

這條查詢邊界是 Firestore 最容易被低估的設計約束。它不是「功能還沒做」，而是 client 直連 + serverless 計費模型的必然結果：把任意 ad-hoc 查詢開放給前端，等於把不可預測的成本與掃描壓力暴露在公網。建模時要先窮舉 access pattern、再決定 document 結構，跟 [DynamoDB single-table design](/backend/01-database/vendors/dynamodb/single-table-design-pattern/) 的 access-pattern-first 思路同源。

## 一致性、realtime 與容量特性

**一致性**：

- 單 document 讀寫與「查詢結果在同一 region 內」提供 strong consistency
- 多 region 部署靠平台複製、跨 region 讀取可能有延遲；一致性語意由平台決定、不可調到自管資料庫那種 isolation level 顆粒

**Realtime 與 offline**：

- snapshot listener 讓 client 訂閱 query 結果、資料變更即時推送，是多裝置同步的核心能力
- 行動 / web SDK 內建 offline persistence，斷線時讀寫本地快取、回線後同步，這是自建 REST API 要額外工程才有的能力

**容量與寫入熱點**：

- serverless 自動擴縮，無 connection 概念，前端裝置數不直接轉成資料庫連線壓力
- 單一 document 的高頻寫入會撞到 contention（官方建議單 document 的持續寫入維持在每秒個位數量級、高頻計數器要用 distributed counter 分片）
- 寫入吞吐與索引維護成本綁在一起：每多一個 index、寫入就多一份維護成本

容量特性的時間敏感數字（每秒寫入軟上限、單 document contention 門檻）以 [官方 best practices](https://firebase.google.com/docs/firestore/best-practices) 為準，設計高頻寫入前先查當前限制。

## 適用場景

**1. 行動 app / SPA 的 MVP 後端**：

- 認證接 Firebase Auth、資料存 Firestore、推播接 Cloud Messaging，整個 MVP 沒有自己的後端服務
- 對應 [0.21](/backend/00-service-selection/delivery-mode-selection/) BaaS 段的「把後端工程師這個角色延後」

**2. 多裝置即時同步**：

- 協作筆記、聊天、即時看板這類「一處改、多處即時更新」的產品
- snapshot listener + offline persistence 是這類需求的天然形狀

**3. access pattern 穩定的 document 工作負載**：

- user profile、設定、feed item、活動紀錄這類讀多寫少、查詢路徑固定的資料
- 跟 [source of truth](/backend/knowledge-cards/source-of-truth/) 對齊：Firestore 可以是這些資料的正式狀態

## 不適用場景

**1. 跨實體報表與分析查詢**：

- 跨 collection JOIN、ad-hoc 篩選、彙總統計在 Firestore 上要靠資料複製工程
- 替代：自建 relational（[PostgreSQL](/backend/01-database/vendors/postgresql/)）或把資料同步進分析系統

**2. 成本對流量敏感的高讀取場景**：

- 計費隨 document read / write / delete 線性成長，高流量下可能超過自建
- 替代：自管資料庫 + 應用層 [cache](/backend/02-cache-redis/)，把熱讀取的單位成本壓下來

**3. 複雜授權需要可測試的控制面**：

- client 直連模型把授權全塞進 Security Rules，規則長到難以 review / 測試時，控制面風險升高
- 替代：把授權拉回後端 API 中介層（自建後端 + 任意資料庫）

**4. 強一致的多實體交易**：

- Firestore 有 transaction 與 batch write，但跨大量 document 的複雜交易不是它的主場
- 替代：relational database 的多表交易

## 跟其他 vendor 的取捨

**vs MongoDB（document 對 document）**：

- Firestore：serverless、client 直連、realtime listener、GCP / Firebase 綁定、查詢能力受限
- MongoDB：查詢與 aggregation 彈性高、跨雲、要自管或用 Atlas managed、走後端中介存取
- 選 Firestore：行動 / 即時同步 / 想省整層後端
- 選 MongoDB：document model 但要彈性查詢、aggregation、跨雲可攜，見 [db3 vendor selection](/backend/01-database/vendors/db3-vendor-selection/)

**vs DynamoDB（serverless NoSQL 對 serverless NoSQL）**：

- Firestore：GCP / Firebase 生態、內建 realtime 與 offline、client 直連為主
- DynamoDB：AWS 生態、access-pattern-first KV、通常走後端整合、streams 接事件驅動
- 兩者的 access-pattern-first 建模思路相近，差別在生態與 client 直連的有無

**vs SQLite（行動端的反向選擇）**：

- Firestore：雲端 store、自動多裝置 sync、realtime
- SQLite：embedded、offline-first、無 sync（見 [SQLite vendor](/backend/01-database/vendors/sqlite/)）
- 選 Firestore：需要跨裝置同步與即時更新
- 選 SQLite：純單機 / offline、不需要雲端同步

**vs Supabase（BaaS bundle 的另一條路）**：

- Firestore：document model、Google 的 BaaS bundle 資料層
- Supabase：底層是 PostgreSQL（relational）、開源 BaaS bundle，遷出時資料是標準 SQL
- 兩者都是 client 直連 + 規則授權的 BaaS 形狀，差別在資料模型（document vs relational）與遷出時的資料可攜性；Supabase 的資料層判讀見 [Managed PostgreSQL 比較](/backend/01-database/vendors/postgresql/managed-pg-comparison/)，選型層錨點見 [0.22](/backend/00-service-selection/capability-buy-vs-build/)

## 容量規劃要點

**1. access pattern 先於 document 結構**：

- 列出 application 對資料的所有讀寫路徑、再設計 collection / document 形狀
- access pattern 沒想清楚就建模，後面報表查不出來要重做

**2. 反正規化換查詢效率**：

- 為了避免跨 collection 多次查詢，常把關聯資料冗餘寫進同一 document
- 代價是寫入時要維護多份副本的一致性，對應 [1.9 Reconciliation](/backend/01-database/reconciliation-data-repair/)

**3. index 與寫入成本綁定**：

- 複合查詢要先建 composite index、否則查詢直接失敗
- 每個 index 增加寫入維護成本，移除用不到的 index 是容量優化的一環

**4. 高頻寫入用 distributed counter**：

- 單一 document 撞到 contention 上限時，把計數拆成多個 shard document 再彙總

**5. 成本以 document 數計，不以掃描量計**：

- 容量估算要算「每個畫面 / API 觸發幾次 read」、乘上日活與頻率
- 把熱讀取移到 [應用層快取](/backend/02-cache-redis/cache-aside/) 是壓低 read 計費的主要手段

## 常見陷阱

- **把 Firestore 當關聯式用**：規劃了一堆需要 JOIN 的 collection、上線後跨集合查詢全靠 client 自己組、latency 與 read 成本爆炸
- **報表需求到了才發現查不出來**：老闆要月報、Firestore 沒有 aggregation pipeline、被迫臨時搭資料複製管線
- **Security Rules 長到沒人敢改**：授權全寫在規則 DSL、沒有版本控制與測試、變更時靠人工推敲
- **單 document 當高頻計數器**：直播按讚 / 即時計數寫爆單一 document 的 contention 上限
- **忽略 read 計費規模**：list 畫面一次回上千筆、每次重整都計上千次 read、帳單月底才浮現

## Deep article 章節群

Firestore overview 負責第一輪服務判斷；vendor 特有機制的設定、踩坑與容量規劃拆成 deep article。下表是目前已建立的實作層教材，讀法是先讀 overview 判斷服務適配，再按撞到的壓力選 deep article。

| 機制       | 文件                                                                                                               | 教學責任                                                             |
| ---------- | ------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| 授權控制面 | [Security Rules 授權建模與可測試化](/backend/01-database/vendors/firestore/security-rules-authz-modeling/)         | 規則求值模型、可組合 function、emulator 單元測試、把規則當程式碼治理 |
| 高頻寫入   | [高頻寫入與 distributed counter](/backend/01-database/vendors/firestore/distributed-counter-high-frequency-write/) | 單 document contention 邊界、分片計數、shard 數與讀寫成本取捨        |
| 資料建模   | [document 反正規化與一致性維護](/backend/01-database/vendors/firestore/denormalization-fanout-consistency/)        | 反正規化決策、fan-out write、副本同步、不一致修復                    |
| 即時同步   | [realtime listener 扇出與成本](/backend/01-database/vendors/firestore/realtime-listener-fanout-cost/)              | snapshot 推送模型、訂閱範圍設計、re-read 計費、連線規模              |

讀法路由：撞到資料外洩 / 越權，讀 Security Rules；撞到熱門事件寫爆計數，讀 distributed counter；改一筆要連動改一千筆，讀反正規化；即時功能帳單失控，讀 realtime listener。撞到報表 / 成本 / 授權整體性的牆，走 [遷往自建 relational](/backend/01-database/vendors/firestore/migrate-to-relational/)。

## Hands-on 操作演練

deep article 講機制判讀，[Hands-on 操作路線](/backend/01-database/vendors/firestore/hands-on/) 把機制轉成可在本地 [Firebase Emulator](https://firebase.google.com/docs/emulator-suite) 跑的演練——零雲端成本、可重跑、產出可驗證 artifact。三個 lab：[emulator quickstart](/backend/01-database/vendors/firestore/hands-on/local-emulator-quickstart/)（建立共用環境）、[Security Rules test lab](/backend/01-database/vendors/firestore/hands-on/security-rules-test-lab/)（規則自動化測試 + 接 release gate）、[distributed counter lab](/backend/01-database/vendors/firestore/hands-on/distributed-counter-lab/)（分片計數機制驗證）。lab 全程標明 emulator 驗得了什麼（功能行為、規則求值）、驗不了什麼（計費、寫入軟上限要回雲端）。

## 已知 limitation 與後續路由

Firestore overview 完成服務判斷、資料形狀、查詢邊界與替代路由；deep article 章節群覆蓋授權、高頻寫入、反正規化與即時同步四個機制；hands-on 章節群提供 emulator 演練。後續可補的方向：offline persistence 的衝突解決深入、realtime listener 在雲端的成本量測 lab（emulator 不計費、要在雲端 staging 跑）。

## 下一步路由

- 完整 T1 對照：[01-database vendors index](/backend/01-database/vendors/)
- 同類對比：[MongoDB vendor](/backend/01-database/vendors/mongodb/)（彈性查詢 document）/ [DynamoDB vendor](/backend/01-database/vendors/dynamodb/)（access-pattern-first KV）/ [db3 vendor selection](/backend/01-database/vendors/db3-vendor-selection/)（document / KV / multi-model 三方選型）
- 遷出方向：[Firestore → 自建 relational](/backend/01-database/vendors/firestore/migrate-to-relational/)（撞到報表 / 成本 / 授權牆後的 Type E 重建模 playbook）
- 操作演練：[Firestore Hands-on](/backend/01-database/vendors/firestore/hands-on/)（emulator quickstart、Security Rules 測試、distributed counter lab）
- 容量背景：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- 選型上層：[0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/) / [0.22 能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/) / [BaaS 知識卡](/backend/knowledge-cards/baas/)
- 從託管平台遷出的資產線盤點：[10.3 託管形態遷出](/backend/10-system-evolution/managed-platform-exit/)
- 官方：[Firestore documentation](https://firebase.google.com/docs/firestore)、[Firestore best practices](https://firebase.google.com/docs/firestore/best-practices)、[Firestore pricing](https://firebase.google.com/docs/firestore/pricing)
