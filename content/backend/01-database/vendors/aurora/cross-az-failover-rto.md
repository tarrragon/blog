---
title: "Aurora Cross-AZ Failover：RTO 量測、endpoint routing 與 application reconnect 契約"
date: 2026-05-27
description: "Aurora cross-AZ failover lifecycle（detection / promotion / DNS update）、官方寫的「通常 60 秒內、常常不到 30 秒」RTO、application DNS cache 跟 connection pool 對齊、Standard Chartered 受監管場景為什麼用獨立 cluster 而非 Global Database failover"
weight: 40
tags: ["backend", "database", "aurora", "failover", "rto", "ha", "deep-article"]
---

這篇整理 Aurora 單一 cluster 內 cross-AZ failover 的流程：failover lifecycle 的 detection、promotion 與 DNS update，application 端的 reconnect 契約，量測真實 RTO 的做法，以及 [Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 受監管銀行業務為什麼選獨立 cluster 而非 Global Database failover。Aurora failover 為什麼不需要 data catch-up，在 [Aurora storage architecture](../storage-architecture/)。

Aurora cross-AZ failover 的 RTO 在官方文件的寫法是「通常 60 秒內恢復、常常不到 30 秒」（截至 2026-09），application 端實測常常看到 60-120 秒。落差來自 application 端的 *DNS cache + connection pool + retry policy* 沒有跟 failover 對齊，Aurora 端的 promotion 本身不慢。

## 問題情境

典型觸發場景：DraftKings / Standard Chartered 等級的金融交易服務、AZ-level outage 期間用戶操作不能斷、RTO 預算 < 60 秒、但 application 端看到的 reconnect 行為跟 AWS 文件不一致。

讀者常見的具體疑問：

- 「Failover trigger 後新 connection 還連到舊 primary、為什麼？」
- 「Writer endpoint DNS 切換了、application 還沒重連、什麼時候會切？」
- 「Failover 期間 in-flight transaction 是全 abort 還是部分 commit？」
- 「我手動測 failover RTO 量出 90 秒、AWS 文件講通常 60 秒內、常常不到 30 秒，誰錯？」

進一步問題：失敗模式分布在 *application 端的 connection state*、不只是 Aurora 端的 promotion 流程。Aurora 端的服務恢復在 storage 共享下通常 60 秒內、常常不到 30 秒（官方文件的寫法，不需要等 data catch-up）、但 application reconnect 受 JVM DNS cache、connection pool validation、retry policy 影響、容易把總體 RTO 拉長到 2-3 倍。

對 Standard Chartered 這種受監管銀行業務、failover 還有合規維度：受監管市場資料 *不能跨境複製*、Global Database 在這種場景違反合規、必須用每市場獨立 cluster 的 cross-AZ failover 吸收 RTO 預算。這個 driver 跟一般工程「跨 region failover 更好」的直覺相反。

## 核心機制：failover lifecycle 的 detection、promotion 與 DNS update

Aurora cross-AZ failover 的 first-class concept 是 *failover lifecycle 三段*：detection → promotion → DNS update。每一段有自己的 SLA 跟可調維度。

**Detection（10-15 秒）**：

- AWS 內部 health check 每幾秒檢查 primary writer health
- 連續失敗到一定閾值才 trigger failover（避免 false positive）
- 讀者無法直接調 detection 閾值、是 AWS managed

**Promotion（< 5 秒）**：

- 選 PromotionTier 最低的 read replica 升 primary
- Storage 跨 AZ 共享、replica 升 primary *不需要 data catch-up*（vs 傳統 PostgreSQL streaming replication 要等 WAL apply）
- Promotion 本身極快、是 Aurora storage 設計的直接受益

**DNS update（5-15 秒）**：

- Cluster endpoint / writer endpoint DNS 切到新 primary
- Aurora endpoint DNS TTL 是 5 秒、AWS DNS infrastructure 通常 5-15 秒 propagate 完
- 但 application 端的 DNS cache 可能 cache 更久 — JVM `networkaddress.cache.ttl` 預設 -1（cache forever）時，application 會一直連到 cache 裡的舊 primary IP

**Endpoint 類型跟 failover 行為**：

- **Writer endpoint**：跟著 failover 走、DNS 切到新 primary、application 寫操作用這個
- **Reader endpoint**：load-balance 到所有 replica；failover 期間短暫包含 promoted replica（已升 primary）、reader query 可能打到 primary、分走新 primary 的 CPU 與連線數（PostgreSQL 的 MVCC 下讀取不取寫鎖，不會跟寫入搶鎖）
- **Custom endpoint**：用戶自定 routing rule、failover 期間行為要驗證、不能假設自動跟隨

**跟通用 failover 差在哪**：Aurora 不需要 data catch-up phase、failover 主要瓶頸是 DNS propagation + application reconnect、不是 promotion 本身。傳統 PostgreSQL streaming replication failover 要等 replica WAL catch-up（heavy write 期間可能秒級延遲）、Aurora 在 storage 設計下消除這段等待。

對應 knowledge card：[failover](/backend/knowledge-cards/failover/)、[rto](/backend/knowledge-cards/rto/)、[rpo](/backend/knowledge-cards/rpo/)。

## Step-by-step 配置 / 量測

**Cluster failover 配置**：

```bash
# 確認 cluster 至少有一個跨 AZ replica
aws rds describe-db-clusters \
  --db-cluster-identifier my-cluster \
  --query 'DBClusters[0].DBClusterMembers'

# 設定 PromotionTier（0 最優先、15 最不優先）
aws rds modify-db-instance \
  --db-instance-identifier my-replica-az-b \
  --promotion-tier 0

# 規格較小、不適合接寫入的 replica 設成 tier 15（最不優先升）
aws rds modify-db-instance \
  --db-instance-identifier my-small-reporting-replica \
  --promotion-tier 15
```

**Application 端 JVM 設定**（最常踩雷的點）：

```properties
# JVM 系統 property、預設 -1 = cache forever、必改
networkaddress.cache.ttl=5
networkaddress.cache.negative.ttl=0
```

**Connection pool 設定**（HikariCP 範例）：

```yaml
spring.datasource.hikari:
  maximum-pool-size: 30
  connection-test-query: "SELECT 1"
  validation-timeout: 5000
  max-lifetime: 1800000      # 30 分鐘、強制 recycle connection
  keepalive-time: 30000      # 30 秒檢查 idle connection
  connection-timeout: 30000
```

**Retry policy**：

```java
// 簡化範例、實際用 Resilience4j 或 Failsafe
RetryPolicy<Object> retryPolicy = RetryPolicy.builder()
    .handle(SQLTransientConnectionException.class, SQLNonTransientConnectionException.class)
    .withBackoff(Duration.ofSeconds(1), Duration.ofSeconds(30))
    .withMaxAttempts(5)
    .build();
```

**手動觸發 failover 量測 RTO**：

```bash
# 觸發 failover、記錄時間
START=$(date +%s%3N)
aws rds failover-db-cluster --db-cluster-identifier my-cluster
echo "Failover triggered at $START ms"

# 用 application heartbeat 寫入時間戳
# application 端跑 every-second insert、failover 後第一個成功 insert 的時間 - START = RTO
```

**驗證點**：

- CloudWatch `FailoverEvent` counter > 0（failover 觸發訊號）
- `DatabaseConnections` 在 failover 期間 drop > 50%、之後 spike（reconnect 風暴）
- Application metric「first successful write after failover trigger」< 30 秒

**Rollback boundary**：promotion 不可逆 — 原 primary 變 replica、不會自動 fallback。要切回原 AZ 必須再做一次 failover。

## 故障模式 / 邊界 case

### DNS cache 把 RTO 從 30 秒拉到 120 秒

徵兆：手動 failover 後、CloudWatch `FailoverEvent` 1 秒內出現、但 application log 顯示寫操作 120 秒後才恢復。

原因：JVM `networkaddress.cache.ttl` 預設 `-1`（cache forever）、application JVM 把 writer endpoint DNS 永久 cache 到舊 primary IP；只有 connection pool eviction 或 application restart 才會重新 resolve。

修：

- JVM startup 加 `-Dnetworkaddress.cache.ttl=5`
- 或在 `$JAVA_HOME/lib/security/java.security` 改 `networkaddress.cache.ttl=5`
- Python application 通常沒這問題（DNS resolve per connection）、但要確認 SQLAlchemy 用 `pool_pre_ping=True`

### Connection pool cached connection 全 stale

徵兆：DNS 切換 OK、但 application 寫操作 timeout 10-30 秒後才觸發 reconnect、p99 latency spike。

原因：connection pool 的 cached connection 還指向舊 primary IP、validation 沒開或 timeout 太長、application 拿到 stale connection 才發現 backend gone。

修：

- HikariCP：`connection-test-query: "SELECT 1"` + `validation-timeout: 5000` + `keepalive-time: 30000`
- SQLAlchemy：`pool_pre_ping=True` + `pool_recycle=1800`
- failover 演練後驗證 connection pool 在 30 秒內 evict 完所有 stale connection

### Reader endpoint failover 期間打到新 primary

徵兆：failover 期間 application read query 偶發打到剛升為 primary 的那台、新 primary 在恢復期間多承擔一份讀負載，應該走 replica 的查詢與寫入共用同一台的 CPU 與連線數。

原因：reader endpoint 是 DNS-based load balance 到所有 replica、failover 期間 *短暫* 包含已升 primary 的 replica（DNS propagation 期間 reader 跟 writer endpoint 都指向同一台）。Read query 打到 primary 後分走新 primary 的 CPU 與連線數；PostgreSQL 的 MVCC 下讀取不取寫鎖，負載是它唯一的代價。

修：

- Application 端 read 跟 write data source 拆分、不要假設 reader endpoint 永遠 read-only
- Failover 期間 application 端做 SQL error type 偵測、`read-only transaction` 錯誤觸發 retry
- 用 custom endpoint group 特定 replica、failover 期間 custom endpoint 行為更可控

### In-flight transaction 全 abort

徵兆：failover 期間正在執行的 transaction *全部 abort*、application 看到 `connection reset` 或 `server closed connection`、commit 沒成功。

原因：Aurora failover 不保留 transaction 狀態、所有 in-flight transaction（包括已執行 BEGIN 但還沒 COMMIT 的）全 abort。Application 沒做 idempotent retry 就會丟失 commit。

修：

- 寫操作必須 idempotent（用 idempotency key、application 端做 deduplication）
- 在 application 層做 transaction-level retry、不在 connection 層 retry
- 重要寫入做 *write-then-verify* 模式：commit 後立刻 SELECT 確認、失敗才 retry

### 升為 primary 的 replica 規格太小

徵兆：failover 後寫入 latency 暴漲、CPU 飽和，發現升 primary 的是一台原本只接報表查詢的小規格 replica。

原因：同 cluster failover 只在同一個 region 的 Aurora Replica 之間挑選，順序先看 promotion tier（0 最優先），同 tier 再挑規格最大的；小規格 replica 沒調 tier 就可能被升為 writer。跨 region 的副本屬於另一個 cluster（Global Database 的 secondary cluster），不會被同 cluster failover 升為 primary，跨 region 切換要走 Global Database 的 switchover / failover。

修：

- 規格與 writer 相同的同 region 跨 AZ replica `--promotion-tier 0` 或 `1`
- 小規格或專用於報表的 replica `--promotion-tier 15`（不優先升）
- Multi-AZ deployment 至少配 2 個與 writer 同規格的 replica、分散在不同 AZ

## Standard Chartered 為什麼選獨立 cluster 而非 Global Database

[Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 揭露受監管產業的 failover 設計選擇 — 案例「判讀」段第 1 點：「7 個受監管市場代表 7 個獨立 cluster（資料不能跨境）、容量規劃變成『7 個獨立規劃 × 各自合規門檻』」。

**合規 driver**：

- 受監管市場資料 *不能跨境複製*
- Aurora Global Database 是跨 region async replication、會把資料推到其他 region
- → Global Database 在這種場景 *違反合規*、不是 DR 選項
- 必須用每市場獨立 cluster、各自做 cross-AZ failover、各自吸收 RTO 預算

**工程含義**：

- 每市場 cross-AZ failover RTO < 30 秒、滿足當地監管 RTO 要求
- 跨市場 DR 不靠 Global Database、靠應用層的 *市場切換*（用戶從 A 市場切到 B 市場是業務決策、不是技術 failover）
- 7 個 cluster 各自獨立、operational surface area × 7（parameter group / backup / IAM / observability fan-out）、但合規要求壓倒運維成本

**Fleet 拓樸**：合規驅動的 fleet 設計（7 個受監管市場 = 7 個獨立 cluster）詳見 [Aurora read replica scaling](../read-replica-scaling/) fleet 治理 SSoT 邊界段。本篇只展開 *單 cluster cross-AZ failover* 流程、不展開跨 cluster 拓樸決策。

**scope warning（必明示、case 自承）**：Standard Chartered case 未公開是 PostgreSQL 還是 MySQL、未公開具體 cost 數字、屬「相關 case study」匿名對照。引用時不能擴寫具體 engine。

## 容量與觀測

**核心 metric**：

```text
FailoverEvent           # failover 觸發 counter、> 0 立即通知
DatabaseConnections     # failover 期間 drop、之後 spike
AuroraReplicaLag        # failover 前 replica 是否 caught up
```

**Application 端 metric**：

```text
first_successful_write_after_failover  # 真實 RTO
connection_pool_error_rate              # stale connection 訊號
db_retry_count                          # retry policy 觸發頻率
```

**量測 RTO 流程**：

1. 跑 application 端 every-second heartbeat insert
2. 手動觸發 failover、記錄 trigger 時間戳
3. 從 heartbeat insert log 找 failover 後第一個成功 insert 的時間戳
4. 差值 = 真實 RTO（包含 detection + promotion + DNS + reconnect）

**Alert**：

- `FailoverEvent > 0` 立即通知 on-call
- `DatabaseConnections` 5 分鐘內 drop > 50% 警告 stale connection
- `db_retry_count` 短期內 spike 警告 reconnect 風暴

**Failover 演練頻率**：

- Non-critical workload：每季一次 planned failover drill
- 受監管產業（Standard Chartered 類）：每月一次、有合規 sign-off 記錄
- 重大版本升級前必跑一次

**回路徑**：[8.x incident response](/backend/08-incident-response/) failover playbook、[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 判斷 reconnect-bound vs query-bound。

## 邊界與整合 / 下一步

**同 vendor 的其他文章**：

- [Aurora storage architecture](../storage-architecture/) — 理解為什麼 Aurora failover 不需要 data catch-up（storage 跨 AZ 共享）
- [Aurora read replica scaling](../read-replica-scaling/) — replica 升 primary 流程跟 fleet 治理 SSoT
- [Aurora Global Database](../global-database-multi-region/) — 跨 region failover RTO 不同數量級（2-15 分鐘 vs cross-AZ 通常 60 秒內）

**Migration playbook**：

- [PostgreSQL / MySQL → Aurora](../migrate-from-self-managed-pg-mysql/) — HA redesign 是 operational redesign 主項、從 Patroni / Orchestrator 切到 Aurora cluster endpoint

**1.x 章節互引**：

- [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) — failover 期間 in-flight transaction abort 對 application 契約的影響
- [8.x incident response](/backend/08-incident-response/) — failover decision log

**何時不用本文**：non-critical workload、RTO 預算 > 5 分鐘、Multi-AZ 預設配置足夠時可跳過。

## 相關連結

- [Aurora vendor overview](/backend/01-database/vendors/aurora/)
- [Failover 卡片](/backend/knowledge-cards/failover/) — 概念基底
- [RTO 卡片](/backend/knowledge-cards/rto/) — RTO 量測判讀
- [Vendor 深度技術文章方法論](/posts/vendor-deep-article-methodology/) — vendor 深度文章從問題情境、核心機制、操作流程、失敗模式、容量與觀測到邊界與整合的寫法
- 官方：[Aurora high availability](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html)
