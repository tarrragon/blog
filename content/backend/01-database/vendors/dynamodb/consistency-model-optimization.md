---
title: "DynamoDB Strongly Consistent → Eventually Consistent：same protocol, different contract"
date: 2026-05-19
description: "DynamoDB consistency model 從 strongly consistent read 改 eventually consistent read 是 50% cost 優化但風險集中在 application contract — 同 vendor / 同 protocol / 同 table / 不同 read consistency；驗證 [#128](/report/data-topology-as-audit-dimension/) self-aware limitation 提出的 consistency axis 候選；涵蓋 read pattern audit / 5 個 production 踩雷"
weight: 11
tags: ["backend", "database", "dynamodb", "consistency", "migration", "axis-candidate"]
---

> 本文是 [DynamoDB](/backend/01-database/vendors/dynamodb/) overview 的 implementation-layer deep article。同時是 [#128 self-aware limitation](/report/data-topology-as-audit-dimension/) 第 1 點「6 維仍可能漏類（identity / consistency / residency 三軸候選）」的 *consistency 軸驗證*。

## Same protocol, different contract：consistency model 對照

DynamoDB 的 read 操作支援兩種 consistency：

| 屬性                    | Strongly Consistent Read           | Eventually Consistent Read         |
| ----------------------- | ---------------------------------- | ---------------------------------- |
| Protocol                | 同（DynamoDB API）                 | 同                                 |
| API call                | 同 `GetItem` / `Query` / `Scan`    | 同（多 `ConsistentRead=false` flag）|
| 結果                    | 最新 commit 的值                   | 可能 stale 0-100ms                 |
| Latency p99             | 5-15ms                             | 1-5ms                              |
| Throughput cost (RCU)   | 1 RCU per 4KB read                 | **0.5 RCU per 4KB read**           |
| Cross-AZ                | 跨 AZ 讀（quorum）                 | 單 AZ 讀                           |
| 故障行為                | leader unavailable 時 read 失敗     | secondary alive 時 read 仍 work    |

兩者 *同 protocol, same API, same table* — 唯一差異是 *application contract*：能否接受 0-100ms 的 staleness。

跑 [6 維 diff dimension audit](/report/content-structure-by-max-diff-dimension/) 對「strongly consistent → eventually consistent」遷移：

| 維度                 | 評估                                      | 等級       |
| -------------------- | ----------------------------------------- | ---------- |
| Schema / API         | 同 API、只改 ConsistentRead flag         | Low        |
| Operational model    | 同 cluster、operational stack 不變        | Low        |
| Paradigm             | 同 NoSQL document store                   | Low        |
| Components           | 同 1 個 table                             | Low        |
| Application change   | 每個 read site 評估、可改                 | Medium     |
| Data topology        | 同 partition / replication                | Low        |
| **Consistency contract** | **strong → eventual、application semantic 完全改** | **High** |

6 維 audit 抓不到「Consistency contract = High」這軸。用既有 6 維歸類、會走 Type B drop-in + application change 中維獨立段；但這個歸類 *漏掉真正的工作量*：

- Application code change（加 ConsistentRead flag）：~10%
- Operational verification：~5%
- **Application contract review（每個 read site 評估 staleness 是否可接受）：~85%**

工作量主軸在 *contract semantic 重審*、不在既有 6 維任一個。Consistency 是 *候選的第 7 維*（或 8 維、跟 identity 並列）。

## Consistency axis 是否獨立：3 個論據

**Yes、consistency 是獨立軸**：

1. **Schema / paradigm / operational 不變 → consistency 仍可變**：同 DynamoDB table、同 application、同 IAM、只改 `ConsistentRead` flag、cost 砍半但 application contract 改；其他 6 維皆 Low、但工作量 80%+ 在 contract review
2. **Paradigm 是 high-level、consistency 是 low-level**：Kafka ↔ NATS 是 paradigm 差（log-based vs subject-based）；DynamoDB strong → eventual 是 *同 paradigm 內的 consistency 子議題*；歸 paradigm 維度太粗
3. **可獨立發生**：PostgreSQL `READ COMMITTED → SERIALIZABLE` migration 同 vendor 同 schema 同 operational、只改 isolation level；Cassandra `LOCAL_QUORUM → EACH_QUORUM` 同 vendor、只改 consistency level — 都是 consistency 獨立變動的 case

**No、consistency 可塞 paradigm**：

- 反論：consistency 是 paradigm 的子議題
- 拒絕：paradigm 涵蓋 *核心抽象*（OLTP / log / pub-sub / document）、consistency 是 *正確性 contract* 屬不同 axis

實證：本文 migration 工作量 85% 在 contract review、確認 consistency 是 *獨立工作量主軸*。

## 結構：類 Type B + consistency contract review 獨立段

跟既有 Type B [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) 對照、本文多出 *consistency contract review* 獨立段：

```text
1. Same protocol, different contract（consistency axis 對照表開頭）
2. Consistency axis 是否獨立的論據
3. 結構 differentiator（類 Type B + contract review）
4. Read site audit (per-call site review)
5. Migration 流程（dual-read 觀察 + canary cutover）
6. Production 故障演練
7. Capacity / cost
8. 整合 / 下一步
```

8 章節、200-260 行。比標準 Type B 多 1 段（contract review）+ 1 段（axis 獨立論據）。

## Read site audit：per-call site contract review

不是 *table-level* 決定 consistency、是 *call site-level* 決定。每個 `GetItem` / `Query` / `Scan` 必須單獨 audit：

```python
# Pre-audit application code
# Find all DynamoDB read sites
$ grep -r "table.get_item\|table.query\|table.scan" src/

# Per-site contract review template:
# - Site: src/order_service.py:123 - get_item by order_id
# - Context: 顯示 order detail page、user 剛點「我的訂單」
# - Contract: user 可接受 100ms 內 stale data?
# - Decision: YES → ConsistentRead=False, saves 50% RCU
#             NO  → keep ConsistentRead=True
```

Audit 分類矩陣（典型 application）：

| Read pattern                            | 預設 consistency       | Eventual 是否可接受 | 估佔比 |
| --------------------------------------- | ---------------------- | ------------------- | ------ |
| User read 自己剛 commit 的 data          | Strong（read-your-write）| 通常 NO            | 5-10%  |
| List query（顯示用 / search 結果）       | Strong（過度保守）     | YES                 | 30-40% |
| Background job / analytics              | Strong（過度保守）     | YES                 | 20-30% |
| Real-time dashboard refresh             | Strong                 | depends（refresh 間隔）| 10-15% |
| 跟 strongly consistent write 同 transaction | Strong（必要）      | NO                  | 5-10%  |
| Health check / monitoring               | Strong（不必要）       | YES                 | 5-10%  |

audit 完後 application 端 60-80% read site 可改 eventual、剩餘 20-40% 保留 strong；整體 RCU cost 降 30-40%。

## Migration 流程

### Phase 0：Audit + classify

- Grep application code 找所有 read site
- per-site contract review、決定 strong / eventual
- 估計 RCU saving

### Phase 1：低風險 site 切換

```python
# Before
response = table.get_item(
    Key={'order_id': order_id},
    ConsistentRead=True  # 預設保守
)

# After（顯式設）
response = table.get_item(
    Key={'order_id': order_id},
    ConsistentRead=False  # 明示 eventual OK
)
```

從 *background job / search result* 開始（低風險、staleness impact 低）、跑 1 週觀察 application metric。

### Phase 2：中風險 site 切換

- User-facing list query
- Dashboard refresh
- 配 application-side 「last updated X seconds ago」hint 讓 user 知道是 cached/stale

### Phase 3：審慎 site 保留 strong

- Read-your-write pattern
- Transactional read
- Financial / payment-critical lookup

Decision document 寫進 ADR、之後新 read site 直接套規則。

## Production 故障演練

### Case 1：Read-your-write 失效、user 看到自己沒提交的舊資料

**徵兆**：user 在 settings page 改了 email、submit 後跳轉首頁、首頁 widget 顯示舊 email 5-30 秒；user feedback「我改了但沒生效」。

**根因**：首頁 widget 用 `ConsistentRead=False` 讀 user profile、剛 commit 的 write 還在 propagate；違反 read-your-write semantic。

**修法**：

1. **Read-your-write 場景強制 strong read**：user 自己 fetch 自己的 data、加 `ConsistentRead=True`
2. **Application-side cache invalidation**：write 後立刻 invalidate local cache、避免 stale read 餵 user
3. **Routing**：user-self-fetch 路由到 strong read、其他 user 看 user 用 eventual read（90% 流量仍便宜）

### Case 2：跨 record consistency 假設失效

**徵兆**：application 寫 order + 寫 inventory（兩個 record）、之後 read order + read inventory；發現有時 order 已寫 inventory 沒寫、application 顯示「order created but inventory not updated」、business state inconsistent。

**根因**：DynamoDB *沒 transaction 跨多 record*（除非用 `TransactWriteItems` API）；eventual read 加劇 inconsistency window；strong read 並不解決根因。

**修法**：

1. **架構**：跨 record 寫入用 `TransactWriteItems`、確保 atomic
2. **read 端 saga pattern**：accept eventual + application-level retry/reconcile
3. **eventual consistency 不是 root cause**：strong read 也會看到 inconsistency、修跨 record write 是根因解

### Case 3：Background job retry 跑舊資料

**徵兆**：background job 每 5 分鐘掃 unprocessed orders、用 `ConsistentRead=False`；偶爾 job retry 2 次都 process 同 order、duplicate processing。

**根因**：job round 1 抓到 unprocessed order → mark as processed；job round 2 read 仍看到 *未 mark* 的舊狀態（eventual stale）、又 process 一次。

**修法**：

1. **Idempotent processing**：用 order ID + 自己 dedup 表、不依賴 DynamoDB consistency
2. **Conditional write**：`UpdateItem` 加 `ConditionExpression: attribute_not_exists(processed_at)`、duplicate 由 DynamoDB 拒絕
3. **不切 strong**：background job 切 strong 也只是 *減少* duplicate 機率、不解決；用 idempotent + conditional 才對

### Case 4：Cost 沒降反升、application 改錯方向

**徵兆**：切換 6 個月後 RCU 成本反而上升 20%；audit 後發現 application 加了大量 background scan 用 `ConsistentRead=False`、scan 本身就比 query 貴、cost 飆。

**根因**：team 把「consistency 砍半 = cost 砍半」過度推廣、加了原本不存在的 read site；新 read 即使 eventual 也是 *新 cost*。

**修法**：

1. **Migration scope 內 freeze new read**：consistency 切換期間禁止加新 read 邏輯
2. **Cost monitoring 在切換前 baseline**：對齊原 RCU usage、新 read 出現必須單獨 review
3. **Scan vs Query**：跑 sample data、確認 application 用 Query 不是 Scan（Scan 對所有 partition 讀 / Query 對 partition key 讀）

### Case 5：故障期間 eventual read 還能 work、應變流程沒覆蓋

**徵兆**：us-east-1 partial outage、strong read 開始 timeout、application 切到 fallback；但 fallback 邏輯只 cover「全 region fail」、沒 cover「strong fail / eventual ok」中間狀態；流量打到 fallback 路徑、出乎預期慢。

**根因**：DynamoDB 提供 *partial consistency degradation* — leader replica 不可用時 strong read 失敗、secondary 仍 alive、eventual read 仍可；application 沒設計這個中間狀態的處理。

**修法**：

1. **明示 fallback strategy**：strong read 失敗時 application 端 retry with eventual + warning user「showing potentially stale data due to system degradation」
2. **Circuit breaker per-consistency-level**：strong read circuit 跟 eventual read circuit 分開、避免一邊 fail 拖另一邊
3. **DR drill 覆蓋此 case**：故障演練不只「全失敗 vs 全 work」、要演 *partial degradation*

## Capacity / cost

| 維度                | All strongly consistent             | Mixed（70% eventual + 30% strong）| All eventually consistent      |
| ------------------- | ----------------------------------- | --------------------------------- | ------------------------------ |
| RCU per read        | 1 RCU per 4KB                       | 0.65 RCU per 4KB（avg）            | 0.5 RCU per 4KB                |
| Read latency p99    | 10-15ms                             | 5-10ms                            | 1-5ms                          |
| Cost saving         | baseline                            | ~35%                              | ~50%                           |
| Application complexity | Low                              | Medium（per-site decision）        | Low                            |
| Audit / migration cost | -                                | 2-3 FTE 月 × audit                | 同 mixed                       |
| Cross-AZ failure    | Strong read fail                    | Strong fail, eventual work        | All work                       |

**判讀**：完全 strong 是 *過度保守*、完全 eventual 是 *過度激進*；mixed 是 sweet spot、但 audit 工作量大。

## 整合 / 下一步

### 跟 [PostgreSQL READ COMMITTED → SERIALIZABLE](https://www.postgresql.org/docs/current/transaction-iso.html) 對照

PostgreSQL isolation level migration 也是 consistency axis 變動、但方向相反（弱 → 強）；同樣需要 per-call-site review、application 端可能撞 serialization failure 處理。

### 跟 [Cassandra LOCAL_QUORUM → EACH_QUORUM](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html#tunable-consistency) 對照

Cassandra tunable consistency 是另一個 consistency 獨立軸 case；EACH_QUORUM 跨 DC 需所有 DC quorum、latency 增、availability 降。

### 跟 [Aurora read replica](/backend/01-database/vendors/postgresql/migrate-to-aurora/) 對照

Aurora read replica 也涉 eventual read decision；application 路由策略類似但 mechanism 不同（DNS-based vs API flag）。

### 下一步議題

- **Consistency axis 升級為第 7 維 audit dimension**：累積 PostgreSQL isolation level / Cassandra tunable consistency / Aurora reader endpoint 3-5 個 case 後評估
- **Sub-dimension proposal**：consistency axis 可拆 sub-dimension - read consistency / write consistency / replication lag tolerance / serialization level
- **跟 paradigm 軸的邊界釐清**：CRDT / event sourcing 是 paradigm 還是 consistency model 選擇？

## 相關連結

- 上游 vendor 頁：[DynamoDB](/backend/01-database/vendors/dynamodb/)
- 平行 deep article：[Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/)（Type B drop-in 對照）
- 平行 axis 候選驗證：[Vault → AWS Secrets Manager](/backend/07-security-data-protection/vendors/hashicorp-vault/migrate-to-aws-secrets-manager/)（identity axis 候選）
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/) / [#128 self-aware limitation 第 1 點](/report/data-topology-as-audit-dimension/)（consistency axis 候選驗證、本文是該驗證的 dogfood）
