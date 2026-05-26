# CockroachDB Transaction Retry Pattern：serializable default 與 application contract 重塑

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：從 PostgreSQL（default `READ COMMITTED`）遷到 CockroachDB（default `SERIALIZABLE`）、application transaction retry 突然爆增、user-facing latency p99 高 5 倍、error rate 顯著上升
- 讀者徵兆：「為什麼同樣的 transaction 在 CockroachDB 一直 retry？」「`40001 serialization_failure` error 怎麼處理？」「我要把 application 改 retry loop 包起來嗎？」「能不能改 isolation level 回 READ COMMITTED？」
- Case anchor: primary [9.C39 DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/)（Aurora Postgres → CockroachDB 遷移時 application retry contract 重塑的真實案例、orders / dispatch hot path 的 retry pattern 是核心議題）；對照 [9.C4 DraftKings Aurora financial ledger](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 提供 *PostgreSQL READ COMMITTED + Aurora* 的另一條路徑（用 application-level sharding 避開 retry 而非處理 retry）

## 核心機制（Vendor-specific mechanism）

- Serializable default：CockroachDB default `SERIALIZABLE`（最強 isolation）、保證 transaction 結果等同某個 serial order
- Conflict detection：read / write set 衝突 → abort 後 transaction、發 `40001 serialization_failure`
- Application 端 retry：driver 不自動 retry、application 必須包 retry loop with exponential backoff
- 新增 `READ COMMITTED`（v23.2+）：可選的 weaker isolation、少 retry 但失去 serializable 保證
- Savepoint pattern：`SAVEPOINT cockroach_restart` + `ROLLBACK TO SAVEPOINT` 是官方推薦 retry 寫法
- 對應 knowledge card：[isolation-level](/backend/knowledge-cards/isolation-level/)、[transaction-boundary](/backend/knowledge-cards/transaction-boundary/)、[serialization-failure](/backend/knowledge-cards/serialization-failure/)（若已建）
- 跟 PostgreSQL serializable 差在哪：PostgreSQL serializable 用 SSI（Serializable Snapshot Isolation）+ predicate lock、CockroachDB 用 timestamp ordering + write intent；衝突偵測時機與成本不同

## 操作流程（Operations）

- Application retry loop（Go example）：

```text
for retry < MAX:
  BEGIN
  SAVEPOINT cockroach_restart
  ... do work ...
  RELEASE SAVEPOINT cockroach_restart
  COMMIT
  on serialization_failure: ROLLBACK TO SAVEPOINT, retry with backoff
```

- 配置：cluster-level `SET CLUSTER SETTING sql.defaults.default_int_size = 8`、application 端 `SET TRANSACTION ISOLATION LEVEL READ COMMITTED`（v23.2+）
- 驗證點：`crdb_internal.txn_stats` 看 retry rate、`SHOW SESSION default_transaction_isolation`
- Idempotency 設計：retry-safe transaction 必須是冪等（同樣 input 多次執行結果一致）、UPDATE balance SET balance = balance - X 是冪等、UPDATE balance SET balance = Y 不是
- Rollback boundary：transaction 自身有 SAVEPOINT 邊界、ROLLBACK TO SAVEPOINT 後可重試；commit 後不可回滾

## 失敗模式（Failure modes）

- Retry loop 沒上限：contention 嚴重時 retry storm、CPU 雪崩、要 max retry + circuit breaker
- 非冪等 transaction 重試：retry 後資料重複寫、ledger double-count、財務 incident
- Cross-statement state 假設：retry 從 SAVEPOINT 重來、application 端如果在 transaction 外 cache state、retry 後 state 不一致
- Hot row contention：高頻 update 同一 row（例：全局 counter）、serializable 衝突率 100%、改 sequence 或 distributed counter
- 改 READ COMMITTED 後忘了驗證業務語意：金融 ledger 用 READ COMMITTED 可能讓 balance 變負、必須留 serializable
- Long-running transaction：read 開始時間早、commit 時 conflict window 大、retry 機率隨 transaction duration 線性上升
- Case 對應根因：DraftKings ledger 在 PostgreSQL / Aurora 用 READ COMMITTED + application-level locking、遷 CockroachDB 必須改 SERIALIZABLE + retry loop 才能保留正確性

## 容量與觀測（Capacity & observability）

- CockroachDB Console metric：`Transaction retry rate`（per table）、`Serialization failure rate`、`Transaction duration p99`、`Hot ranges by retry count`
- Application metric：retry count per request、retry-induced latency p99、circuit breaker trip count
- 容量公式：基底 QPS × (1 + avg retry count) = 實際 transaction load
- Tuning：reduce transaction scope、kill long-running query、partition hot rows
- 回路徑：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 判斷 retry-bound vs CPU-bound、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) retry rate × baseline QPS

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[CockroachDB HLC + Raft consensus](./hlc-raft-consensus.md)（為什麼 serializable 是 default）、[CockroachDB locality-aware schema](./locality-aware-schema.md)（partition 降低 hot row contention）、[CockroachDB survival goals](./survival-goals.md)（cross-region latency 加長 retry window）
- 跟 PostgreSQL 對照：PostgreSQL READ COMMITTED 是 default、application 沒 retry loop 是 acceptable；遷 CockroachDB 必須重塑 application transaction contract
- Migration playbook：PG → CockroachDB 的 application audit 必看 transaction shape
- 1.x 章節互引：[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) 上游、[isolation level](/backend/knowledge-cards/isolation-level/) 卡
- 何時不用本文：純 read-only workload、無 contention、或已用 PostgreSQL serializable（contract 相似）

## 寫作前置 checklist

- [ ] case anchor 確認：等 C2 agent 補 application retry contract case；無 case 時 DraftKings ledger 對照「PostgreSQL READ COMMITTED」是 anti-recommendation 起點
- [ ] knowledge card 雙引用：[isolation-level](/backend/knowledge-cards/isolation-level/) + [transaction-boundary](/backend/knowledge-cards/transaction-boundary/)
- [ ] sibling 對比：跟 PostgreSQL serializable SSI 對照、跟 Spanner external consistency 對照
- [ ] 預估寫作長度：240-280 行（retry pattern + idempotency design + 5 種失敗模式展開）
- [ ] 寫作難度：中高（retry pattern 是 application contract 改寫、需要具體 Go / Python / Java code 示例、case 缺時用合成 ledger 場景）
