# TrueTime API 深度：GPS + 原子鐘、commit wait、為什麼 external consistency 需要它

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：跨 region OLTP 想保證「全球用戶看到的交易順序跟 wall clock 一致」、但 NTP 同步誤差動輒 10-100ms、足夠讓 region A 已 commit 的計費事件被 region B 看到一個更新的 timestamp 卻是舊狀態
- 讀者徵兆：分散式系統團隊在 Cloud SQL / Aurora 多 region 上做 read replica，發現「跨 region read 順序顛倒」「audit log timestamp 不可靠」「reconcile 對帳對不上」
- 案例壓力：Google Ads 計費需要把每筆扣款事件放進可驗證的 *外部* 順序、不只是 transaction 內部 serializable
- Case anchor: [9.C10 Cloud Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — Google Ads / Play 訂閱 / Search 計費跟 TrueTime 綁定

## 核心機制（Vendor-specific mechanism）

- TrueTime 的兩個 primitive：`TT.now()` 回傳一個 *interval* `[earliest, latest]`、不是單一時刻；`TT.after(t)` / `TT.before(t)` 判斷一個事件是否確定在 t 之後 / 之前
- 硬體基礎：每個 datacenter 部署 GPS 接收器 + 原子鐘冗餘（armageddon master）、time master 之間互相比對排除離群值、TrueTime daemon 從多個 master 拉時間並算 worst-case bound
- 不確定性 ε（epsilon）：跨 datacenter 同步 + clock drift 估計、目標維持在 1-7ms 區間（Google 論文 2012 引用、Spanner 文件 2024-2026 引用）
- Commit wait 機制：當一個 read-write transaction 要拿 commit timestamp s、Spanner 設 s = `TT.now().latest`、然後 *等待* 直到 `TT.after(s)` 才回 ACK — 這段「等」就是 commit wait、確保下一個 transaction 拿到的 timestamp 一定 > s（external consistency 的核心）
- 跟通用 [linearizability](/backend/knowledge-cards/linearizability/) 卡片的差異：linearizability 只要求「存在某個全序」、external consistency 進一步要求「全序跟 real-time 順序一致」、TrueTime 是把後者變可實作的關鍵
- 對應 knowledge card：[external-consistency](/backend/knowledge-cards/external-consistency/)、[linearizability](/backend/knowledge-cards/linearizability/)、[quorum](/backend/knowledge-cards/quorum/)

## 操作流程（Operations）

- 觀測 ε 的方式：Cloud Monitoring metric `spanner.googleapis.com/instance/clock_skew_ms`、判讀正常 < 7ms、異常 spike > 50ms 代表 time master 失聯
- 跨 region instance 配置時的 TrueTime 影響：voting region 越分散、ε 上限越高、commit wait 越長 → write latency 直接受 ε 影響
- read-only transaction 的 staleness 選項：`strong`（等 TrueTime 確認可讀最新）vs `exact_staleness`（讀 t 秒前快照、避開 commit wait）vs `bounded_staleness`（容忍 t 秒）— 三者 trade-off 與 SDK 範例
- 驗證點：跑 cross-region write + cross-region read benchmark、量 p50 / p99 write latency、確認 ≈ 2 × ε + quorum RTT
- Rollback boundary：TrueTime 配置不由用戶調、commit wait 由 Spanner 自動執行；應用層 rollback 邊界在「改用 stale read / bounded staleness」而不是「關掉 TrueTime」

## 失敗模式（Failure modes）

- ε 暴衝：GPS 干擾、datacenter time master 雙故障、ε 從 4ms 跳到 200ms → 所有 write 的 commit wait 暴增、p99 write latency 從 50ms 變 500ms — 徵兆是 Cloud Monitoring `commit_latencies` heatmap 整層平移
- 把 strong read 用在不需要的路徑：報表、analytics、user profile fetch 全用 strong read、每次 read 都付 TrueTime 對齊代價、p99 read 跟 write 同步退化
- 在 client 側做「自己的 timestamp」：app 用 `time.Now()` 當業務 key、跨 region 寫入時 client clock skew 直接破壞順序 — Spanner 內部 external consistency 對、業務層卻錯
- 把 Spanner 當 single-region SQL 用、卻配 multi-region instance：每筆 write 都付跨洲 quorum + commit wait、cost 跟 latency 都浪費
- ε 沒監控：team 直到事故才看 clock_skew metric、被動處理而非主動告警

## 容量與觀測（Capacity & observability）

- 必看 metric：`commit_latencies` (p50 / p95 / p99)、`api/request_count` by `method`、`instance/cpu/utilization_by_priority`、`clock_skew_ms`
- 用 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 框架把 TrueTime ε 跟 commit latency 配成 evidence pair
- 容量規劃路由：回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、把「ε × write rate」當 latency budget 的固定支出
- Alert 建議：clock_skew_ms > 20ms warn、> 50ms page；commit_latencies p99 偏離 baseline 2x 觸發 saturation discovery（回 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)）

## 邊界與整合（Boundary & next steps）

- 何時不用 strong read：reporting / analytics / dashboard 場景改用 bounded staleness 換 cost
- Sibling deep articles：[consistency-models-comparison](./consistency-models-comparison.md)（為什麼 external consistency ≠ serializability ≠ linearizability）、[schema-migration-interleaved-tables](./schema-migration-interleaved-tables.md)（schema change 也用 TrueTime 保證版本邊界）
- Migration playbook 連結：[migrate-from-cloud-sql-pg](./migrate-from-cloud-sql-pg.md) 的 cutover 階段需要把 application 對 timestamp 的假設審一遍
- 跟 1.x 章節的互引：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 用 TrueTime 當 PC 系統的代表、跟 Cosmos DB AP 系統對照
- Anti-recommendation：單 region workload 不該為了 external consistency 升 Spanner、Cloud SQL + serializable isolation 已經夠

## 寫作前置 checklist

- [ ] case anchor 確認：9.C10 Spanner planetary scale 為唯一已建立 case
- [ ] knowledge card 雙引用：external-consistency / linearizability / quorum 都需在內文反向 link 回本文
- [ ] sibling 對比：跟 PostgreSQL serializable（SSI）、Aurora DSQL TrueTime 替代方案的差異
- [ ] 預估寫作長度：260-320 行（TrueTime 機制密度高、commit wait 數學要展開）
