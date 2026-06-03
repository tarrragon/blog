---
title: "Aurora 多 cluster 按業務切分：微服務私有 store、blast radius 隔離與 fleet 治理"
date: 2026-06-02
description: "把所有服務塞進一個大 Aurora cluster 會讓單一服務的查詢拖垮全部；本文展開按業務 / 微服務切 cluster 的判斷維度、blast radius 隔離、共用 vs 分離的成本與運維 surface 權衡，以及多 cluster fleet 的治理一致性，含 Netflix Aurora consolidation 對照"
weight: 32
tags: ["backend", "database", "aurora", "multi-cluster", "blast-radius", "fleet", "deep-article"]
---

把所有服務的資料塞進一個大 Aurora cluster，平時運維最省事，直到某一天：報表服務跑了一個沒索引的聚合 query、佔滿 connection 與 IOPS、結帳服務跟著變慢、整個平台一起卡。問題的根源不是那個 query 本身，而是「不相關的業務共用同一個 cluster、彼此沒有隔離」。多 cluster 按業務切分要回答的是：哪些業務該各自獨立 cluster、哪些可以共用、切分後 fleet 怎麼維持治理一致。

本文不是 Aurora overview（請看 [Aurora vendor 頁](/backend/01-database/vendors/aurora/)）— 而是 cluster 邊界劃分與多 cluster 治理的實作層教學。

## 共用大 cluster 的根本問題：blast radius

單一大 cluster 把多個業務的失敗耦合在一起。一個業務的異常會透過共用資源外溢到其他業務：

- **資源競爭**：connection pool、CPU、IOPS、buffer cache 共用，一個業務的尖峰擠壓其他業務
- **failure blast radius**：cluster 故障 / 升級 / schema 變更鎖表，影響所有掛在上面的業務
- **容量規劃糾纏**：要為「所有業務尖峰的總和」規劃容量，無法針對單一業務調整
- **schema change 互相牽制**：一個業務的 migration 鎖表、其他業務跟著受影響

按業務切 cluster 的核心價值是把這些耦合切開——每個 cluster 的故障、容量、變更只影響自己的業務範圍。

## 切分判斷維度

不是「每個服務都該有自己的 cluster」（那會走向另一個極端：cluster 數爆炸、運維 surface 失控）。切分依以下維度判斷：

| 維度            | 傾向獨立 cluster                 | 可共用 cluster               |
| --------------- | -------------------------------- | ---------------------------- |
| 業務關鍵性      | 核心交易（結帳、帳本）需隔離保護 | 內部工具、低關鍵性服務可共用 |
| 負載形狀        | 負載差異大、尖峰時段錯開         | 負載相近、可一起規劃容量     |
| 故障容忍        | 不能被別的業務拖垮               | 可接受共命運                 |
| schema 變更頻率 | 高頻 migration、不想牽制別人     | 低頻、變更少                 |
| 合規邊界        | 資料需獨立隔離（PCI / 個資分艙） | 無特殊合規隔離需求           |

`9.C23 Netflix` 是這個判斷的 case anchor：Netflix 把過往多套不同 *種類* 的關聯式 DB（PostgreSQL / MySQL / Oracle）整合到 Aurora、效能提升最高 75%、成本下降 28%；但整合的是「DB 種類 / 運維 surface」，*不是* 把所有資料塞進一個 cluster——Netflix 的微服務各自擁有自己的 Aurora cluster、彼此不共用。兩件事同時成立：減少 DB *技術種類* 降低運維知識負擔、同時維持 *per-service cluster* 隔離 blast radius。

> **Scope warning**：Netflix 的「+75% 效能 / -28% 成本」是跨多 workload 的最大改善幅度、非每個 workload 都 +75%（case 原文已標明）；且 Netflix 數據層遠不止 Aurora（還有 Cassandra / EVCache / Iceberg），Aurora 承擔的是需要 ACID 的 OLTP。引用時不可外推成「整合到 Aurora 就 +75%」。

## 兩種切分哲學的對照

大規模平台的 cluster 切分沒有單一正解，光譜兩端各有代表：

- **per-service 私有 store（Netflix 式）**：每個微服務一個 Aurora cluster、容量規劃變成「每個服務各自規劃」、跨服務 contention 變成 *網路議題* 而非 *DB lock 議題*
- **高度 consolidation**：少數大 cluster 承載多業務、運維實例少、但 blast radius 大

實務多落在中間：核心 / 高關鍵 / 合規敏感業務各自獨立 cluster，低關鍵性的內部服務可數個共用一個 cluster。判斷的是「這群業務能不能接受共命運」。

## Fleet 治理：切分後的一致性

切成多 cluster 後，運維 surface 從「一個 cluster」變成「N 個 cluster」。若沒有治理一致性，N 個 cluster 各自飄移會比一個大 cluster 更難維護。fleet 治理要把以下標準化：

- **配置一致**：engine 版本、parameter group、backup 策略、加密設定用 IaC 統一管理，避免逐個手調漂移
- **監控一致**：每個 cluster 同一套 CloudWatch alarm 基線（connection / replication lag / CPU / IOPS），不是只盯總量
- **升級協調**：major version 升級分批跨 fleet，不是一次全升（也不是放任各 cluster 版本散落）
- **成本歸屬**：按 cluster / 業務 tag 切成本，讓每個業務看見自己的 DB 成本

這層治理對應 [read-replica-scaling 的 fleet 治理段](/backend/01-database/vendors/aurora/read-replica-scaling/)——讀副本 fleet 與多 cluster fleet 共用「N 個實例如何維持治理一致」的方法。

## 失敗模式

production 常見的踩雷：

#### Case 1：共用大 cluster、報表 query 拖垮交易

分析 / 報表 workload 跟核心交易共用 cluster、一個重 query 佔滿資源、交易延遲飆高。修法：分析類 workload 切到獨立 cluster 或獨立 read replica；核心交易的 cluster 不混入不可控的分析查詢。

#### Case 2：cluster 切太細、運維 surface 爆炸

矯枉過正、每個小服務都獨立 cluster、結果幾十個 cluster 各自飄移、升級與監控成本失控。修法：低關鍵性、負載相近、可共命運的服務合併共用 cluster；切分以「blast radius 需求」為準，不是「每個服務都要」。

#### Case 3：切分了 cluster 但沒切分 fleet 治理

多 cluster 各自手調 parameter group、版本散落、backup 策略不一、出事才發現某個 cluster 設定漂移。修法：fleet 配置用 IaC 統一、監控基線一致、升級分批協調。

#### Case 4：跨 cluster 交易需求才發現切錯邊界

把本該強一致綁在一起的資料切到不同 cluster、結果需要跨 cluster 交易（Aurora 不提供跨 cluster transaction）、application 層自己補償、複雜又易錯。修法：cluster 邊界要對齊 transaction boundary——必須在同一個交易內一起成功失敗的資料，放同一 cluster（對應 [1.3 transaction 與一致性邊界](/backend/01-database/transaction-boundary/)）。這是切分前就要確認的邊界，切錯後重切成本高。

**Anti-recommendation**：團隊規模小、服務少、無合規隔離需求、且負載總量單一 cluster 撐得住 → 不要預先切成多 cluster；多 cluster 的治理成本只在「blast radius 隔離 / 合規分艙 / 負載差異大」真正需要時才值得。從少到多容易，從多合併回少要資料遷移。

## 容量與觀測

- 每個 cluster 獨立的 CloudWatch 基線：`DatabaseConnections` / `CPUUtilization` / `AuroraReplicaLag` / IOPS
- 跨 fleet 的成本 dashboard：按 cluster / 業務 tag 歸屬，看哪個業務的 DB 成本成長最快
- blast radius 演練：定期確認單一 cluster 故障不會外溢到其他業務（混沌測試）

> **Scope warning**：本文未引用 production case 的 cluster 數量 / 容量數字；切分維度與治理項屬通用平台工程 + Netflix consolidation 的架構訊號。

接回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[05 部署平台模組](/backend/05-deployment-platform/) 的 service decomposition。

## 邊界與整合

### cluster 邊界 vs 微服務邊界

多 cluster 切分常跟微服務拆分一起發生，但兩者不必一一對應。一個微服務可以擁有一個 cluster（Netflix 式私有 store），數個低關鍵微服務也可共用一個 cluster。判斷錨點是 transaction boundary 與 blast radius，不是「服務數 = cluster 數」。當切分壓力其實來自「不同資料模型」而非「隔離需求」，可能該考慮的是 polyglot persistence（OLTP 用 Aurora、KV 用 DynamoDB、analytics 用數倉），而非切更多 Aurora cluster。

### Sibling 與 cross-link

- [read-replica-scaling](/backend/01-database/vendors/aurora/read-replica-scaling/) — fleet 治理方法共用、讀副本 fleet 與多 cluster fleet 同源
- [cross-az-failover-rto](/backend/01-database/vendors/aurora/cross-az-failover-rto/) — 每個 cluster 的 failover 行為、blast radius 隔離後各自獨立
- [serverless-v2-scaling](/backend/01-database/vendors/aurora/serverless-v2-scaling/) — 低關鍵 / 間歇負載的 cluster 可用 serverless 降離峰成本
- [1.8 State Ownership 與 Query Boundary](/backend/01-database/state-ownership-query-boundary/) — cluster 邊界對齊狀態 ownership
- 替代路由：切分壓力來自資料模型差異 → polyglot persistence、回 [00 服務選型模組](/backend/00-service-selection/)
- 跟 [Netflix 9.C23](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 互引：DB 種類 consolidation + per-service cluster 隔離雙重成立的架構
