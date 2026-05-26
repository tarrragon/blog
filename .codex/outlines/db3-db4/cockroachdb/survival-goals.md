# CockroachDB Survival Goals：zone-level vs region-level 配置與 RTO/RPO 取捨

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：multi-region CockroachDB cluster 上線、要決定「一個 region 整個掛掉、cluster 還要不要繼續 serve write」、不同答案對應完全不同 latency / cost / replica 數量
- 讀者徵兆：「`SURVIVE ZONE FAILURE` 跟 `SURVIVE REGION FAILURE` 差在哪？」「為什麼 region survival 寫入 latency 是 zone survival 的 3 倍？」「Default 配置是什麼、上線前要不要改？」
- Case anchor: primary [9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)（AWS Outposts + US-East-1 跨 8 州單一邏輯 cluster、Wire Act 合規逼出 region survival 配置、~100 nodes 高峰自動容錯）、secondary [9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/)（60+ multi-region cluster 規模運維 survival goal）；對照 [9.C14 Standard Chartered Aurora banking](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 受監管金融、用 Aurora 多 cluster 達成同類 RTO 目標的另一條路徑

## 核心機制（Vendor-specific mechanism）

- 兩種 survival goal：
  - `SURVIVE ZONE FAILURE`（default）：失去 1 AZ 仍能寫；replica 跨 AZ 但可能集中在同 region
  - `SURVIVE REGION FAILURE`：失去 1 region 仍能寫；replica 強制跨 region、需要至少 3 region
- Survival goal 是 *database-level* 或 *table-level* 配置、不是 cluster-level
- 配置語法：`ALTER DATABASE mydb SURVIVE REGION FAILURE`
- Replica placement：survival goal 影響 Raft 自動把 replica 分散到哪些 region / zone
- Voting replica vs non-voting replica：region survival 模式下、voting replica 強制跨 region、non-voting 可用於 read-only locality
- 對應 knowledge card：[quorum](/backend/knowledge-cards/quorum/)、[rto](/backend/knowledge-cards/rto/)、[rpo](/backend/knowledge-cards/rpo/)、[blast-radius](/backend/knowledge-cards/blast-radius/)
- 跟通用 HA 差在哪：CockroachDB survival goal 是宣告式（不用手動配 replica placement）、Raft 自動執行

## 操作流程（Operations）

- 配置：`ALTER DATABASE mydb SURVIVE REGION FAILURE`、需要 cluster 至少 3 個 region、每 region 至少 3 個節點
- 驗證點：`SHOW SURVIVAL GOAL FROM DATABASE mydb`、`crdb_internal.ranges` 確認 replica 分佈、Raft replication factor `SHOW ZONE CONFIGURATION FOR DATABASE mydb`
- 升級流程：zone survival → region survival 是非破壞性配置改變、Raft 自動 rebalance replica；可能短期增加 cross-region traffic
- 監控 rebalance：`SELECT * FROM crdb_internal.kv_store_status` 看 range 數量變化、CockroachDB Console 看 rebalance queue
- Rollback boundary：survival goal 改變可即時降級（region → zone）、replica 自動 rebalance；無不可逆動作

## 失敗模式（Failure modes）

- Default zone survival 期待 region survival：上線後一個 region 掛、cluster 變 read-only、客訴；要在 production 前明確選 survival goal
- Region survival 但只配 2 個 region：Raft majority 需要 3 個獨立 fault domain、2 region 配置實際是 zone survival
- Write latency 暴漲：zone → region survival 寫 latency 從 5ms 跳到 50ms+（跨 region quorum）、未量測就上線
- Cross-region cost 暴漲：region survival 強制 voting replica 跨 region、每次 write 跨 region traffic × 3、月費可能 2-3 倍
- Locality 跟 survival goal 衝突：用戶資料 partition by region 想留 local、但 survival goal 要跨 region、replica 仍跑遠端
- 合規邊界 violation：受監管市場資料*不能跨境*、region survival 強制跨 region 違反合規；需用 zone survival + 跨市場獨立 cluster
- Case 對應根因：Standard Chartered 受監管市場為什麼*不能*用 region survival、必須用每市場獨立 cluster + zone survival

## 容量與觀測（Capacity & observability）

- CockroachDB Console metric：`Raft replicas per node`、`Range count by survival mode`、`Cross-region write latency`、`Rebalance queue size`
- 容量公式：region survival 需要 region count × 3 nodes（minimum）、replica factor 預設 3、storage 用量 × replica factor
- p99 latency 預算：zone survival single-region 5-10ms、region survival 跨 region 50-150ms（取決於地理距離）
- Cost signal：cross-region data transfer 是 region survival 的隱藏成本、CockroachDB Console `Network traffic by direction`
- 回路徑：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) survival goal 對 replica count / cost 影響、[8.x DR playbook](/backend/08-incident-response/) region failure 演練

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[CockroachDB HLC + Raft consensus](./hlc-raft-consensus.md)（Raft 機制是 survival goal 的基礎）、[CockroachDB locality-aware schema](./locality-aware-schema.md)（locality + survival goal 一起決定 replica placement）、[CockroachDB transaction retry pattern](./transaction-retry-pattern.md)（cross-region latency 對 retry 影響）
- 跟 Aurora 對照：Aurora cross-AZ failover（zone-level survival）、Aurora Global Database（region-level 但 async）、CockroachDB region survival 是 sync
- Aurora DSQL / Spanner 決策樹：見 [aurora-dsql-spanner-decision-tree](./aurora-dsql-spanner-decision-tree.md)
- 1.x 章節互引：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)、[1.13 DR / 跨 region 設計](/backend/01-database/disaster-recovery/)（若已建）
- 何時不用 region survival：single-region 已滿足、預算敏感、合規禁止跨境

## 寫作前置 checklist

- [ ] case anchor 確認：等 C2 agent 補；無 direct case 時 Standard Chartered 對照作 anti-recommendation（為什麼*不用* region survival）
- [ ] knowledge card 雙引用：[quorum](/backend/knowledge-cards/quorum/) + [rto](/backend/knowledge-cards/rto/) + [blast-radius](/backend/knowledge-cards/blast-radius/)
- [ ] sibling 對比：跟 Aurora Global Database async vs CockroachDB region survival sync 對照
- [ ] 預估寫作長度：220-260 行（兩種 survival goal + replica placement + latency / cost tradeoff）
- [ ] 寫作難度：中（CockroachDB docs 充分、anti-recommendation 由 Standard Chartered case 對照支撐）
