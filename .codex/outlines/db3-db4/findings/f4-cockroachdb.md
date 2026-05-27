# F4：CockroachDB Case Audit Findings

## Audit 範圍跟邊際遞減判讀

- **Audit 範圍**：3 個 direct case（9.C39 DoorDash、9.C40 Netflix、9.C41 Hard Rock Digital），全部 rich case。
- **Case 類型分類**：3 個都屬 rich case，含具體數字（QPS / cluster 數 / node 數 / vCPU / 跨州數）+ 業務情境 + 引用源；但每個 case 內都有清楚的 *觀察層 vs 判讀層* 分界（DoorDash「1.636M QPS」是觀察、「Aurora single-primary 是天花板」是判讀；Netflix「380+ cluster」是觀察、「artery of small DBs」是判讀；Hard Rock「100→33 node」是觀察、「賽季年度循環」是判讀）。
- **純新議題比例**：~85%（13 findings / 3 case ≈ 4.3 findings per case）。3 個 case 涵蓋三條主要 frame（single-primary 撞牆 / 補 Cassandra 缺口 / 合規 boundary），議題重疊 < 20%（DoorDash 跟 Hard Rock 都有 event-driven peak 角度、但 frame 取捨不同）。
- **邊際遞減判讀**：未觸發。3 case 各自揭露獨立 frame（OLTP single-primary 寫入瓶頸 / polyglot persistence fleet / 合規驅動 topology），重複 frame < 50%，純新議題 > 1 個 / case。若再加 1-2 個 case（如 Comcast、Bose）才會觀察到遞減。

## Findings 列表

### Finding F4.1：1.636M QPS 是 *Aurora 主 cluster 在那個時間點撞牆的痛點* 而非 CockroachDB 撐到的水位

- **來源**：9.C39 DoorDash「判讀」段需要警惕段
- **Case 類型**：rich（觀察層 fact）
- **揭露內容**：DoorDash 2020-04-17 高峰 > 1.636M QPS 走 Aurora、結果 multi-hour outage。case *明確警告* 不要把這個數字當成「CockroachDB 撐 1.6M QPS」的證據、它是 Aurora 撞牆的痛點。case 沒揭露遷移後單一 CockroachDB cluster 的峰值。
- **Outline mapping**：
  - 已覆蓋於：`hlc-raft-consensus.md` 問題情境段「Aurora Postgres 1.636M QPS single-primary 撞牆 → CockroachDB Raft per range」
  - 該補但漏了：outline 沒提 case 自己的警語（「1.636M 是 Aurora 痛點、不是 CockroachDB throughput claim」）、reviewer B 可能抓出「rich case 判讀層被當 fact」失分
  - Outline 缺口：寫稿時必須引用 case 警語、明示 1.636M QPS 屬「Aurora 撞牆訊號」而非「CockroachDB 容量證明」。屬陷阱 4（rich case 判讀層 vs 觀察層分層）

### Finding F4.2：single-primary 撞牆轉折點是 *primary CPU + WAL flush rate*、不是 IOPS

- **來源**：9.C39 DoorDash「策略」段 1
- **Case 類型**：rich（判讀層 derive）
- **揭露內容**：case 明確指出 Aurora / RDS Postgres 寫入持續成長最終撞天花板、轉折點是「primary CPU + WAL flush rate」、不是 IOPS。
- **Outline mapping**：
  - 已覆蓋於：無
  - 該補但漏了：`hlc-raft-consensus.md` 失敗模式段沒提這個轉折訊號；`aurora-dsql-spanner-decision-tree.md` 「是否要 distributed SQL」決策的觸發訊號段沒提
  - Outline 缺口：應補進 `hlc-raft-consensus.md` 的「為什麼要 distributed SQL」段、或補進決策樹的「問題 0：什麼訊號代表 single-primary 該換掉」前置。屬 outline 沒覆蓋的新主題。

### Finding F4.3：OLTP 引擎遷移的「兩階段紓壓」原則

- **來源**：9.C39 DoorDash「策略」段 2 + 觀察段表格
- **Case 類型**：rich（fact）
- **揭露內容**：DoorDash 不是「一次性換引擎」、而是「先寫工具把 table 從主 cluster 拆到獨立 Aurora cluster（紓壓）」+「再寫第二套工具把 Aurora → CockroachDB（換引擎）」。第一階段一個月內把 dozens of tables 拆出、第二階段是自動化 lossless migration pipeline。
- **Outline mapping**：
  - 已覆蓋於：無（所有 outline 都沒處理 migration 路徑）
  - 該補但漏了：`transaction-retry-pattern.md` 在「從 PostgreSQL 遷到 CockroachDB」段提到 application contract 重塑、但沒提引擎遷移的兩階段紓壓
  - Outline 缺口：屬 migration playbook 議題、不該硬塞進現有 5 篇 outline。建議：在 `transaction-retry-pattern.md` 補一個 sibling cross-link 指向 `[01.4 database migration playbook]`、或在 `aurora-dsql-spanner-decision-tree.md` 補「migration 路徑」段引用此 case。

### Finding F4.4：PostgreSQL wire 相容是 *protocol-level* 而非 fork，SQL 行為仍要 audit

- **來源**：9.C39 DoorDash「策略」段 3
- **Case 類型**：rich（明確澄清）
- **揭露內容**：CockroachDB 保留 PostgreSQL wire protocol 相容、降低 application 層改動；但 CockroachDB *不是* PostgreSQL fork、實際 SQL 行為（serializable default、retry semantics、partial index）仍要驗證。
- **Outline mapping**：
  - 已覆蓋於：`aurora-dsql-spanner-decision-tree.md` 軸 3「CockroachDB PostgreSQL wire（高相容）」
  - 該補但漏了：outline 寫「高相容」太樂觀、case 明確說 *protocol-level 相容、SQL 行為仍要 audit*。`transaction-retry-pattern.md` 從 PostgreSQL 遷 CockroachDB 段該明示這個分界
  - Outline 缺口：`aurora-dsql-spanner-decision-tree.md` 應補「PostgreSQL 相容性 audit checklist」段（serializable default / retry semantics / partial index 三項）；`transaction-retry-pattern.md` 該段引用此 case 而非合成範例

### Finding F4.5：cluster 數量增加、alert volume 反而下降的反直覺結論

- **來源**：9.C39 DoorDash「判讀」段 3
- **Case 類型**：rich（判讀層 derive）
- **揭露內容**：DoorDash 遷移後跑更多 cluster、但 incident alert volume 反而下降。case 判讀理由：每個 CockroachDB cluster 內建 Raft 自動容錯、單節點 fail 不會 page on-call、Aurora 時代的「primary failover alert」消失。
- **Outline mapping**：
  - 已覆蓋於：無
  - 該補但漏了：`survival-goals.md` 提到「Raft 3-replica 自動 failover」但沒從 alert / on-call burden 角度切入；`hlc-raft-consensus.md` 失敗模式段沒從反面（成功訊號）寫
  - Outline 缺口：屬陷阱 4 邊界（判讀層 derive、引用要分層）。建議在 `survival-goals.md` 容量與觀測段補「告警 surface 變化」訊號、引用 DoorDash case + 標明「case 中此屬作者判讀層」

### Finding F4.6：Cassandra 5 條件湊不齊的 transactional 缺口

- **來源**：9.C40 Netflix「判讀」段 1
- **Case 類型**：rich（fact 列五條件）
- **揭露內容**：Netflix 2019 評估後選 CockroachDB 補 Cassandra 缺口、五個並存條件：multi-active topology、global consistent secondary index、global transaction、open source、SQL。Cassandra 在 transactional 場景 *湊不齊* 這五項。具體場景：Studio Cloud Drive（強一致 metadata + 全球可寫）、Open Connect 控制平面、Spinnaker、Maestro、Gaming control plane。
- **Outline mapping**：
  - 已覆蓋於：無、5 個 outline 都沒寫「Cassandra vs CockroachDB 五條件」對比
  - 該補但漏了：`aurora-dsql-spanner-decision-tree.md` 的決策樹只比 Aurora / Spanner / DSQL 三家、漏掉「Cassandra → distributed SQL」這條路徑（Netflix 是這條路徑的代表）
  - Outline 缺口：屬 outline 沒覆蓋的新主題。建議在 `aurora-dsql-spanner-decision-tree.md` 補「決策樹前置問題：你是從 single-primary 遷還是從 eventual consistency 遷？」段、引用 Netflix case；或在 `survival-goals.md` 補 polyglot persistence 上下文

### Finding F4.7：380+ cluster 是「artery of small DBs」哲學、不是巨型 DB

- **來源**：9.C40 Netflix「判讀」段 2 + 策略段 2
- **Case 類型**：rich（判讀層 derive）
- **揭露內容**：380+ cluster ≠ 一個巨型 DB。Netflix 模型是「每個微服務 / 應用配自己 cluster」、cluster sizing 從幾個 node 到 60 nodes、最大 60 nodes / 26.5 TB。容量規劃變成「每 cluster 各自規劃」、不是「全公司一條容量曲線」。
- **Outline mapping**：
  - 已覆蓋於：無
  - 該補但漏了：`hlc-raft-consensus.md` 容量與觀測段寫「整 cluster scale-out 加 range」的容量公式、太單一；`locality-aware-schema.md` 沒提「per-app cluster」邊界
  - Outline 缺口：屬「容量規劃顆粒」議題、應在 `hlc-raft-consensus.md` 容量段補「cluster boundary 顆粒」訊號、或在 `aurora-dsql-spanner-decision-tree.md` 補「per-app cluster vs shared cluster」決策軸。屬陷阱 4 邊界（artery of small DBs 是 case 判讀層）

### Finding F4.8：multi-region 是 *survival*、不是 latency 優化

- **來源**：9.C40 Netflix「判讀」段 3 + 策略段 3
- **Case 類型**：rich（fact + 反直覺判讀）
- **揭露內容**：Netflix 60+ multi-region cluster 主要動機是 region-level survival、不是降 latency（跨 region quorum 反而增 latency）。Gaming cluster 48-node 跨 4 region 就是為了 region failover 不停服、不是讓玩家延遲變低。
- **Outline mapping**：
  - 已覆蓋於：`survival-goals.md` 問題情境段「region survival 寫入 latency 是 zone survival 的 3 倍」已隱含；`hlc-raft-consensus.md` 容量段 p99 latency 預算「multi-region 跨洲 100-150ms」已隱含
  - 該補但漏了：兩篇 outline 都把這個結論當技術 fact、漏掉 case 的反直覺定位 frame（「multi-region 動機釐清成 survival、不是 latency」是業務層判讀）
  - Outline 缺口：應在 `survival-goals.md` 核心機制段補「為什麼選 region survival」判讀條件、引用 Netflix Gaming 48-node 案例

### Finding F4.9：self-managed 380+ cluster 需要專屬 Database Platform Team

- **來源**：9.C40 Netflix「判讀」段需要警惕 + 策略段 4
- **Case 類型**：rich（fact + 邊界警告）
- **揭露內容**：Netflix 是 self-managed、不是 Cockroach Cloud。需要專屬 Database Platform Team 養 380+ cluster（含 backup、upgrade、incident response、capacity review）。沒這量級團隊的組織直接 self-host 380 cluster 是 ops 自殺、Cockroach Cloud 才是合理路徑。
- **Outline mapping**：
  - 已覆蓋於：`aurora-dsql-spanner-decision-tree.md` 失敗模式段「self-managed CockroachDB 低估 ops cost」
  - 該補但漏了：失敗模式只說「DBA bandwidth 沒到位變 disaster」、太抽象；Netflix 「需要專屬 Database Platform Team」是 concrete 訊號
  - Outline 缺口：應在 `aurora-dsql-spanner-decision-tree.md` 失敗模式段引用 Netflix case、加「self-managed cluster 數量 vs 平台團隊規模」判讀訊號（小規模 self-managed 不需要、大規模需要、轉折點在哪 case 沒講要謹慎）

### Finding F4.10：法規顆粒決定基礎設施拓樸、不是反過來

- **來源**：9.C41 Hard Rock Digital「判讀」段 1 + 策略段 1
- **Case 類型**：rich（fact + 業務判讀）
- **揭露內容**：美國 Wire Act 要求 betting data 必須在下注州內處理 → 每個營運州都要有州內運算資源。傳統「每州一個獨立 silo」path 撞牆於跨州統一帳戶、跨州 reporting、欺詐偵測。Hard Rock 用 AWS Outposts 把運算放進州內、但邏輯上仍是 *一個* CockroachDB cluster、region placement 配置決定哪些 range 釘在哪個 Outpost。
- **Outline mapping**：
  - 已覆蓋於：`locality-aware-schema.md` 問題情境段提到「Wire Act 合規逼出 row-level locality 配置」
  - 該補但漏了：outline 只提合規驅動 row-level locality、漏掉「邏輯一個 cluster + 物理跨州 Outpost」這個拓樸創新、漏掉「為什麼不是每州獨立 cluster」的失敗模式對比
  - Outline 缺口：應在 `locality-aware-schema.md` 失敗模式段補「拆獨立 cluster 解合規但破壞業務邏輯」反模式、引用 Hard Rock 對比 Standard Chartered。屬高 impact finding。

### Finding F4.11：survival goal 對應 *業務 SLO*（bet placement RPO=0）

- **來源**：9.C41 Hard Rock Digital「判讀」段 2 + 策略段
- **Case 類型**：rich（fact + 業務語意）
- **揭露內容**：bet placement 不能 lose、玩家下注後 crash 沒紀錄對博彩牌照是合規事故。CockroachDB Raft 3-replica + 跨 AZ 配置讓 Outpost 失敗時其他 replica 在、自動 failover。survival goal「Outpost 或 AZ 失敗不丟」是業務 SLO 翻譯成 DB 層配置。
- **Outline mapping**：
  - 已覆蓋於：`survival-goals.md` 失敗模式段提到「合規邊界 violation：受監管市場資料不能跨境」（但用 Standard Chartered 對比）
  - 該補但漏了：outline 該舉「業務 SLO → survival goal」的反向翻譯（從業務不能丟某事件、倒推 RPO=0、倒推哪種 survival goal）；Hard Rock 是這條路徑的 concrete case
  - Outline 缺口：應在 `survival-goals.md` 操作流程段補「從業務 SLO 倒推 survival goal 的步驟」、引用 Hard Rock bet placement 案例

### Finding F4.12：賽季型 scale up / down 是業務年度循環、不是異常事件

- **來源**：9.C41 Hard Rock Digital「判讀」段 3 + 策略段 3
- **Case 類型**：rich（fact）
- **揭露內容**：100 nodes → 33 nodes → 100 nodes 的擺盪在 sportsbook 是 *年度循環*（NFL 季結束 / NBA 季初切換）、流量結構性下降。CockroachDB 加減節點靠 range rebalance、不停服。容量規劃要直接把 NFL / NBA / 國際賽事曆塞進預測模型、不要當 surprise。
- **Outline mapping**：
  - 已覆蓋於：無 5 篇 outline 直接涵蓋
  - 該補但漏了：`hlc-raft-consensus.md` 容量段、`survival-goals.md` 容量段都沒提「節點數隨業務季節擺盪」的 ops 視角
  - Outline 缺口：屬於 sportsbook 業務特例、不該強塞進 5 篇 outline、屬 9.6 容量規劃模型外部 routing。建議在 `aurora-dsql-spanner-decision-tree.md` 補「distributed SQL 對 elastic scaling 的訊號 — 業務 seasonality 強烈時優於 single-primary」、引用 Hard Rock case

### Finding F4.13：邊緣硬體（Outposts / Local Zones）是 *合規工具*、不是 latency 工具

- **來源**：9.C41 Hard Rock Digital「策略」段 2
- **Case 類型**：rich（澄清性 fact）
- **揭露內容**：AWS Outposts 主要為「資料留某地理邊界」存在、latency 改善是副作用。決策時先看合規驅動力、latency 改善列為 bonus。
- **Outline mapping**：
  - 已覆蓋於：`locality-aware-schema.md` 問題情境段提到「Wire Act 合規逼出 row-level locality 配置」+「AWS Outposts」、但沒明示「Outposts 是合規工具、不是 latency 工具」的反直覺判讀
  - 該補但漏了：outline 寫的時候容易把 Outposts 描述為「跨州延遲改善」、實際 case 明說是合規驅動
  - Outline 缺口：屬 outline 寫稿時的陷阱、應在 `locality-aware-schema.md` 失敗模式段補「把 Outposts 當 latency 工具是動機誤判」訊號

### Finding F4.14：「省了 10-20 工程師」是 *機會成本*、不是節省支出

- **來源**：9.C41 Hard Rock Digital「判讀」段需要警惕段 + 策略段 4
- **Case 類型**：rich（明確澄清的 fact）
- **揭露內容**：Hard Rock 50 人 tech team、估「若用 PostgreSQL 需多加 10-20 工程師」。case *明確警告* 這是「沒招那麼多 DBA」的機會成本、不是已 hire 後解雇。distributed SQL 的 ops 槓桿來自系統內建 Raft / placement 把 DBA 工作壓進系統內。
- **Outline mapping**：
  - 已覆蓋於：`aurora-dsql-spanner-decision-tree.md` 失敗模式段「self-managed CockroachDB 低估 ops cost」（反向、為何要付出 ops cost）
  - 該補但漏了：沒人寫「distributed SQL 對小團隊的 ops 槓桿」這個 *正向* frame
  - Outline 缺口：應在 `aurora-dsql-spanner-decision-tree.md` 補「team size 是 distributed SQL 適配的決策訊號」段、引用 Hard Rock 50 人 case；同時引用 case 的警語（「機會成本、不是節省支出」）避免陷阱 4

## Outline 校準建議

### Keep（5 篇 outline 哪些被 case 充分支撐）

- **`hlc-raft-consensus.md`**：HLC + Raft + leaseholder 機制本身屬 vendor 文件範疇、case 補 production scale 訊號（DoorDash 1.636M / Netflix 380+ cluster）足夠。**機制段 keep**、但容量與觀測段該結合 F4.7 補「per-cluster 容量規劃」訊號
- **`survival-goals.md`**：zone vs region survival 機制 keep。Case anchor（Hard Rock + Netflix）對 region survival 的支撐充分
- **`transaction-retry-pattern.md`**：serializable default + retry pattern + idempotency 設計 keep。Case anchor（DoorDash）對 application contract 重塑的支撐有但 *稍弱*（DoorDash case 沒明寫 retry contract 重塑、是 outline 推論的）— 見 scope warning
- **`aurora-dsql-spanner-decision-tree.md`**：三軸（topology / managed 成熟度 / SQL 相容）+ 五問題決策樹 keep。Case 三家 ground truth 已備

### Rewrite（哪幾篇 framing 該改）

- **`locality-aware-schema.md`**：三種 table locality 機制 keep、但 framing 該從「global SaaS GDPR 場景」改為「Hard Rock 跨州合規 + 邏輯一個 cluster」。GDPR 場景是合成範例、Hard Rock 是 concrete case。F4.10 + F4.13 揭露的「邏輯一個 cluster + 物理跨地理 placement」frame 該主導第一段問題情境

### Add（findings 揭露但 outline 沒覆蓋的新主題）

- **F4.2 single-primary 撞牆訊號（primary CPU + WAL flush rate）**：應補進 `hlc-raft-consensus.md` 「為什麼要 distributed SQL」前置段
- **F4.3 OLTP 引擎遷移兩階段紓壓**：應補進 `transaction-retry-pattern.md` 或 `aurora-dsql-spanner-decision-tree.md` 的 migration 路徑段
- **F4.4 PostgreSQL 相容性 audit checklist**：應補進 `aurora-dsql-spanner-decision-tree.md` 「PostgreSQL 相容性」段
- **F4.6 Cassandra 5 條件湊不齊**：應補進 `aurora-dsql-spanner-decision-tree.md` 決策樹前置「你是從 single-primary 還是從 eventual consistency 遷？」
- **F4.14 distributed SQL 對小團隊 ops 槓桿**：應補進 `aurora-dsql-spanner-decision-tree.md` 「team size」決策軸

### Scope warning（哪幾篇有 over-extrapolation 風險）

- **`transaction-retry-pattern.md`**：outline 寫「DoorDash orders / dispatch hot path 的 retry pattern 是核心議題」— DoorDash case *沒寫* serializable retry contract / 40001 / SAVEPOINT pattern / hot row contention。case 只寫 PostgreSQL wire 相容、實際 SQL 行為（serializable default、retry semantics）要驗證。outline 把「需驗證」推論為「retry pattern 是核心議題」是 *跨 case 合成 frame*（陷阱 8）。建議：寫稿時要 *明示* DoorDash case 沒直接揭露 retry pattern、本章是從 PostgreSQL → CockroachDB 通用 contract 重塑視角合成。Sibling `9.C4 DraftKings` 對比也是 outline 合成（DraftKings case 沒寫 retry pattern、case 是 Aurora 內 sharding 路徑）。
- **`hlc-raft-consensus.md`**：outline 容量段寫「single-region 3-replica write p99 3-5ms；multi-region 跨洲 100-150ms」— 這些數字 *沒有* 來自 3 個 case（DoorDash / Netflix / Hard Rock 都沒揭露 p99 數字）。是 outline 自生通用數字。寫稿時應明示「以下 latency 數字屬通用工程估算、case 未揭露具體數字」、避免陷阱 1（skeleton case 擴寫成 case 事實）
- **`survival-goals.md`**：outline 失敗模式段「write latency 暴漲：zone → region survival 寫 latency 從 5ms 跳到 50ms+」— Netflix 案例沒揭露具體 latency 數字、Hard Rock 也沒寫。屬 outline 自生。寫稿要分層
- **`aurora-dsql-spanner-decision-tree.md`**：outline 寫「Spanner 10+ 年 Google 內部 + 外部 GA」「Aurora DSQL 2024-05 GA（最新）」— 3 case 都沒揭露 GA 時間 / 成熟度比對、依靠 9.C10 Spanner case 跟外部知識。寫稿時要明示來源層次（case vs vendor 公開文件 vs 外部知識）

## Distributed SQL paradigm shift frame

3 case 共通的 frame 浮現出 3 個視角、影響 DB4 內部 distributed SQL 子組（CockroachDB / Spanner / Aurora DSQL）的 reader journey：

### Frame 1：single-primary 撞牆訊號的兩條路徑

- **DoorDash 路徑**：寫入量持續成長、primary CPU + WAL flush 撞天花板 → 換 multi-primary 引擎（CockroachDB）
- **Netflix 路徑**：Cassandra eventual consistency 撐不住 transactional 需求 → 補 distributed SQL（CockroachDB）
- **Hard Rock 路徑**：合規逼出地理邊界 + 不想 silo 化 → 用 distributed SQL 的 placement 能力一個邏輯 cluster
- **Reader journey 啟示**：DB4 內部 distributed SQL 系列文章該先讓讀者識別自己屬哪條路徑、再進機制（HLC / locality / survival）。建議 `aurora-dsql-spanner-decision-tree.md` 改成 entry point、加「你的撞牆訊號是哪條路徑」前置段

### Frame 2：application contract 重塑（serializable retry / idempotency）的 case 支撐度

- 3 個 case 對 application transaction contract 重塑的揭露 *都偏弱*：DoorDash 只寫 PostgreSQL wire 相容、SQL 行為要驗證；Netflix / Hard Rock 都沒寫 retry pattern
- 這個議題在 vendor 文件（Cockroach Labs blog、SQL Layer docs）有充分覆蓋、但 *case 庫沒 ground truth*
- **影響**：`transaction-retry-pattern.md` 要走 standard-driven（依 vendor 文件） + DoorDash case 作為觸發 context、而不是宣稱 case 揭露 retry contract。屬陷阱 8（跨 case 合成 frame 升級成 case 揭露）的高風險檔

### Frame 3：locality + survival 的合規 / 部署 trade-off

- **Netflix**：survival 動機釐清為 region failure 容忍、不是 latency；multi-region cost 用 polyglot persistence 收斂（CockroachDB 只放 transactional 補位、其餘給 Cassandra）
- **Hard Rock**：合規動機釐清為地理邊界、不是 latency；用 Outposts + region placement 解獨立 cluster 的業務邏輯破壞
- **跨 case 合成 frame**：locality + survival 是「業務 / 合規」的兩個顆粒、不是「latency 優化」的 fine-grained tuning。`locality-aware-schema.md` + `survival-goals.md` 兩篇該共用這個 frame、SSoT 對應建議：locality 主寫 `locality-aware-schema.md`、survival 主寫 `survival-goals.md`、跨主題的「業務動機 vs latency 動機」frame 寫進 `survival-goals.md`（業務 SLO 視角更接近）、`locality-aware-schema.md` cross-link 不展開
