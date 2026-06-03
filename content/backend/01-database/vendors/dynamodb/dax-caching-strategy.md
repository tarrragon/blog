---
title: "DynamoDB DAX 快取策略：cluster 架構、item/query cache、write-through 與 invalidation 邊界"
date: 2026-06-02
description: "DAX 不是「加上去就變快」的開關；本文展開 DAX cluster 架構、item cache vs query cache 兩種快取、write-through 一致性語意、query cache 只靠 TTL 失效的陷阱，以及 strongly consistent read 繞過 cache 的邊界，含 Lemino 讀峰值補位 case fact 與 gsi-lsi-design 的 SSoT 切分"
weight: 36
tags: ["backend", "database", "dynamodb", "dax", "cache", "deep-article"]
---

> 本文是 [DynamoDB](/backend/01-database/vendors/dynamodb/) overview 的 implementation-layer deep article。寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

熱門節目首播時段、application 對同一批 metadata item 的讀取 latency p99 從 5ms 尖到 40ms、下游 timeout 連鎖。team 加了 DAX、p99 壓回個位數毫秒。三個月後另一個 service 也「照抄」加 DAX、結果 cost 上升、latency 沒降 — 那個 service 是寫密集、每次讀的 key 都不同、cache hit rate 不到 20%。同一個工具、在一個 workload 壓回 p99 延遲、在另一個只增加成本卻不降延遲。DAX 的價值取決於 read pattern 跟一致性需求是否匹配。本文展開 DAX 的 cluster 架構、兩種快取的不同失效語意、以及 write-through 跟 strongly consistent read 的邊界。

> **DAX 觸發條件 SSoT**：DAX 「該不該存在」的觸發條件（讀峰值持續高 / cache hit rate 可預期 / read:write ratio 高）主寫於 [gsi-lsi-design 的 DAX 段](/backend/01-database/vendors/dynamodb/gsi-lsi-design/#dax-作為讀峰值補位)、含 `9.C29 Lemino` case fact 跟 `9.C19 Capcom` derive 分層。本文承接「已決定要用 DAX」之後的機制、配置與失效邊界、不重複展開觸發判讀。

## 核心機制：DAX cluster 與兩種快取

DAX（DynamoDB Accelerator）是 DynamoDB 前面的 in-memory write-through cache、提供 microsecond 級讀取（DynamoDB 本身是 single-digit ms）。它 API 相容 — application 把 DynamoDB client 換成 DAX client、API call 不變、讀寫自動經過 cache 層。

**cluster 拓樸**：

- 一個 DAX cluster 由多個 node 組成、一個 primary（接受寫）+ 多個 read replica
- 跨多 AZ 部署、primary 故障時 replica 接手
- application 透過 DAX endpoint 連 cluster、SDK 自動分散讀取到 replica

**兩種快取、不同生命週期**：

| 快取類型    | 內容                                  | 寫入如何影響                            | 失效方式                 |
| ----------- | ------------------------------------- | --------------------------------------- | ------------------------ |
| Item cache  | `GetItem` / `BatchGetItem` 的單筆結果 | write-through 寫入時同步更新對應 item   | item TTL + write-through |
| Query cache | `Query` / `Scan` 的結果集             | 單筆 write *不會* 失效對應 query 結果集 | 只靠 query TTL           |

這張表的第二列是 DAX 最常被誤解的點：**query cache 不會因為底層某筆 item 被改而失效**。item cache 走 write-through、寫入時會更新；但 query cache 存的是「整個結果集」、DAX 無法知道某筆新寫入是否該進某個已快取的 query 結果、所以 query cache 只靠 TTL 過期。這代表 query 結果可能 stale 到一個 TTL 週期。

> **Scope warning**：「item cache 預設 TTL 5 分鐘」、「query cache 預設 TTL 5 分鐘」這些預設值屬 AWS vendor 規格、可在 cluster 設定調整、實作時 cross-verify 官方 doc。本文不含 production case 揭露的 DAX TTL 配置數字。

對應 knowledge card：[cache-invalidation](/backend/knowledge-cards/cache-invalidation/)、[write-through-cache](/backend/knowledge-cards/write-through-cache/)、[ttl](/backend/knowledge-cards/ttl/)、[cache-hit-rate](/backend/knowledge-cards/cache-hit-rate/)。

## 一致性與 invalidation 邊界

DAX 的一致性語意是它跟「一般 cache-aside」最大的差別、也是踩雷集中區。

**write-through 的保證範圍**：

寫入經過 DAX 時、DAX 先寫 DynamoDB、成功後更新自己的 item cache。所以「寫完馬上用 `GetItem` 讀同一筆」、在 *同一個 DAX node* 上能讀到新值。但這不是 strong consistency — 多 node cluster 下、寫入只更新 primary 與被路由到的 node、其他 read replica 的 item cache 仍可能 stale 到 TTL。

**strongly consistent read 繞過 cache**：

DAX 只服務 eventually consistent read。application 若要求 strongly consistent read（`ConsistentRead=True`）、DAX 直接 pass through 到 DynamoDB、不經 cache、也享受不到 microsecond latency。這是設計上的取捨 — DAX 換 latency 的代價是放棄 strong consistency。read-your-write 嚴格場景不能靠 DAX。

**query cache stale 的真實後果**：

application 用 `Query` 列「某 user 的 active order」、結果被 query cache 快取；user 新建一筆 order、item cache 更新了該筆 item、但 *列表 query 的 cache 沒失效*、user 重整頁面在 TTL 內看不到新訂單。修法不是調 DAX、是判斷「這個 query 能不能接受 TTL 內 stale」— 不能接受的、該 query 不要走 DAX（直接打 DynamoDB）、或縮短該類 query 的 TTL。

> **Scope warning**：上述一致性語意屬 DAX vendor 規格 + 通用 cache 工程知識、非 production case 揭露；實際 staleness 視 cluster node 數、TTL 配置與讀寫分布而定。

## 操作流程

從 read pattern 評估到上線的 6 步流程。

#### Step 1：確認 read pattern 適配

在加 DAX 前、用 CloudWatch 看目標 table 的 read:write ratio 跟 read 的 key 重複度：

- read:write 高（讀遠多於寫）+ 重複讀同一組 key → 適合
- 寫密集 / 每次讀不同 key / 大量 strongly consistent read → 不適合（回頭看 [gsi-lsi-design DAX 觸發條件](/backend/01-database/vendors/dynamodb/gsi-lsi-design/#dax-作為讀峰值補位)）

#### Step 2：cluster sizing

```text
node 數 = 讀峰值 throughput / 單 node 容量 + 1（容錯餘量）
node class = 依 working set 大小選（cache 要能裝下熱資料）
```

跨至少 2 個 AZ、確保 primary 故障有 replica 接手。

#### Step 3：application 切換 client

```python
import amazondax
# 原本：dynamodb = boto3.resource("dynamodb")
dax = amazondax.AmazonDaxClient.resource(endpoint_url="dax://my-cluster.xxx.dax-clusters.region.amazonaws.com")
table = dax.Table("orders")
# API 不變、讀寫自動經過 DAX
response = table.get_item(Key={"PK": "ORDER#123", "SK": "META"})
```

#### Step 4：分流 strongly consistent read

```python
# 需要 strong 的讀直接走 DynamoDB、不要走 DAX
ddb_table.get_item(Key=..., ConsistentRead=True)   # 繞過 cache
# 可接受 eventual 的讀走 DAX
dax_table.get_item(Key=...)                          # 走 cache
```

application 要明確區分哪些讀路徑能接受 stale、哪些不能；不能接受的不走 DAX。

#### Step 5：設定 TTL 與監控 hit rate

依資料變動頻率設 item / query cache TTL：變動慢的 metadata 可設長 TTL、變動快的設短或不快取。上線後盯 `CacheHitRate`。

#### Step 6：驗證點

```python
# 驗證 hit rate 達預期、確認 DAX 真的減少 DynamoDB 讀
# CloudWatch: DAX CacheHits / (CacheHits + CacheMisses)
# 同時看 DynamoDB ConsumedReadCapacityUnits 是否下降
```

**Rollback boundary**：DAX 可隨時 detach — application 端把 DAX endpoint 換回 DynamoDB endpoint 即可、無資料遷移；DAX 只是讀路徑加速層、不持有唯一資料。

## 失敗模式

production 常見的 5 個踩雷：

#### Case 1：把 DAX 當預設配置

寫密集 / 低 hit rate workload 加 DAX、invalidation 開銷 + cluster 成本 > cache 收益。修法：先確認 read pattern 適配（Step 1）、DAX 是讀峰值補位不是預設（觸發條件 SSoT 在 gsi-lsi-design）。

#### Case 2：以為 query cache 會即時反映寫入

寫入後列表 query 在 TTL 內看不到新資料、被當成 bug 長時間誤查。修法：理解 query cache 只靠 TTL 失效（不是 bug 是設計）；強一致列表需求的 query 不走 DAX、或縮短 TTL。

#### Case 3：strongly consistent read 全走 DAX 還抱怨不快

application 全程 `ConsistentRead=True`、DAX 全部 pass through、等於沒裝 DAX 還多付 cluster 錢。修法：分流 — strong read 直接打 DynamoDB、eventual read 才走 DAX。

#### Case 4：cluster 單 AZ / 單 node

省成本只開單 node、primary 故障時讀路徑整個失效、回退到 DynamoDB 瞬間流量尖峰。修法：跨 2+ AZ、primary + replica；DAX 故障的 fallback 路徑（直連 DynamoDB）要先測過。這個 Case 的失敗代價跟其他 Case 不對稱 — 其餘 Case 多是成本浪費或延遲沒降、detach DAX 即可回復；單 AZ / 單 node 故障是讀路徑硬中斷、回退瞬間把原本被 cache 吸收的讀峰值全打回 DynamoDB、若 base table 的 RCU 或 on-demand burst 餘量沒預留、會引發 throttling 連鎖。回退路徑要按「DAX 全失效時的讀峰值」預估 DynamoDB 側容量、而非平時被 cache 削減後的讀量。

#### Case 5：working set 超過 cache 容量

熱資料超過 node memory、cache 不斷 evict、hit rate 掉到沒意義。修法：依 working set 選 node class、或縮小快取範圍（只快取真正熱的 access pattern）。

**Anti-recommendation**：read:write ratio 低、或 cache hit rate 預期 < 50% 的 workload、不要上 DAX；application 端的 request-level cache 或根本不快取可能更划算。DAX 是 cluster 常駐成本（instance-hour 計）、只在讀峰值持續高才回本。

## 容量與觀測

CloudWatch metric：

- `CacheHits` / `CacheMisses` / 算出 `CacheHitRate` — 核心健康指標
- `ItemCacheHits` / `QueryCacheHits` — 分辨兩種快取各自的命中
- `CPUUtilization` / `EvictedSize` — node 是否過載、cache 是否頻繁 evict
- DynamoDB 端 `ConsumedReadCapacityUnits` — 確認 DAX 真的削減了 base 讀取

**判讀**：

- `CacheHitRate` < 70% — 重新評估 DAX 是否該存在、或快取範圍是否該收窄
- `EvictedSize` 持續高 — working set 超過 cache 容量、要加大 node class
- DynamoDB read capacity 沒因 DAX 下降 — read pattern 不適配、DAX 沒發揮作用

> **Scope warning**：「70% hit rate 閾值」屬通用工程估算、非 case 揭露；實際閾值依 cost 結構與 latency 目標調整。

接回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。

## 邊界與整合

### DAX vs application-side cache vs ElastiCache

DAX 不是唯一的 DynamoDB 讀加速方案。三者責任不同：

- **DAX**：DynamoDB 專屬、API 相容、write-through、零 application cache 邏輯；綁 DynamoDB
- **application-side cache**（如 in-process LRU）：最低延遲、但每個 instance 各自一份、一致性難管
- **ElastiCache（Redis / Valkey）**：通用 cache、可跨資料源、但要自己寫 cache-aside 邏輯與 invalidation

當快取需求超出單一 DynamoDB table（跨資料源聚合 / 需要 Redis 資料結構如 sorted set leaderboard）、回 [02 快取模組](/backend/02-cache-redis/) 評估 ElastiCache；DAX 最適配的情境是「純 DynamoDB 讀加速、且不想自行維護 cache 邏輯」。

### Sibling 與 cross-link

- [gsi-lsi-design](/backend/01-database/vendors/dynamodb/gsi-lsi-design/) — DAX 觸發條件 SSoT（讀峰值補位 / Lemino case fact / Capcom derive）在該篇、本篇承接機制層
- [on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) — DAX 削減 base 讀取後、provisioned RCU 規劃要重算
- [consistency-model-optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/) — strongly consistent read 繞過 DAX、對應 read 一致性軸
- [partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) — DAX 不解 hot partition、寫熱點仍打到 DynamoDB
- 替代路由：跨資料源快取 / Redis 資料結構需求 → [02 快取模組](/backend/02-cache-redis/) ElastiCache
- 跟 [Lemino 9.C29](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 互引：DAX 讀峰值補位的 case fact
