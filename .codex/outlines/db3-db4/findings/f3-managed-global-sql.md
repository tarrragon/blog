# F3：Aurora + Spanner Case Audit Findings

## Audit 範圍跟邊際遞減判讀

- **讀的 case 數**：5（Aurora 4 + Spanner 1）
- **case 類型分類**：
  - Rich case：9.C4 DraftKings、9.C10 Spanner、9.C23 Netflix（含具體數字 / 設計細節 / 引用源）
  - Medium case：9.C28 FanDuel（結構化、但 betting transaction TPS / concurrent streams 數字被 case 自己標明為「未提供」、明示 derive 邊界）
  - Skeleton-leaning rich：9.C14 Standard Chartered（10x / 4000 TPS / 7 市場數字明確、但其他細節（PostgreSQL 還是 MySQL、加密 algorithm）case 自己用「相關 case study」匿名標明、屬 rich 中保守的一支）
- **邊際遞減訊號**：5 case 共抽出 13 個 unique finding、純新議題比例 ~80%（每 case 1.5-3.5 unique）。重複 frame：「Aurora storage / compute 分離」在 9.C4 / 9.C23 / 9.C28 都浮現、「事件型峰值規劃」在 9.C4 / 9.C28 都浮現、「合規 / 受監管邊界」在 9.C14 / 9.C28 都浮現 — 重複比例 ~30%、未觸發 stop。Spanner 只 1 case 但 finding 密度高（4 個純新議題、含 line-rate scaling / commit wait / granular sizing / dogfood 邊界）、跟 Aurora 4 case 形成完整 managed vs global SQL 對比。
- **停止 audit 條件**：本批 5 case 為 DB4 vendor article scope 上限（Aurora 4 個 + Spanner 唯一公開 dogfood case）、無更多 Aurora / Spanner case 待讀；audit 已 saturate。

## Findings 列表

### Finding F3.1：200 個獨立 Aurora cluster = sharding by business、不是 1 個 cluster + 200 schema

- **來源**：9.C4 DraftKings「判讀」段第 1 點 + 「需要警惕」段
- **Case 類型**：Rich
- **揭露內容**：DraftKings 100 萬 ops/min ≈ 17K ops/sec 是「200 cluster 加總」、平均每 cluster 約 80 ops/sec。case 明示「不是一個巨型 cluster 撐全部、而是按業務切 200 個 cluster」、把單機極限改成 shard 極限、blast radius 隔離。
- **Outline mapping**：
  - Aurora 已覆蓋於：`read-replica-scaling.md` 失敗模式「> 15 replica 需求要拆 cluster（DraftKings 200 個獨立 cluster 模式）、不是堆 replica」、`migrate-from-self-managed-pg-mysql.md` 案例對照段「200 個獨立 cluster、按業務切分（不是一個大 cluster + 200 schema）」
  - 該補但漏了：`storage-architecture.md` 在 Netflix 案例展開 +75% 時、應同時 reference DraftKings 200 cluster 拓樸 — storage 設計本身不解 cluster 數量議題、需要 explicit boundary「Aurora 解 single-cluster scaling、不解 fleet-level cluster 邊界決策」
  - Outline 缺口：缺一張「Aurora cluster fleet management」邊界討論（200 cluster 怎麼治理 — parameter group / backup retention / IAM / observability fan-out）；本批 5 outline 都當 single-cluster 視角、漏掉 fleet 維度
- **High-impact 等級**：High（揭露 managed SQL scaling 的 fleet 軸、跟 storage / compute 分離互補）

### Finding F3.2：Aurora 寫延遲 6ms 是 quorum + cross-AZ 的硬底線、不是 storage 設計就能再壓低

- **來源**：9.C4 DraftKings「觀察」段表格（讀 < 1ms、寫 6ms、replication lag 30s → 10-30ms）
- **Case 類型**：Rich
- **揭露內容**：DraftKings 在 production load 下、讀 < 1ms、寫 6ms — 寫延遲是「quorum 4-of-6 + 跨 AZ network round-trip」的物理下界、不是 storage 設計神奇。讀寫差距 6x 是 OLTP 容量規劃槓桿的 baseline。
- **Outline mapping**：
  - Aurora 已覆蓋於：`storage-architecture.md` 失敗模式「誤以為 Aurora 寫入比 PostgreSQL primary 一定更快：寫小 row、單筆 commit、跨 AZ network round-trip 仍是 3-5ms、不會比 local SSD primary 快」、`read-replica-scaling.md` 隱含於「6ms 寫 vs <1ms 讀」
  - 該補但漏了：`storage-architecture.md` 應在「容量與觀測」段加入 DraftKings 6ms / <1ms 作為 production reference number、而不只是用「3-5ms / typical」籠統說法。case 給的是 production-grade 數字、不是 marketing。
  - Outline 缺口：無
- **High-impact 等級**：Medium

### Finding F3.3：Replication lag 30 秒 → 10-30ms 的工程意義是「可預測」而非「快」

- **來源**：9.C4 DraftKings「判讀」段第 2 點
- **Case 類型**：Rich
- **揭露內容**：case 明示「這個改善不只是『快』、而是讓 read-after-write 變得可預測」。對應 transaction boundary 設計：傳統 streaming replication lag unbounded（取決於 primary 寫速度）、Aurora 共享 storage 讓 lag 有可預期上限。
- **Outline mapping**：
  - Aurora 已覆蓋於：`storage-architecture.md` 失敗模式「Replication lag 誤解：read replica lag 10-30ms 是 *typical*」、`read-replica-scaling.md` 核心機制「typical 10-30ms（vs PostgreSQL streaming replication 秒級）、不會像 PostgreSQL 那樣 unbounded」
  - 該補但漏了：兩篇都寫到 lag 數字、但漏了 case 強調的「可預測性」frame — read-after-write 是不是可規劃、是 application 端決定 sticky session / retry 策略的 key。`read-replica-scaling.md` 的失敗模式「Reader endpoint round-robin 推 stale read」應 explicit cite DraftKings case 的「可預測」frame、不是只說 lag 數字。
  - Outline 缺口：無
- **High-impact 等級**：Medium

### Finding F3.4：Super Bowl +50% 「no sweat」的工程意義是 headroom 預留、不是 Aurora 神奇

- **來源**：9.C4 DraftKings「判讀」段第 3 點
- **Case 類型**：Rich
- **揭露內容**：case explicit 寫「這句話的工程意義是 *提前做好容量規劃*、不是『Aurora 神奇』。寫 workload 預期可能 +50%、整個 system headroom 預留至少 50%、加上 read replica 動態加減、才能讓 50% 增幅變成『不流汗』」。這是 case 本身的反 marketing 判讀、不是讀者推論。
- **Outline mapping**：
  - Aurora 已覆蓋於：`read-replica-scaling.md` 操作流程「預配 vs auto-scale：peak workload 預知（Super Bowl）用預配（提前 1 小時加 replica）、unpredictable burst 才用 auto-scale」
  - 該補但漏了：`read-replica-scaling.md` 的失敗模式「Auto-scaling 來不及接秒級尖峰：replica creation 2-5 分鐘、Super Bowl 開賽 30 秒尖峰已過」應 explicit reference case 的 +50% no-sweat 判讀層、不只用 FanDuel 的 5-10x 例。case 的「no sweat = 提前 headroom」是 capacity planning 章節的核心 anchor、不只是 replica auto-scale 議題。
  - Outline 缺口：本批 outline 沒有 capacity planning principle 段、`storage-architecture.md` 跟 `read-replica-scaling.md` 都假設讀者已懂 headroom；缺一段「Aurora capacity planning 的 anchor 是 headroom budget、Aurora 服務只是讓 headroom 利用更平滑」的明示
- **High-impact 等級**：High（揭露 managed SQL vs vendor marketing 的判讀層）

### Finding F3.5：讀寫負載「雙峰錯位」— 比賽進行讀爆量、payout 時寫爆量

- **來源**：9.C4 DraftKings「觀察」段最後一行（「write workloads spike up significantly around payout events, but opening the app during the game also activates a lot of balance queries」）
- **Case 類型**：Rich
- **揭露內容**：DraftKings 的負載形狀不是單峰、是讀寫雙峰錯位。比賽進行時 balance query 爆量（讀）、payout 時 ledger write 爆量（寫）。讀寫資源規劃要分開、不能用「峰值總 TPS」單一數字規劃。
- **Outline mapping**：
  - Aurora 已覆蓋於：`read-replica-scaling.md` 問題情境「FanDuel Super Bowl / DraftKings 比賽日、流量 5-10 倍尖峰、read query（用戶查 balance / 投注紀錄 / odds）打爆 primary」— 但只用「read 爆量」frame、漏掉「讀寫雙峰錯位」
  - 該補但漏了：`read-replica-scaling.md` 應 explicit 引用 DraftKings 雙峰錯位、論證「讀寫資源分開規劃」是 Aurora 讀寫分流的核心 driver、不只是「分散負載」
  - Outline 缺口：`storage-architecture.md` 應在「容量與觀測」段加入「OLTP 工作負載形狀」討論 — case 揭露的雙峰錯位是 *application-level pattern*、storage layer 本身不解、要靠 application 拆讀寫 datasource。outline 漏這層 application 邊界
- **High-impact 等級**：High（揭露 OLTP workload shape 軸、跟 Aurora 讀寫分流綁定）

### Finding F3.6：受監管市場資料駐留 = 7 個獨立 cluster、不是 Global Database

- **來源**：9.C14 Standard Chartered「判讀」段第 1 點 + 「策略」段第 1 點
- **Case 類型**：Rich
- **揭露內容**：case explicit 寫「7 個受監管市場代表 7 個獨立 cluster（資料不能跨境）、容量規劃變成『7 個獨立規劃 × 各自合規門檻』」。這是 case 揭露的合規 anti-pattern — 不是「Aurora Global Database 不好」、是「合規禁止跨境複製、Global Database 違反合規」。
- **Outline mapping**：
  - Aurora 已覆蓋於：`global-database-multi-region.md` 失敗模式「合規邊界誤用 Global Database：Standard Chartered 案例顯示受監管市場資料*不能跨境複製*、Global Database 違反合規、要改用每市場獨立 cluster」、`cross-az-failover-rto.md` 「Standard Chartered 用每市場獨立 cluster 而非 Global Database 跨 region failover」
  - 該補但漏了：兩篇都已 cite、覆蓋良好。但 `migrate-from-self-managed-pg-mysql.md` 的 Driver 段「No-go condition」漏掉「合規禁止跨境複製」這條 — 應加入、避免讀者誤以為 Aurora 一定有 Global Database 選項
  - Outline 缺口：無
- **High-impact 等級**：Medium

### Finding F3.7：「韌性 + 性能」並列不是 trade-off — Aurora 多 AZ storage 同時提供

- **來源**：9.C14 Standard Chartered「判讀」段第 2 點
- **Case 類型**：Rich
- **揭露內容**：case 明示「傳統工程文化常把可靠性跟性能視為對立、銀行業務要求兩者同時達標。Aurora 的多 AZ storage + replica 同時提供性能（讀分流）跟韌性（故障切換）、達成 *韌性即性能* 的目標」。這是 Aurora storage 設計的核心價值主張、case 直接揭露。
- **Outline mapping**：
  - Aurora 已覆蓋於：`storage-architecture.md` 核心機制「6-way replication：每個 storage segment 跨 3 AZ × 2 node」、`cross-az-failover-rto.md` 「不需要 data sync：storage layer 跨 AZ 共享、replica 升 primary 不需要 catch-up」
  - 該補但漏了：兩篇都隱含、但都沒 explicit 點出 case 強調的「韌性 + 性能不是 trade-off」frame。`storage-architecture.md` 應在問題情境 / 核心機制段加一句「Aurora 把 HA 從 application-level（Patroni promotion + WAL catch-up）下推到 storage-level、讓韌性投資自動 amortize 成 read 性能」
  - Outline 缺口：無
- **High-impact 等級**：Medium

### Finding F3.8：受監管遷移合規 lead time（3-12 月 / 市場）是時程主項、不是技術遷移時間

- **來源**：9.C14 Standard Chartered「判讀」段第 3 點 + 「策略」段第 3 點
- **Case 類型**：Rich
- **揭露內容**：case explicit 寫「每個受監管市場的審查可能 3-12 個月、合計遷移時程是『市場數 × 平均審查月份』、不是『技術遷移月份』」。受監管 migration 的關鍵時程是合規審查 lead time、不是 DMS / dual-read window。
- **Outline mapping**：
  - Aurora 已覆蓋於：無
  - 該補但漏了：`migrate-from-self-managed-pg-mysql.md` 的 Phase plan 假設 2-8 週 data migration + < 1 小時 cutover、完全沒含合規審查 lead time。對受監管讀者誤導 — 銀行 / 保險 / 醫療讀者照本 playbook 走會嚴重低估時程
  - Outline 缺口：`migrate-from-self-managed-pg-mysql.md` 應加一段「合規驅動遷移的時程模型」 — 或在 Driver 段明示「本 playbook 假設 non-regulated workload；regulated 場景見 Standard Chartered 補充」、否則案例對照段 cite Netflix 不 cite Standard Chartered 是 case 不對稱
- **High-impact 等級**：High（揭露 managed SQL migration 的合規軸、本 playbook outline 顯著缺口）

### Finding F3.9：Netflix +75% 效能根因是 storage / compute 分離 + 不再 flush dirty page、不是「分散式儲存籠統說法」

- **來源**：9.C23 Netflix「判讀」段第 2 點 + storage-architecture.md 失敗模式段已點明
- **Case 類型**：Rich
- **揭露內容**：case 明示「Aurora 把 storage 跟 compute 分離、storage 用分散式 log-based 設計、replication 在 storage 層處理、不在 compute 層 — 這讓 read replica 不會受 master 寫入壓力影響、性能曲線比傳統 RDB 平滑」。+75% 是 *跨多 workload 最大值*、不是單 workload。
- **Outline mapping**：
  - Aurora 已覆蓋於：`storage-architecture.md` 問題情境 case anchor + 失敗模式「Case 對應根因：[9.C23 Netflix] +75% 效能根因是 *compute 不再 flush dirty page*、不是 marketing 的『分散式儲存』籠統說法」、`migrate-from-self-managed-pg-mysql.md` 案例對照段
  - 該補但漏了：`storage-architecture.md` 已正確識別、但「+75%」的「跨多 workload 最大值」derive 層應 explicit 標明、避免讀者誤把 75% 套到單一 workload — 屬 rich case 的 fact vs derive 分層紀律
  - Outline 缺口：無
- **High-impact 等級**：Medium

### Finding F3.10：DB 種類整合是規模化必要工程 — Netflix 從多套 RDB 統一到 Aurora 是 ops surface area 議題

- **來源**：9.C23 Netflix「判讀」段第 1 點 + 「策略」段第 1 點 + 「需要警惕」段
- **Case 類型**：Rich
- **揭露內容**：case 揭露 Netflix consolidation driver 不是「Aurora 比 PostgreSQL 快」、而是「PostgreSQL / MySQL / Oracle 各自需要不同 DBA / backup / monitoring」、ops surface area 太大。同時 case 警示：Netflix 仍用 Cassandra / EVCache / Iceberg — Aurora 只覆蓋「需要 ACID 的 OLTP」、不是 all-purpose store。
- **Outline mapping**：
  - Aurora 已覆蓋於：`migrate-from-self-managed-pg-mysql.md` Driver 段「主要 driver：團隊規模成長、DBA bandwidth 飽和、backup / failover / patch 操作負擔超過產品價值」、案例對照段「驗證 operational consolidation 的價值」
  - 該補但漏了：`migrate-from-self-managed-pg-mysql.md` 的 Driver 段引 Netflix 案例時、應同時引 case 警示「Aurora 不是 all-purpose store、Netflix 仍用 Cassandra / EVCache」 — 避免讀者誤以為 Aurora 可以替所有 store
  - Outline 缺口：無
- **High-impact 等級**：Medium

### Finding F3.11：Aurora 微服務私有 store 模式 — 每微服務各自 cluster、容量規劃複雜度分散

- **來源**：9.C23 Netflix「判讀」段第 3 點
- **Case 類型**：Rich
- **揭露內容**：case 揭露「Netflix 微服務各自有自己的 Aurora cluster、不共用 — 跟 monolith『一個大 DB 撐全部』相反。這層架構讓『DB 容量規劃』變成『每個微服務的容量規劃』、複雜度分散」。
- **Outline mapping**：
  - Aurora 已覆蓋於：間接於 DraftKings 200 cluster 的 fleet 視角（F3.1）
  - 該補但漏了：本批 outline 沒有 explicit「微服務私有 store vs shared store」討論軸。Netflix 跟 DraftKings 都用 fleet of cluster、但 driver 不同（Netflix 是 microservice ownership、DraftKings 是 business sharding）— 揭露兩種 fleet 拓樸 driver、應在 storage-architecture / read-replica-scaling 的「何時拆 cluster」段並列
  - Outline 缺口：`read-replica-scaling.md` 邊界段「何時拆 cluster vs 加 replica」應 explicit 加「微服務拆分」這條 driver、不只用「> 15 replica / blast radius / 合規」三條
- **High-impact 等級**：High（揭露 Aurora fleet 拓樸的兩條 driver 路徑）

### Finding F3.12：FanDuel 雙峰是「兩種 SLO 並行」、不是「一個服務 5-10x」

- **來源**：9.C28 FanDuel「判讀」段第 1 點 + 「策略」段第 1 點
- **Case 類型**：Medium（case 自己標明 betting TPS / concurrent streams 數字未公開）
- **揭露內容**：case explicit 寫「直播跟投注是兩種完全不同 SLO：直播容忍秒級延遲（用 CDN + ABR 串流）、投注必須毫秒級成交。兩個服務必須各自獨立擴容、各自獨立 SLO」。5-10x 是兩個工作負載各自的擴容倍數、不是同一服務的 5-10x。
- **Outline mapping**：
  - Aurora 已覆蓋於：`read-replica-scaling.md` 問題情境「FanDuel Super Bowl / DraftKings 比賽日、流量 5-10 倍尖峰」— 但用了 5-10x 的數字、漏掉「兩個服務並行」frame
  - 該補但漏了：`read-replica-scaling.md` 應 explicit 標明「FanDuel 5-10x 是 betting 服務的 Aurora 擴容倍數、不是 streaming 部分（streaming 走 CDN 不走 Aurora）」 — 避免把兩種 SLO 壓縮成「Aurora 撐 5-10x」單一數字
  - Outline 缺口：無（但這是 medium case 引用紀律的關鍵點 — case 沒給具體 betting TPS、outline 不能擴寫成「Aurora 在 betting 路徑撐 X TPS」）
- **High-impact 等級**：Medium

### Finding F3.13：事件型容量分級 — playoff / championship / Super Bowl 各自倍數、不是一律 10x

- **來源**：9.C28 FanDuel「判讀」段第 3 點 + 「需要警惕」段
- **Case 類型**：Medium
- **揭露內容**：case 明示「平日 baseline → 季後賽 2-3x → 季冠軍賽 4-5x → Super Bowl 5-10x。容量規劃要按事件級別分段、不是一律 10x。」+ case 自己警示「『5-10x』是 *峰值倍數*、不是 *peak 持續時間*。Super Bowl 的關鍵 30 分鐘可能 8-10x、其他 3 小時可能 3-5x」。
- **Outline mapping**：
  - Aurora 已覆蓋於：`read-replica-scaling.md` 操作流程「peak workload 預知（Super Bowl）用預配」— 但只說「Super Bowl」、漏掉事件分級
  - 該補但漏了：`read-replica-scaling.md` 應加入事件分級表（playoff / championship / Super Bowl 倍數）、或在容量公式段 explicit 引用 case「按事件級別分段」
  - Outline 缺口：本批 outline 缺一段「Aurora event-driven scaling 的容量分級」討論、目前都當「Super Bowl = 5-10x」單一數字
- **High-impact 等級**：Medium

### Finding F3.14：Spanner 線性擴展是 OLTP 最高設計目標 — coordinator 是傳統 OLTP bottleneck

- **來源**：9.C10 Spanner「判讀」段第 1 點
- **Case 類型**：Rich
- **揭露內容**：case 明示「『2 nodes → 45K reads/sec、4 nodes → 90K reads/sec』這個 linear scaling 在傳統 OLTP（PostgreSQL、MySQL）做不到 — 因為 *跨節點交易* 需要 coordinator、coordinator 是 bottleneck。Spanner 用 Paxos + TrueTime 把 coordinator 變成『拓樸感知的多 leader』、才達成線性」。
- **Outline mapping**：
  - Spanner 已覆蓋於：`truetime-api-depth.md` 核心機制（commit wait + Paxos）、`consistency-models-comparison.md` 「Spanner 的 external consistency：用 TrueTime + commit wait 實作」
  - 該補但漏了：`truetime-api-depth.md` 應 explicit 標明「TrueTime 的目的是消滅 single coordinator bottleneck、把 OLTP 從 1x node = 1x throughput 推到 linear scaling」 — 目前 outline focus 在 commit wait 機制本身、漏掉「為什麼這套機制存在」的商業邏輯先行
  - Outline 缺口：`consistency-models-comparison.md` 應加入 line-rate scaling 的對照表 — 為什麼 PostgreSQL serializable 在 multi-node 拿不到 line-rate、是 single-coordinator 限制；Spanner 不是「強一致 + 全球」奇蹟、是「coordinator 換拓樸」工程
- **High-impact 等級**：High（揭露 global SQL 的根本 frame、TrueTime 是手段不是目的）

### Finding F3.15：強一致 vs 全球部署不是「必須二選」、但跨 region quorum 是硬限

- **來源**：9.C10 Spanner「判讀」段第 2 點 + 「策略」段第 3 點
- **Case 類型**：Rich
- **揭露內容**：case 揭露兩件事：(1)「CAP 定理常被解讀為『全球部署只能 eventual consistency』、Spanner 顯示『投入專屬硬體（GPS、原子鐘）+ 演算法（TrueTime）可以同時拿到 strong consistency + global distribution』」、(2)「external consistency 必須等多區 quorum、跨洲交易延遲可達 100-200ms」。Spanner 不是免費全球、是 *用 latency 換 consistency*。
- **Outline mapping**：
  - Spanner 已覆蓋於：`truetime-api-depth.md` 操作流程「跨 region instance 配置時的 TrueTime 影響：voting region 越分散、ε 上限越高、commit wait 越長 → write latency 直接受 ε 影響」、`consistency-models-comparison.md` 操作流程決策樹
  - 該補但漏了：`consistency-models-comparison.md` 應 explicit 引用 case 的「100-200ms 跨洲延遲」數字、作為 latency budget 反推的 anchor — 目前 outline 提到「commit wait 10-50ms」但漏掉跨洲 quorum 數量級
  - Outline 缺口：`migrate-from-cloud-sql-pg.md` Driver 段「No-go condition」應加入「應用層延遲容忍 < 50ms write」這條 — 跨 region Spanner write 100-200ms、延遲敏感 workload 不該升 Spanner（case 已揭露）
- **High-impact 等級**：High（揭露 global SQL 的物理硬限 — quorum 光速）

### Finding F3.16：計費粒度 = 容量規劃顆粒、Spanner 早期 100 pu 起跳是 sizing barrier

- **來源**：9.C10 Spanner「判讀」段第 3 點
- **Case 類型**：Rich
- **揭露內容**：case 揭露「Spanner 早期最小單位是 100 processing units（pu）≈ 1 node、太大讓中小負載難以用。後來推出 100 pu 起跳的 granular sizing、讓容量規劃可以從小開始」。
- **Outline mapping**：
  - Spanner 已覆蓋於：無
  - 該補但漏了：`migrate-from-cloud-sql-pg.md` 的 Driver / No-go 段、應加入「Spanner sizing 起點」討論 — 對小 / 中型 PostgreSQL workload、Spanner 100 pu × per-pu monthly cost 可能比 Cloud SQL HA 設定貴很多倍、是 migration cost 邊界
  - Outline 缺口：`truetime-api-depth.md` 容量段提到 latency budget、漏掉 sizing budget；本批 Spanner outline 沒有 cost / sizing 軸的明示討論、僅 implicit
- **High-impact 等級**：High（揭露 Spanner migration 的 cost barrier、本批 outline 漏 sizing 軸）

### Finding F3.17：Spanner 10 億 req/sec 是「全使用者加總」、不是「單客戶配額」

- **來源**：9.C10 Spanner「需要警惕」段
- **Case 類型**：Rich
- **揭露內容**：case 自己警示「『10 億 req/sec』是 Google 內部的某個峰值瞬間、是 Spanner 服務 *全部使用者加總*、不是單一 instance 數字。讀案例時要區分『全球聚合峰值』跟『單一客戶能拿到的最大配額』」。這是 case 自帶的 fact vs derive 紀律。
- **Outline mapping**：
  - Spanner 已覆蓋於：無
  - 該補但漏了：本批 4 個 Spanner outline 都沒 explicit 引用 9.C10「10 億 req/sec」數字、避開了 over-extrapolation 風險。但 `truetime-api-depth.md` 跟 `consistency-models-comparison.md` 引 Google Ads / Play 作為 case anchor 時、應明示「Google internal dogfood、不是 customer-facing capacity」邊界
  - Outline 缺口：`migrate-from-cloud-sql-pg.md` 「無強案例」段已標明 9.C10 是 dogfood case、紀律到位
- **High-impact 等級**：Low（紀律已到位、但需在 truetime / consistency outline 補一句邊界）

## Outline 校準建議

### Keep（保留現狀、已正確 anchor）

- `storage-architecture.md` 對 9.C23 Netflix 的 anchor 跟 +75% derive 層分離（F3.9）— 紀律到位
- `cross-az-failover-rto.md` 對 9.C14 Standard Chartered 的合規 anchor（F3.6）
- `global-database-multi-region.md` 用 Standard Chartered 作為 *anti-recommendation*（不用 Global Database）的 anchor 設計很好（F3.6）
- `migrate-from-self-managed-pg-mysql.md` 用 Netflix 作為 operational consolidation driver、用 DraftKings 作為 cluster 拓樸 redesign（F3.10、F3.1）
- `consistency-models-comparison.md` 不依賴強案例、用 anomaly example 替代 — 對 dogfood case 是正確紀律

### Rewrite（需要 case anchor 加強或數字校準）

- `storage-architecture.md` 容量觀測段應加入 DraftKings 6ms 寫 / <1ms 讀作為 production reference（F3.2）、跟「韌性 + 性能不是 trade-off」frame（F3.7）
- `read-replica-scaling.md` 應拆「Auto-scaling 接不住秒級尖峰」失敗模式、explicit 引用 DraftKings「+50% no sweat = headroom 預留」判讀層（F3.4），跟 FanDuel 雙 SLO 並行 frame（F3.12），跟事件型分級（F3.13）
- `read-replica-scaling.md` 邊界段「何時拆 cluster vs 加 replica」應加「微服務拆分」這條 driver（F3.11）
- `migrate-from-self-managed-pg-mysql.md` Driver / No-go 段應加「合規禁止跨境複製」(F3.6)、案例對照引 Netflix 時補「Aurora 不是 all-purpose store」邊界（F3.10）
- `truetime-api-depth.md` 應在開頭加一段「TrueTime 的目的是消滅 single coordinator bottleneck、達成 line-rate scaling」商業邏輯先行段（F3.14）、並明示 9.C10 是 dogfood 邊界（F3.17）
- `consistency-models-comparison.md` 應加入 cross-region quorum 100-200ms 數量級 anchor（F3.15）

### Add（新增段落 / 子議題）

- `storage-architecture.md` 加「OLTP workload shape（讀寫雙峰錯位）」段（F3.5） — application-level pattern 跟 storage 設計的邊界
- `read-replica-scaling.md` 加事件型容量分級表（F3.13）跟讀寫雙峰錯位 driver（F3.5）
- `migrate-from-self-managed-pg-mysql.md` 加「合規驅動遷移的時程模型」段（F3.8） — 受監管 migration 的 lead time = 市場數 × 審查月份
- `migrate-from-cloud-sql-pg.md` 加 sizing barrier 討論（F3.16）— Spanner 100 pu 起跳對中小 PostgreSQL workload 的成本門檻

### Scope warning（避免 over-extrapolation）

- 9.C28 FanDuel 是 medium case、betting TPS / concurrent streams 數字 case 自己標明未公開。outline 不能寫「Aurora 在 betting 路徑撐 X TPS」（F3.12）
- 9.C10 Spanner 是 dogfood case、引用「10 億 req/sec」「2-nodes 45K reads」要 explicit 標明「Google internal、不是 customer-facing capacity」（F3.17）
- 9.C14 Standard Chartered 是 rich-but-保守 case、未公開 PostgreSQL 還是 MySQL、未公開具體 cost 數字。outline 不能擴寫「Standard Chartered 用 Aurora PostgreSQL」這類細節
- 9.C23 Netflix +75% 是「跨多 workload 最大值」、不是「每個 workload +75%」（case 自己警示）

## Managed SQL vs Global SQL frame

跨 5 case 抽出的根本對比：

### 軸 1：scaling 路徑根本不同

- **Managed SQL（Aurora）**：single-primary + storage 共享、scaling 兩個槓桿 — (a) read replica 分流（最多 15）、(b) cluster fleet 拓樸（DraftKings 200 cluster / Netflix microservice 私有 store / Standard Chartered 7 個合規 cluster）。+75% 效能來自 storage / compute 分離不是 multi-write。
- **Global SQL（Spanner）**：multi-leader Paxos、scaling 一個槓桿 — node 數線性擴展（2 → 4 nodes = 45K → 90K reads）。coordinator 不再是 bottleneck、是 TrueTime + Paxos 的 *拓樸感知多 leader*。

### 軸 2：consistency 跟 latency 的物理邊界

- **Managed SQL**：single-region single-primary、跨 AZ quorum 6ms 寫底線；跨 region 用 Global Database = async（< 1 秒 lag、reader-only）；要跨 region active-active 改 Aurora DSQL（paradigm shift）
- **Global SQL**：external consistency 是 default、TrueTime commit wait 是必付成本（ε ~1-7ms typical）；跨 region quorum 是物理光速硬限（跨洲 100-200ms write latency）。Spanner 不是「免費全球」、是「用 latency 換 consistency」

### 軸 3：fleet 治理 vs 單一 instance

- **Managed SQL**：production scale 必然走 fleet of cluster — DraftKings 200 cluster（business sharding）、Netflix 微服務私有 store、Standard Chartered 合規市場各自 cluster。容量規劃變成「per cluster 各自規劃 + fleet-level 治理（parameter / backup / IAM / observability fan-out）」
- **Global SQL**：one global cluster 跨 region。容量規劃變成「node 數預測 + sizing barrier（Spanner 100 pu 起跳對小負載偏貴）」。fleet 軸不存在、但 sizing 軸更敏感

### 軸 4：合規邊界處理方式

- **Managed SQL**：合規邊界用 fleet 拓樸吸收 — 每個受監管市場獨立 cluster（Standard Chartered 7 cluster）、Global Database 在合規禁止跨境複製場景反而違反合規。合規 lead time（3-12 月 / 市場）是時程主項。
- **Global SQL**：合規邊界用 instance configuration 吸收 — Spanner 提供 regional / dual-region / multi-region instance config、選 regional 即避開跨境。但 dogfood case（9.C10）跟公開 customer case（Sharechat / Blockchain.com）的合規模式不一定一樣、引用要保守。

### 對 DB4 reader journey 的影響

- **Aurora 章節後接哪些 vendor**：read replica scaling / fleet management 議題自然接到 DynamoDB（KV 替代）、Aurora DSQL（active-active 升級）— Aurora 是 *managed OLTP 的單一 vendor 路徑*
- **Spanner 是相鄰路由還是 paradigm shift**：Aurora → Spanner 是 paradigm shift（single-primary → multi-leader、storage 共享 → 全球 Paxos、async DR → external consistency）。reader journey 應明示「不是 Aurora 加強版」、是「不同的 OLTP 抽象」
- **共用討論軸**：fleet vs single instance、合規邊界、event-driven scaling vs sustained line-rate scaling — 兩家 vendor 都觸及、但解決方式不同
- **DB4 結構建議**：Aurora 章節在 storage-architecture / read-replica-scaling / global-database-multi-region 之間建立 fleet 軸 cross-link；Spanner 章節在 truetime / consistency / migrate-from-cloud-sql-pg 之間補 sizing 軸跟 dogfood 邊界明示
