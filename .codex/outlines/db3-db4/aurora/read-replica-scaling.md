# Aurora Read Replica Scaling：15 replica 上限、lag profile 與 peak workload 容量規劃

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **Stage 3 校準（case-first）**：本 outline 是 Aurora fleet 治理軸的 SSoT — 邊界段「何時拆 cluster vs 加 replica」展開 fleet 拓樸 3 條 driver。另補 (1) DraftKings「+50% no sweat」= headroom 預留判讀（F3.4）、(2) FanDuel 雙 SLO 並行 frame（F3.12）、(3) 事件型容量分級表（F3.13）、(4) DraftKings 讀寫雙峰錯位作為讀寫分流 driver（F3.5）。

## 問題情境（Production pressure）

- 啟動壓力：FanDuel Super Bowl / DraftKings 比賽日、流量 5-10 倍尖峰、read query（用戶查 balance / 投注紀錄 / odds）打爆 primary、需要快速擴 read replica 但又怕 lag 把 stale read 推到 user-facing
- 讀者徵兆：「加 read replica 後 primary CPU 沒降、為什麼？」「Auto-scaling 加 replica 要幾分鐘、來不及接尖峰」「Reader endpoint round-robin 把 query 打到 lag 大的 replica、用戶看到舊 balance」
- 讀寫雙峰錯位 driver（9.C4 DraftKings 揭露）：比賽進行讀爆量（balance query）、payout event 寫爆量（ledger write）、兩個峰不在同一時刻。讀寫資源規劃要分開、不能用「峰值總 TPS」單一數字 — 這是 Aurora 讀寫分流的核心 driver、不只是「分散負載」（case「觀察」段最後一行）
- Case anchor：[9.C28 FanDuel dual-peak](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) Super Bowl 5-10x peak（注意：是 *betting 服務* 的 Aurora 擴容、不是 streaming）；[9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 200 cluster + Super Bowl +50% headroom 設計

## 核心機制（Vendor-specific mechanism）

- 15 replica 上限：每個 Aurora cluster 最多 15 個 read replica（跨 AZ）、跨 region replica 走 Global Database（不算 15）
- 共享 storage：replica 不靠 logical replication catch-up、直接從共享 storage 讀；lag 來源是 *compute node 的 buffer cache 同步*、不是 WAL replay
- Lag profile：typical 10-30ms（vs PostgreSQL streaming replication 秒級）、heavy write 期間可能 100ms+、不會像 PostgreSQL 那樣 unbounded — 9.C4 DraftKings 揭露「30 秒降到 10-30ms」的工程意義是「可預測」而非「快」、read-after-write 變得可規劃（case「判讀」段第 2 點）
- Reader endpoint：DNS-based round-robin、不感知 replica 健康狀態；application 想要 lag-aware routing 要自己實作或用 RDS Proxy
- Auto-scaling policy：CloudWatch metric（CPU / connection）trigger、replica creation 2-5 分鐘、無法用於秒級尖峰
- 對應 knowledge card：[replication-lag](/backend/knowledge-cards/replication-lag/)、[stale-read](/backend/knowledge-cards/stale-read/)、[read-replica](/backend/knowledge-cards/read-replica/)（若已建）
- 跟通用 read replica 差在哪：Aurora replica 不用 catch-up WAL、lag 上限可預測；vs PostgreSQL streaming replication lag 是 unbounded（取決於 primary 寫速度）

## 操作流程（Operations）

- 配置：`aws rds create-db-instance --db-cluster-identifier mycluster --db-instance-class db.r6g.4xlarge`、Auto-scaling policy 用 CloudWatch alarm
- Reader endpoint vs custom endpoint：custom endpoint 可以 group 特定 replica（例：分析 query 走獨立 endpoint、不影響 OLTP）
- 預配 vs auto-scale：peak workload 預知（Super Bowl）用預配（提前 1 小時加 replica）、unpredictable burst 才用 auto-scale
- 驗證點：`AuroraReplicaLag` < 100ms、reader endpoint CPU distribution 均勻、application stale-read error rate < 0.1%
- Rollback boundary：移除 replica 即時生效、無 data loss；但 reader endpoint DNS cache 仍可能短暫 routing 到已移除 replica

## 失敗模式（Failure modes）

- 加 replica 後 primary CPU 沒降：application 沒把 read query routing 到 reader endpoint、所有 query 仍打 primary；要 application 端拆 read / write data source（雙峰錯位是這層拆分的 driver）
- Reader endpoint round-robin 推 stale read：read-after-write 場景（用戶下注後立刻查 balance）打到 lagging replica、看到舊 balance、客訴；解法：sticky session 或 application 端做「下注後 N 秒走 primary」（DraftKings「可預測」frame 讓這個 N 秒可規劃）
- **Auto-scaling 來不及接秒級尖峰 → headroom 預留判讀（9.C4 DraftKings 揭露）**：
  - 機制限制：replica creation 2-5 分鐘、Super Bowl 開賽 30 秒尖峰已過
  - **case 自己反 marketing**：DraftKings「Super Bowl +50% no sweat」的工程意義是「*提前做好容量規劃*、不是『Aurora 神奇』」（case「判讀」段第 3 點 原文）
  - 真實做法：寫 workload 預期可能 +50%、整個 system headroom 預留至少 50%、加上 read replica 動態加減、才能讓 50% 增幅變成「不流汗」
  - 判讀層：peak workload 預知（賽事 / 促銷）用 *headroom 預留 + 提前預配*、不靠 auto-scale 接秒級；auto-scale 是 unpredictable burst 才用
- 15 replica 上限：超過 15 個 read replica 需求要拆 cluster — 詳見下方「何時拆 cluster vs 加 replica」邊界段
- Heavy write 期間 replica lag spike：bulk insert / DDL 期間 replica buffer cache invalidate、lag 可能 100-500ms、不該假設 typical 10-30ms 永遠成立
- **FanDuel 雙 SLO 並行 frame（9.C28 揭露）**：
  - case 明示「直播跟投注是兩種完全不同 SLO：直播容忍秒級延遲（用 CDN + ABR 串流）、投注必須毫秒級成交。兩個服務必須各自獨立擴容、各自獨立 SLO」（case「判讀」段第 1 點）
  - **scope warning 必明示**：5-10x 是 *betting 服務的 Aurora 擴容倍數*、不是 streaming 部分（streaming 走 CDN 不走 Aurora）— 避免把兩種 SLO 壓縮成「Aurora 撐 5-10x」單一數字
  - **scope warning（case 自承）**：AWS 案例 *沒有* 提具體 betting transaction TPS、concurrent streams、延遲分布。outline 不能寫「Aurora 在 betting 路徑撐 X TPS」這類細節

## 事件型容量分級表（9.C28 FanDuel 揭露）

事件型 scaling 不是一律 10x — case 揭露 *事件級別* 是容量分級單位：

| 事件級別              | 倍數  | 來源                          |
| --------------------- | ----- | ----------------------------- |
| 平日 baseline         | 1x    | FanDuel case「判讀」段第 3 點 |
| 季後賽 playoff        | 2-3x  | FanDuel case 揭露事件分級     |
| 季冠軍賽 championship | 4-5x  | FanDuel case 揭露事件分級     |
| Super Bowl            | 5-10x | FanDuel case 揭露事件分級     |

**case 自己警示（scope warning 必保留）**：

- 「5-10x」是 *峰值倍數*、不是 *peak 持續時間*。Super Bowl 的關鍵 30 分鐘可能 8-10x、其他 3 小時可能 3-5x（case「需要警惕」段）
- 分級 driver 是「同類事件中的最高倍率」、不是恆定數字 — outline 引用時要保留事件 tier 對應、不是一律「Super Bowl = 10x」單一閾值
- 跨業務 transfer 判讀：本表 *只代表體育博彩賽季 cycle*、不能直接套到 e-commerce flash-sale（6750x in seconds、跟事件 tier 結構不同 — 對照 Tixcraft frame 8）；事件型分級的關鍵是「峰值是已知的」、不是「峰值多大」

容量規劃做法：建立 event tier 體系、每 tier 對應不同 pre-scale 倍數跟 lead time（賽前 N 小時預配）；對應 [9.11 高峰事件準備](/backend/09-performance-capacity/) 的容量分級。

## 邊界與整合：fleet 治理 SSoT — 何時拆 cluster vs 加 replica

本段是 Aurora fleet 治理軸 SSoT — `storage-architecture.md` / `cross-az-failover-rto.md` / `global-database-multi-region.md` / `migrate-from-self-managed-pg-mysql.md` cross-link 不重複展開（依 module-outline Section G）。

**跨 case 合成 frame**：production scale 不是「單一巨型 cluster」而是 fleet of clusters、但 *driver 各異*：

| Driver                 | Case anchor                                                                                           | Fleet 規模  | 拆分判讀                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------ |
| Business sharding      | [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)         | 200 cluster | 業務本身可切分（每體育類別 / 每地理 / 每產品線各自 cluster）、blast radius 隔離      |
| Microservice ownership | [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)                 | 多 cluster  | 每微服務私有 store、不共用 cluster — 容量規劃分散到 service owner                    |
| 合規市場 boundary      | [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) | 7 cluster   | 受監管市場資料 *不能跨境複製*、每市場獨立 cluster — Global Database 在合規場景反指標 |

**何時拆 vs 加 replica 的判讀順序**：

1. > 15 replica 需求 → 拆 cluster（Aurora 硬上限）
2. Blast radius 隔離需求 → 拆 cluster（單 cluster 故障影響範圍太大）
3. 業務本身可切分（user shard / 產品線 / 地理）→ 拆 cluster（DraftKings 拓樸）
4. 微服務私有 store 拓樸 → 拆 cluster（Netflix 拓樸、跟服務生命週期綁定）
5. 合規禁止跨境複製 → 拆 cluster（Standard Chartered 拓樸、Global Database 反指標）
6. 以上都不成立 → 加 replica（最便宜的容量槓桿）

**容易誤判的邊界**：

- 9.C4 DraftKings 100 萬 ops/min ≈ 17K ops/sec 是 *200 cluster 加總*、平均每 cluster 約 80 ops/sec（case「需要警惕」段）— 不是「單一 cluster 撐 100 萬 ops」、案例對照不能擴寫成單 cluster 容量
- Fleet 治理本身有 ops surface area 成本（parameter group / backup / IAM / observability fan-out × N cluster），不是免費；driver 不夠強時不該拆

## 容量與觀測（Capacity & observability）

- CloudWatch metric：`AuroraReplicaLag`（per replica）、`AuroraReplicaLagMaximum`（cluster max）、`CPUUtilization` per replica、`DatabaseConnections` per replica
- Application metric：read query latency p99 per endpoint（writer vs reader）、stale-read error count
- 容量上限：15 replica / cluster、cross-region 走 Global Database
- 容量公式：read QPS / replica throughput = replica count、加 30% buffer for lag spike + headroom budget（依事件 tier）
- 回路徑：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 判斷 read-bound vs write-bound、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) peak workload 預配 vs auto-scale 決策

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[Aurora storage architecture](./storage-architecture.md)（共享 storage 為什麼能養 15 replica + 雙峰錯位 application 邊界）、[Aurora cross-AZ failover RTO](./cross-az-failover-rto.md)（replica 升 primary 流程）、[Aurora Global Database](./global-database-multi-region.md)（跨 region replica 配置 + 合規 anti-pattern）
- 1.x 章節互引：[1.4 Replication Lag](/backend/01-database/replication-lag/)（若已建）、[1.10 Read replica 設計](/backend/01-database/read-replica-design/)（若已建）
- Event-driven scaling 跨 vendor frame：對照 [DynamoDB on-demand vs provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) 5 種 scaling 模式（flash-sale spike / predictable peak / sustained growth / season cycle / surge baseline shift / dual-peak misalignment），本篇是 predictable peak + dual-peak misalignment 主場
- RDS Proxy 整合：lag-aware routing、connection pool 共享、Lambda 場景
- 何時不用本文：single replica + cross-AZ failover 已滿足、read traffic 不是 bottleneck

## 寫作前置 checklist

- [ ] case anchor 確認：FanDuel Super Bowl peak 預配時機、DraftKings 200 cluster 設計理由、DraftKings 雙峰錯位、headroom 預留判讀
- [ ] **Scope warning（必明示）**：
  - FanDuel 5-10x 限定 betting Aurora 擴容、不是 streaming（streaming 走 CDN）
  - FanDuel betting TPS / concurrent streams 未公開、不能 over-extrapolate
  - 事件分級「5-10x 是峰值倍數、不是持續時間」case 自帶警示要保留
  - DraftKings 100 萬 ops 是 200 cluster 加總、不是單 cluster 數字
- [ ] Fleet 治理 SSoT 標記：本篇是 SSoT、其他 outline cross-link 不展開
- [ ] knowledge card 雙引用：[replication-lag](/backend/knowledge-cards/replication-lag/) + [stale-read](/backend/knowledge-cards/stale-read/)
- [ ] sibling 對比：跟 PostgreSQL streaming replication 的 lag profile 對照
- [ ] 預估寫作長度：280-330 行（lag 機制 + auto-scaling 限制 + 雙 SLO + 事件分級表 + fleet 治理 SSoT）
- [ ] 寫作難度：中（兩個 case 提供 peak workload 訊號 + Netflix / Standard Chartered fleet 拓樸 driver）
