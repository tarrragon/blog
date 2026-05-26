# Consistency Models 對照：external consistency vs serializability vs linearizability

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：團隊在 Spanner / CockroachDB / Aurora DSQL 之間選型、看文件講 strict serializability、external consistency、linearizable、snapshot isolation、serializable — 五個詞混用、不確定買的是哪一種保證
- 讀者徵兆：「我們需要強一致」但說不出強到哪、把 serializable transaction 跟 linearizable read 當同一件事、debug 對帳時發現「兩個 transaction 都 commit 成功、順序卻違反 user 體感」
- 真實壓力場景：金融帳本 — A 在台北轉帳給 B、B 在東京立即收到通知然後查餘額、結果查到「轉帳前」的餘額 — serializable 允許這種行為、external consistency 不允許
- Case anchor: [9.C10 Cloud Spanner planetary scale](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — Google Ads 計費需 external consistency；對照 PostgreSQL SSI、CockroachDB HLC、Aurora DSQL 的選擇

## 核心機制（Vendor-specific mechanism）

- 三個概念的精確定義：
  - **Serializability**：transaction 結果等同於 *某個* 序列順序執行；不要求順序跟 real-time 一致
  - **Linearizability**：單一 object 操作有全序、且全序跟 real-time wall-clock 一致；只談 single-object
  - **External consistency / Strict serializability**：transaction 層級的 serializability + 全序跟 real-time 一致；= 把 linearizability 推廣到 multi-object transaction
- Spanner 的 external consistency：用 TrueTime + commit wait 實作、保證 commit timestamp 順序 = real-time 順序
- CockroachDB 的對照：用 HLC（Hybrid Logical Clock）+ uncertainty interval、提供 serializable + per-key linearizable、不是完整 external consistency（有 read uncertainty restart 機制補）
- PostgreSQL SSI 的位置：serializable isolation、但 single-node、沒有跨節點時間保證
- Aurora DSQL（2024+）的位置：宣稱 strong consistency、internally serializable、跟 Spanner external consistency 的差異在 *跨 region* 行為（時間敏感 claim、實作前查官方文件）
- 對應 knowledge card：[linearizability](/backend/knowledge-cards/linearizability/)、[external-consistency](/backend/knowledge-cards/external-consistency/)、[isolation-level](/backend/knowledge-cards/isolation-level/)

## 操作流程（Operations）

- 決策樹：先問「跨 multi-object transaction 嗎」→ 是 → 「跨 region 寫入嗎」→ 是 → 「real-time 順序是產品契約嗎」→ 是 → Spanner / Aurora DSQL；否 → CockroachDB / PostgreSQL serializable 足夠
- 驗證一致性等級的方法：Jepsen-style test、寫 read-write workload 跑 anomaly checker、量 dirty write / lost update / write skew / G2 anomaly
- SDK 層的選擇點：Spanner 預設就是 external consistency、但 read 可降到 bounded staleness；CockroachDB 預設 serializable、可選 `AS OF SYSTEM TIME` 換 stale read；PostgreSQL 要顯式 `SET TRANSACTION ISOLATION LEVEL SERIALIZABLE`
- 驗證點：跑 G2-item / write skew 經典 anomaly test、確認系統行為符合宣告等級
- Rollback boundary：若一致性等級從強降到弱、要審計應用層所有讀取點（特別是「讀後決策再寫」的 critical path）

## 失敗模式（Failure modes）

- 把「我們用 transaction」當「強一致」：transaction 只保證原子性、不保證 isolation level；預設 isolation 可能是 read committed、寫 skew 直接漏
- 假設 single-node serializable = distributed serializable：PostgreSQL SSI 跨 read replica 立刻失效（replica lag）、團隊以為加 replica 還是 serializable
- 跨系統 timestamp 假設：service A 用 Spanner、service B 用 Redis、用各自 timestamp 重組事件順序 — service B 的 clock 沒 TrueTime 保證、跨系統 external consistency 不成立
- 把 linearizability 跟 strong consistency 混用、忽略 multi-object 場景：DynamoDB strongly consistent read 是 single-item linearizability、不等於跨 item transaction 強一致
- 過度承諾 external consistency：dashboard / analytics 強寫 strong read、付不必要的 latency tax
- Case 對應根因：金融對帳失敗的根因常是「以為 serializable = external consistency」、跨 region read 拿到舊版本

## 容量與觀測（Capacity & observability）

- 一致性等級對 latency 的影響量化：external consistency ≈ baseline；bounded staleness 可節省 commit wait（10-50ms）；eventual 再砍 quorum RTT
- Cloud Monitoring：`spanner` 系列觀察 commit latency 分布、CockroachDB 觀察 `sql.txn.restart.serializable` 計數（serializable restart 率）
- 回到 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 把一致性等級當 release gate 的一部分
- Capacity 觀點：external consistency 的 commit wait 是「無法 scale away 的 latency 支出」、capacity planning 要先扣這部分

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[truetime-api-depth](./truetime-api-depth.md)（external consistency 的硬體基礎）、[schema-migration-interleaved-tables](./schema-migration-interleaved-tables.md)（schema change 的版本一致性）
- Migration playbook 連結：[migrate-from-cloud-sql-pg](./migrate-from-cloud-sql-pg.md) 的 Diff 階段要明確標示一致性等級從 SSI 升到 external consistency 的應用層影響
- 跟 1.x 章節的互引：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)、[1.6 Transaction 設計](/backend/01-database/transaction-design/) （若存在）
- Knowledge card 雙引用：本文當 [linearizability](/backend/knowledge-cards/linearizability/) 卡片的 vendor 應用範例

## 寫作前置 checklist

- [ ] case anchor 確認：9.C10 Spanner 為主、其他系統當對照組（PostgreSQL SSI / CockroachDB / Aurora DSQL）但都不需強案例
- [ ] knowledge card 雙引用：linearizability + external-consistency + isolation-level 三張卡互引
- [ ] sibling 對比：concept-driven 文章、不需 production case 主導；用 anomaly example（write skew / G2）替代
- [ ] 預估寫作長度：280-340 行（三概念定義 + 對照表 + 反例展開）
