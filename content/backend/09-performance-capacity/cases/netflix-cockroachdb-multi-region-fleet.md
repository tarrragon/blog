---
title: "9.C40 Netflix：380+ CockroachDB cluster 的 multi-active 拓樸艦隊"
date: 2026-05-26
description: "Netflix 把 Cassandra 不夠用的 transactional workload 移到 CockroachDB、380+ cluster / 60+ 跨 region、含 Open Connect、studio cloud drive、gaming control plane"
weight: 40
tags: ["backend", "performance", "capacity", "case-study", "db-oltp", "aws", "low-latency-sustained"]
---

這個案例的核心責任是說明「Cassandra 撐不住 transactional 一致性」如何用 distributed SQL 補位。Netflix 不是把所有 DB 換成 CockroachDB、而是 *用 CockroachDB 補 Cassandra 缺的那塊*：需要 rich transaction + global secondary index + multi-active 寫入的場景。跟 [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 對照 — Aurora 整合的是 OLTP single-region workload、CockroachDB 解的是「跨 region 強一致 + 跨 cluster 高彈性」。

## 觀察

Netflix CockroachDB 艦隊的關鍵數字（引自 [Now Streaming: Why Netflix Runs a Fleet of 380+ CockroachDB Clusters](https://www.cockroachlabs.com/customers/netflix/) / [The history of databases at Netflix](https://www.cockroachlabs.com/blog/netflix-at-cockroachdb/)）：

| 指標                 | 數字                         |
| -------------------- | ---------------------------- |
| 總 cluster 數        | 380+                         |
| Production cluster   | 160+                         |
| Multi-region cluster | 60+                          |
| 最大單區 cluster     | 60 nodes / 26.5 TB           |
| Gaming 平台 cluster  | 48 nodes、跨 4 個 region     |
| 首個 prod cluster    | 2020 上線                    |
| Production cluster   | 2022 已達 100、近年擴至 160+ |
| 部署拓樸常態         | 多數 single-region、3 個 AZ  |

服務組合：CockroachDB self-managed（Netflix Database Platform Team 自運維）、跨 AWS region、與 Cassandra / EVCache / RDS 並存（polyglot persistence）。

關鍵 workload：

- **Studio Cloud Drive**：影視製作資產的 file-system 風格服務、需要強一致 metadata + 全球可寫
- **Open Connect 控制平面**：Netflix 自有 CDN、控制全球網路設備、需要跨 region 一致 control state
- **Spinnaker（持續交付平台）**：deployment workflow state 需要 transactional 一致
- **Maestro（ML / 資料 workflow orchestration）**：scheduling 與 state machine 不容許 eventual consistency
- **Gaming control plane**：metadata 跨 4 region、region failure 不能 downtime

## 判讀

Netflix CockroachDB 艦隊揭露三個「補 Cassandra 缺口」的 OLTP 工程選擇。

1. **Cassandra 不是 transactional 引擎、補位需求是工程現實**：Netflix 2014 全面採用 Cassandra 解 global replication、但 *lightweight transaction* 跟 unreliable secondary index 在 studio / control plane 等場景出問題。2019 評估後選 CockroachDB 是因為它同時滿足 multi-active topology、global consistent secondary index、global transaction、open source、SQL — 五個條件 Cassandra 在 transactional 場景下湊不齊。對應 [00 服務選型模組](/backend/00-service-selection/) 的 polyglot persistence 與 [01.5 transaction boundary](/backend/01-database/transaction-boundary/)。
2. **380+ cluster ≠ 「一個巨型 DB」**：Netflix 是 *artery of small DBs* 模型 — 每個微服務 / 應用配自己的 cluster、cluster sizing 從幾個 node 到 60 nodes 不等。容量規劃變成「每個 cluster 各自規劃」、不是「全公司一個容量曲線」。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/) 跟 [9.C23 Netflix Aurora](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 的「微服務私有 store」哲學。
3. **Multi-region 是「region failure 0 downtime」、不是「更快」**：Netflix 60+ multi-region cluster 主要動機是 region-level survival、不是降 latency（跨 region quorum 反而會增 latency）。Gaming cluster 48-node 跨 4 region 就是為了「region failover 不停服」、不是讓玩家延遲變低。對應 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) 的 latency vs availability 取捨。

需要警惕：

- case study 沒揭露單一 cluster QPS / latency 具體數字、只揭露 *艦隊規模* 跟 *最大 cluster 容量*。讀案例時不要把「380 cluster」直接換算成「Netflix CockroachDB QPS 上限」。
- Netflix 是 *self-managed*、不是 Cockroach Cloud — 需要專屬 Database Platform Team 養 380+ cluster。沒這量級團隊的組織直接 self-host 380 cluster 是 ops 自殺、Cockroach Cloud 才是合理路徑。

## 策略

可重用的工程做法：

1. **不要試圖一個 DB 撐全部**：Netflix 同時用 Cassandra（高吞吐 eventual）、CockroachDB（transactional + global）、Aurora（單區 ACID）、EVCache（cache）。每種 DB 對應不同 workload 類型、不混用。對應 [00 服務選型模組](/backend/00-service-selection/) 的 polyglot persistence。
2. **每個 cluster 對應一個 application boundary**：避免 multi-tenant 大 cluster、改用「per-app cluster」— 容量規劃顆粒對齊 application、爆掉時 blast radius 限縮在單一 app。對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 的 blast radius 設計。
3. **Multi-region 用於 survival、不是 latency 優化**：跨 region quorum 物理上必然增 latency。把 multi-region 動機釐清成 *region failure 容忍*、不要混淆「跨 region = 更快」。對應 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 的 survival goal vs latency budget 取捨。
4. **Self-managed 規模化需要專屬平台團隊**：Netflix 有 Database Platform Team 養 380+ cluster — 包含 backup、upgrade、incident response、capacity review。沒這量級團隊就走 managed service。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/) 的人力成本權衡。

跨平台等效：

- Spanner（GCP）解同類「global transaction + secondary index」、GCP-only
- DynamoDB Global Tables 走 eventual consistency、不是 Netflix 想要的 strong consistency
- Yugabyte / TiDB 是 distributed SQL 對等候選、生態深度與 PostgreSQL wire 相容度有差

## 下一步路由

- 想理解 polyglot persistence 選型 → [00 服務選型模組](/backend/00-service-selection/) + [9.C23 Netflix Aurora](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)
- 想規劃 multi-region survival goal → [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) + [CockroachDB vendor](/backend/01-database/vendors/cockroachdb/)
- 對照其他 distributed SQL 案例 → [9.C39 DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/) / [9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/) / [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)
- 想理解 transaction vs eventual consistency 邊界 → [01.5 transaction boundary](/backend/01-database/transaction-boundary/)

## 引用源

- [Now Streaming: Why Netflix Runs a Fleet of 380+ CockroachDB Clusters（PDF）](https://assets.ctfassets.net/00voh0j35590/7qBPsA0FKKTuAK4JhK27uu/1b30b2015f32878874bd0873a2a54361/CockroachLabs-NETFLIX-Case-Study.pdf)
- [Now Streaming: Why Netflix Runs a Fleet of 380+ CockroachDB Clusters（cockroachlabs.com Netflix customer page）](https://www.cockroachlabs.com/customers/netflix/)
- [The history of databases at Netflix: From Cassandra to CockroachDB](https://www.cockroachlabs.com/blog/netflix-at-cockroachdb/)
- [A Netflix RoachFest24 Original: The Case for Multi-Region Clusters](https://www.cockroachlabs.com/blog/netflix-dbaas-roachfest24-recap/)
- [How Netflix engineers choose their tech stack](https://www.cockroachlabs.com/blog/persistence-as-a-service-at-netflix/)
