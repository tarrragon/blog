# CockroachDB HLC + Raft Consensus：為什麼 distributed SQL 不同於 single-primary

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：團隊評估 CockroachDB 替代 PostgreSQL streaming replication、看到「跨 region 強一致」但又被「每次寫經過 Raft」嚇到、不知道 latency 跟 throughput 預算要怎麼算
- 讀者徵兆：「Spanner 用 TrueTime 原子鐘、CockroachDB 沒硬體時鐘怎麼做 linearizability？」「Raft 每次寫要等 majority ack、不是比 PostgreSQL 慢？」「HLC clock skew 大會發生什麼？」
- Case anchor: primary [9.C39 DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/)（Aurora Postgres 1.636 M QPS single-primary 撞牆 → CockroachDB Raft per range 把寫入分散到多 node）、secondary [9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)（380+ cluster、60+ multi-region 規模證明 Raft 維運可承擔）；對照 [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 提供 distributed consensus 的另一條工程路徑（TrueTime vs HLC）

## 核心機制（Vendor-specific mechanism）

- HLC（Hybrid Logical Clock）：結合 physical clock + logical counter、不依賴 hardware atomic clock；vs Spanner TrueTime 用 GPS / atomic clock 提供 uncertainty bound
- Raft 三段：propose → replicate to majority → commit；每個 range 獨立 Raft group、leaseholder 是 Raft leader 的角色
- Range：CockroachDB 把 key space 切成 ~512 MB 的 range、每個 range 一個 Raft group；vs Spanner split、DynamoDB partition
- Leaseholder：每個 range 有一個 leaseholder（通常等於 Raft leader）、所有 read / write 經過 leaseholder
- Transaction 兩階段：先寫 intent（uncommitted）、commit 後 resolve intent；read 看到 intent 時要等 commit 或 abort
- 對應 knowledge card：[distributed-sql](/backend/knowledge-cards/distributed-sql/)、[quorum](/backend/knowledge-cards/quorum/)、[consensus](/backend/knowledge-cards/consensus/)（若已建）
- 跟 single-primary 差在哪：PostgreSQL primary write 1 個節點 ack 就 commit；CockroachDB write 要 majority（3 個 replica 至少 2 個）ack；latency p99 高 2-5 倍

## 操作流程（Operations）

- 配置：cluster 至少 3 個節點（Raft quorum minimum）、`--locality=region=us-east1,zone=us-east1-a` 標 locality
- HLC clock skew tolerance：default 500ms、`--max-offset` 配置；clock skew 超過 max-offset 節點自動 panic
- 驗證點：`SELECT * FROM crdb_internal.gossip_nodes` 看 clock offset、`SHOW CLUSTER SETTING server.clock.persist_upper_bound_interval`、Raft snapshot 健康（`crdb_internal.kv_store_status`）
- NTP 配置：production 必跑 NTP / chronyd、否則 clock skew 隨機 panic
- Rollback boundary：HLC 不可改後悔（時鐘前進不可回滾）、Raft commit 不可回滾、只能新交易補償

## 失敗模式（Failure modes）

- Clock skew panic：NTP 服務掛、節點時鐘漂移 > 500ms、節點自動 panic 保護一致性；vs PostgreSQL primary 不關心 time skew
- Raft majority lost：3 節點 cluster 失去 2 個、剩 1 個無法 commit、cluster 全 read-only；vs PostgreSQL primary 失效後 streaming replica 仍可 read
- Hot range：某個 range 寫流量集中、leaseholder 節點 CPU 飽和；解法：手動 split range 或 partition by region
- Transaction retry storm：serializable contention 嚴重時 application 端 retry loop、CPU 雪崩；要走 [transaction retry pattern](./transaction-retry-pattern.md)
- Range split / rebalance 影響 latency：自動 split 大 range、rebalance 期間 leaseholder 切換、p99 spike
- Case 對應根因：Spanner 用 TrueTime + 2-phase commit 解決同問題、CockroachDB 用 HLC + Raft、tradeoff 在「硬體成本 vs clock skew tolerance」

## 容量與觀測（Capacity & observability）

- CockroachDB Console metric：`Raft log queue size`、`Range count per node`、`Leaseholder count per node`、`HLC offset distribution`、`Transaction retry rate`
- 容量公式：write QPS / range / Raft latency = node count；考慮 replication factor（3-replica → write amplification 3x）
- p99 latency 預算：single-region 3-replica write p99 3-5ms；multi-region 跨洲 100-150ms（物理光速）
- 容量上限：單一 range 寫 throughput ~1000 QPS、整 cluster scale-out 加 range
- 回路徑：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 判斷 Raft-bound vs storage-bound、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) replication factor 跟 latency budget

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[CockroachDB survival goals](./survival-goals.md)（Raft replica 分佈策略）、[CockroachDB transaction retry pattern](./transaction-retry-pattern.md)（serializable 對 application 契約影響）、[CockroachDB locality-aware schema](./locality-aware-schema.md)（range placement 控制）
- 跟 Aurora 對照：Aurora storage-level quorum vs CockroachDB range-level Raft、不同 layer 的 consensus
- Aurora DSQL / Spanner 決策樹：見 [aurora-dsql-spanner-decision-tree](./aurora-dsql-spanner-decision-tree.md)
- 1.x 章節互引：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 上游、[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)（distributed transaction 邊界）
- 何時不用本文：single-region OLTP 用 PostgreSQL 已足夠、distributed consensus overhead 不划算

## 寫作前置 checklist

- [ ] case anchor 確認：等 C2 agent 補 CockroachDB direct case（候選：DoorDash / Comcast / Hard Rock Digital）；無 case 時用 Spanner case 對照 + 公開技術 blog（Cockroach Labs 官方）
- [ ] knowledge card 雙引用：[distributed-sql](/backend/knowledge-cards/distributed-sql/) + [quorum](/backend/knowledge-cards/quorum/)
- [ ] sibling 對比：跟 Spanner TrueTime + 2PC 對照、跟 Aurora storage quorum 對照
- [ ] 預估寫作長度：260-300 行（HLC + Raft + leaseholder 三層機制、技術密度高）
- [ ] 寫作難度：中高（公開 paper + 官方 docs 足、但要避免落入 spec 復述、需 Spanner case 對照撐 production 訊號）
