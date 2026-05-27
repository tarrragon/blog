---
title: "9.C39 DoorDash：Aurora Postgres 寫入瓶頸 → CockroachDB 多主寫入"
date: 2026-05-26
description: "DoorDash 從 Aurora Postgres 遷到 CockroachDB、解 1.6 M QPS 單主寫入瓶頸、外送平台爆量壓力下重做 OLTP 拓樸"
weight: 39
tags: ["backend", "performance", "capacity", "case-study", "db-oltp", "aws", "sustained-growth"]
---

這個案例的核心責任是說明「single-primary OLTP 撞到寫入天花板」如何用 distributed SQL 拆解。跟 [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 對比 — DraftKings 在 Aurora 上靠「業務切 200 個獨立 cluster」橫向擴展、DoorDash 是「保留 PostgreSQL wire 介面、但底層換成多主寫入的 CockroachDB」。兩條路徑都在解「Aurora 單主寫入容量上限」、走法不同。

## 觀察

DoorDash 從 Aurora Postgres 遷到 CockroachDB 的關鍵敘述（引自 [Why DoorDash migrated from Aurora Postgres to CockroachDB](https://www.cockroachlabs.com/blog/aurora-postgres-to-cockroachdb/) / [The New Stack 報導](https://thenewstack.io/how-doordash-migrated-from-aurora-postgres-to-cockroachdb/)）：

| 指標                | 數字                                                |
| ------------------- | --------------------------------------------------- |
| 2020-04-17 高峰 QPS | > 1.636 million QPS                                 |
| 事件結果            | multi-hour outage                                   |
| 事件背景            | 疫情封鎖、外送需求暴增                              |
| 遷移啟動            | 事件後幾週、先把 table 從主 cluster 拆出            |
| 第一階段移轉量      | 一個月內把 dozens of tables 拆到獨立 Aurora cluster |
| 第二階段            | 自動化工具把 Aurora Postgres → CockroachDB          |
| 後續結果            | 跑更多 cluster、incident alert volume 反而下降      |

服務組合：Aurora Postgres（遷移前主要 OLTP）、CockroachDB self-hosted、自製 table extraction tool、自製 lossless migration pipeline。

關鍵負載形狀：DoorDash 是 *規模化外送平台* — 訂單、Dasher 派遣、餐廳 menu、新業務（grocery / convenience）並存。寫入壓力來自訂單成立、status 變更、地圖位置更新等多種 hot write path。2020 疫情前流量已大、疫情後再翻倍、且高峰集中在週末晚餐 / 週日早午餐時段。

## 判讀

DoorDash 的工程選擇揭露三個 OLTP 寫入容量設計重點。

1. **Aurora 的「single-primary 寫入」是規模化的天花板**：Aurora 把 storage 跟 compute 分離、read replica 容易擴、*但寫入仍走唯一 primary*。1.636 M QPS 不是均勻分佈、是 hot table 集中寫爆。對應 [01.6 高併發資料存取](/backend/01-database/high-concurrency-access/) 的寫入容量規劃。CockroachDB 改成 Raft per range、每個 node 都能服務寫入、容量隨節點線性擴。
2. **Migration 工具自製是先決條件、不是 nice-to-have**：DoorDash 沒「一次性遷整套」、而是先寫工具把 table 從主 cluster 拆到獨立 Aurora cluster（紓壓）、再寫第二套工具把 Aurora → CockroachDB（換引擎）。兩階段都要 *lossless* + *可回退*。對應 [01.4 database migration playbook](/backend/01-database/database-migration-playbook/) 的「先建工具、再遷資料」原則。
3. **Cluster 數量增加、alert volume 卻下降**：直覺反過來、cluster 多 = 維運面變大、應該更多 alert。但每個 CockroachDB cluster 內建 Raft 自動容錯、單節點 fail 不會 page on-call、Aurora 時代的「primary failover alert」消失。對應 [04 可觀測性模組](/backend/04-observability/) 的「告警 surface 設計」與 [06.x reliability](/backend/06-reliability/) 的 graceful degradation。

需要警惕：1.636 M QPS 是 *主 cluster 峰值*、不是「DoorDash 全部寫入 QPS」。case 沒揭露遷移後單一 CockroachDB cluster 的峰值、只說「跑更多 cluster」。讀案例時不要把這個數字當成「CockroachDB 撐 1.6 M QPS」的證據、它是 *Aurora 在那個時間點撞牆的痛點*。

## 策略

可重用的工程做法：

1. **single-primary 撞牆前、先評估 multi-primary 選項**：Aurora / RDS Postgres 是 single-primary 為主、寫入量持續成長最終會撞天花板。轉折點不是 IOPS、是 *primary CPU + WAL flush rate*。對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 的瓶頸辨識。
2. **遷 OLTP 引擎要走「兩階段紓壓」**：先在原引擎內把 hot table 拆出（降低主 cluster 壓力、爭取時間）、再規劃換引擎（架構級改造）。直接「一次性換引擎」風險過高。對應 [01.4 database migration playbook](/backend/01-database/database-migration-playbook/)。
3. **PostgreSQL wire protocol 相容性是降低遷移成本的關鍵**：DoorDash 保留 PostgreSQL driver / ORM、應用層改動小。CockroachDB 不是 PostgreSQL fork、是 *protocol-level 相容*、實際 SQL 行為（serializable default、retry semantics、partial index）仍要驗證。對應 [CockroachDB vendor](/backend/01-database/vendors/cockroachdb/) 的 PostgreSQL 相容性 audit 段。

跨平台等效：

- AWS Aurora DSQL（2024）解同類「multi-primary 寫入」問題、但 AWS-only
- Spanner（GCP）同類設計、GCP-only
- TiDB（MySQL wire）解同類問題、亞洲生態深
- 自管 PostgreSQL + Citus（sharded extension）走 application 層 sharding、operation burden 較高

## 下一步路由

- 想理解 single-primary 寫入天花板訊號 → [9.5 瓶頸定位流程](/backend/09-performance-capacity/) + [01.6 高併發資料存取](/backend/01-database/high-concurrency-access/)
- 想規劃 PostgreSQL → CockroachDB migration → [01.4 database migration playbook](/backend/01-database/database-migration-playbook/) + [CockroachDB vendor](/backend/01-database/vendors/cockroachdb/)
- 對照其他 OLTP 規模化案例 → [9.C4 DraftKings Aurora](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)（按業務切 cluster）/ [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)（DB 種類整合）
- 想對照其他 distributed SQL 案例 → [9.C40 Netflix CockroachDB fleet](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) / [9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)
- 想理解全球一致性 OLTP 選型 → [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)
- 想拆 CockroachDB transaction retry 與 contention 模式 → [CockroachDB transaction retry pattern](/backend/01-database/vendors/cockroachdb/transaction-retry-pattern/)
- 想對比 Aurora DSQL / Spanner / CockroachDB 的選型 → [Aurora DSQL / Spanner / CockroachDB 決策樹](/backend/01-database/vendors/cockroachdb/aurora-dsql-spanner-decision-tree/)

## 引用源

- [Why DoorDash migrated from Aurora Postgres to CockroachDB](https://www.cockroachlabs.com/blog/aurora-postgres-to-cockroachdb/)
- [How DoorDash Migrated from Aurora Postgres to CockroachDB（The New Stack）](https://thenewstack.io/how-doordash-migrated-from-aurora-postgres-to-cockroachdb/)
- [How We Scaled New Verticals Fulfillment Backend with CockroachDB（DoorDash Engineering Blog）](https://careersatdoordash.com/blog/how-we-scaled-new-verticals-fulfillment-backend-with-cockroachdb/)
- [DoorDash Uses CockroachDB to Create Config Management Platform for Microservices（InfoQ）](https://www.infoq.com/news/2024/02/doordash-config-cockroachdb/)
