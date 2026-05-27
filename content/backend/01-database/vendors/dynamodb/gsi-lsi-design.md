---
title: "DynamoDB GSI 與 LSI 設計：access pattern 補位、projection、consistency 跟 DAX 補位"
date: 2026-05-27
description: "GSI / LSI 是 single-table 沒覆蓋的 access pattern 補位、不是萬靈丹；本文涵蓋 projection 三型選擇、sparse index、GSI 自己會 hot partition、DAX 讀峰值補位的觸發條件（含 Capcom 是 derive vs Lemino 是 case fact 的分層）"
weight: 32
tags: ["backend", "database", "dynamodb", "gsi", "lsi", "dax", "deep-article"]
---

> 本文是 [DynamoDB](/backend/01-database/vendors/dynamodb/) overview 的 implementation-layer deep article。寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

single-table design 上線後第三個月、PM 提了三個新 query 需求：「依商品分類查訂單」、「依 status 查 user」、「依時間 range 取最近活動」。team 第一反應是加 GSI、結果 GSI 從 1 個變 6 個、cost 跟 latency 一起上升。打開 AWS Cost Explorer 一看、GSI 的 storage + WCU 合計已經超過 base table。這時 team 開始懷疑「single-table 是不是錯了」— 那是 *誤判*。GSI 多到 cost 超過 base table 通常是 *主 PK 沒設計好*、不是 single-table 錯。本文展開 GSI / LSI 的正確補位、projection 的三型選擇、sparse index、以及 DAX 作為讀峰值補位的觸發條件。

## 核心機制：GSI vs LSI 的工程差異

DynamoDB 的兩種 secondary index 解的問題不同：

| 屬性        | GSI（Global Secondary Index）           | LSI（Local Secondary Index）     |
| ----------- | --------------------------------------- | -------------------------------- |
| Partition   | 獨立 partition、可選新 PK + SK          | 同 base table partition、同 PK   |
| 建立時機    | 隨時可加 / 移除                         | 只能在 create table 時定義       |
| Consistency | 只支援 eventual read                    | 支援 strongly consistent read    |
| Capacity    | 獨立 RCU/WCU、按 base 主表 write 同步收 | 共享 base table capacity         |
| 數量上限    | vendor 規格、需 cross-verify AWS doc    | vendor 規格、需 cross-verify     |
| 適用場景    | 跨 PK 查詢、需求變動                    | 同 PK 內不同 SK + 需 strong read |

> **Scope warning**：「LSI 數量上限 5 個」、「GSI 數量上限 20」這些具體數字屬 vendor 規格、需在實作時 cross-verify AWS doc 當前數字、本文 case（Disney+ / Capcom / Lemino）沒揭露具體 index 數量。

**Projection type** 決定 GSI 儲存哪些 attribute：

- `KEYS_ONLY`：只存 PK + SK + base key、最省 storage、但讀取後通常還要回 base table 撈 attribute
- `INCLUDE`：除了 key、再存指定的 attribute；常用 sweet spot、storage 跟 query 效率平衡
- `ALL`：複製 base table 所有 attribute；最方便、最貴

讀路徑差異：

- GSI eventual read：跨 partition、不支援 strong；base table write → GSI replication 通常 < 1s 但無 SLA
- LSI strong read：同 partition quorum 內成立、read-your-write 場景適用

對應 knowledge card：[hot partition](/backend/knowledge-cards/hot-partition/)、[consistency level](/backend/knowledge-cards/consistency-level/)。

## DAX 作為讀峰值補位

DAX（DynamoDB Accelerator）不是 GSI / LSI 同層方案、不是 DynamoDB 預設配置、是「讀峰值持續高時的補位」。寫進你的設計前先看觸發條件：

**`9.C29 Lemino` 揭露**（case fact）：「DAX 是 DynamoDB 讀 cache 的標準解法」、觸發條件是「當讀峰值持續高、加 DAX 減少 DynamoDB 讀次數、降低成本」（熱門節目首播時段、共用 metadata）。Lemino 是 case 直接揭露使用 DAX。

**`9.C19 Capcom` 是判讀層 derive、不是 case fact**：原 finding 從「single-digit ms」latency 反推 Capcom 必須用 sub-region cache + DynamoDB DAX、不能單靠 DynamoDB；但 `9.C19` case *沒有公開揭露* 使用 DAX。引用 Capcom 時要明示「DAX 是作者判讀層推論、Capcom 沒公開使用」、避免把推論寫成 case 揭露。

**跟 GSI / LSI 的職責分離**：

- GSI / LSI 解「無法用主 PK 查」的問題（access pattern 補位）
- DAX 解「同 query 重複打 DynamoDB 太貴或太慢」的問題（讀路徑加速）
- 兩者不互斥、但解不同問題；不要把 DAX 當 GSI 替代品

**DAX 適用觸發條件**：

- 讀峰值持續高（熱門節目 / 共用 leaderboard / 全平台共享 metadata / read:write ratio > 10:1）
- cache 命中率可預期高（重複讀同一組 key）

**DAX 不適用情境**：

- 寫密集 workload（cache invalidation 開銷 > cache 收益）
- 每次讀都不同 key（cache hit rate < 30%、加 DAX 等於白花錢）
- read-your-write 場景（DAX 仍是 eventual cache、staleness 視 cache TTL 而定）

## 設計流程

從 access pattern 補位到 DAX 評估的 6 步流程。

#### Step 1：標記最小成本路徑

每個 access pattern 標記能用最便宜路徑解：

- 能用主表 PK/SK 直接 `GetItem` / `Query` → 主表（最便宜）
- 同 PK 內不同 SK 排序 + 需要 strong read → LSI（同 partition、strong）
- 跨 PK 或 base table 已建好 → GSI（額外 storage + WCU）

#### Step 2：選 LSI 還是 GSI

LSI 只能在 create table 時定義、不能後加。team 經常踩雷：上線後想加 strongly consistent 索引、發現只能重建 table。建 table 前列完 access pattern、不確定走 GSI 不走 LSI 是保守選擇（GSI 隨時可加可移）。

#### Step 3：projection 設計

每個 GSI 單獨設 projection、不要全用 `ALL`：

- query 只要回 key → `KEYS_ONLY`
- query 需要常見 3-5 個欄位 → `INCLUDE`（列出實際 column、storage 跟 query 效率平衡）
- 用 GSI 直接顯示資料（不回 base table） → `ALL`（storage 跟 WCU 都翻倍、慎用）

#### Step 4：sparse index pattern

GSI PK 只在某 attribute 存在時填、自動「只索引子集」、節省 storage：

```python
def write_order(order_id: str, status: str):
    item = {"PK": f"ORDER#{order_id}", "SK": "META", "status": status}
    # sparse index: 只有 active order 進 GSI
    if status == "active":
        item["GSI1PK"] = "STATUS#active"
        item["GSI1SK"] = order_id
    table.put_item(Item=item)
```

GSI1 只索引 active order、archive order 不進 GSI。當 active order 是 10%、storage 節省約 90%。

> **Scope warning**：「50-90% storage 節省」具體節省比例屬通用工程估算、依 active subset 比例變動、case 未揭露 sparse index 具體數字。

#### Step 5：驗證點

```python
response = table.query(
    KeyConditionExpression=Key("GSI1PK").eq("STATUS#active"),
    IndexName="GSI1",
    ReturnConsumedCapacity="INDEXES"  # 看每個 query 走 GSI 還是主表
)
print(response["ConsumedCapacity"])
```

CloudWatch GSI metric：看每個 GSI 的 WCU usage 跟主表的比例；GSI WCU > base table WCU 通常是設計訊號。

#### Step 6：DAX 評估

讀峰值持續高 + cache hit rate 可預期、才加 DAX；不要把 DAX 當預設配置（Lemino 揭露的觸發條件）。先觀察 base 路徑的 read pattern、判斷 cache hit rate 預期值、再決定加 DAX。

**Rollback boundary**：GSI 可隨時刪、但 deletion 是 async 且不可逆；建議先 application 切回 base table query、觀察 1 週再刪 GSI。DAX 可隨時 detach、application 端把 DAX endpoint 換回 DynamoDB endpoint 即可。

## 失敗模式

6 個 production 常見踩雷：

#### Case 1：GSI 寫入 throttle 拖累主表 write

GSI 用了集中型 PK（如 `STATUS#active` 所有 active order 集中）、單 partition 上限 1000 WCU 撞牆、GSI replication 失敗、主表 write retry、整體 latency 上升。修法：GSI PK 設計獨立 review、不可繼承主表 PK 的均勻假設（base PK 均勻 ≠ GSI PK 均勻）；GSI PK 也要做 [partition key 均勻度判讀](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)。

#### Case 2：GSI eventual read 餵錯資料

application 用 GSI 讀「user 最新 status」、code 假設 strong 一致；實際 100-500ms staleness 導致 UI 顯示舊狀態。修法：read-your-write 場景改回主表 query（主表支援 strong）、或加 application-side write-through cache。

> **Scope warning**：「100-500ms staleness」具體數字屬通用工程估算、case 未揭露 GSI replication latency 具體 p99 數字。

#### Case 3：projection ALL 把 cost 翻倍

圖省事所有 GSI 用 `ALL`、實際 query 只需要 3 個 column；storage + WCU 都浪費。修法：每個 GSI 單獨設 projection、`INCLUDE` 列出實際 column；只在「用 GSI 直接顯示資料、不回主表」場景才用 `ALL`。

> **Scope warning**：「cost 翻 3 倍」具體數字屬通用工程估算、case 未揭露具體 cost ratio。

#### Case 4：LSI 用完了才發現要的是 GSI

LSI 上限受 vendor 規格限制（建議 cross-verify AWS doc 當前數字）且建 table 時定、半年後想加 strongly consistent 索引發現要重建 table。修法：建 table 前列完 access pattern、不確定就走 GSI（隨時可加可移）；LSI 留給「明確需要同 PK + strong read」場景。

#### Case 5：GSI 反向 scan 取代 query

application 用 GSI 做 `Scan` 而非 `Query`、全 GSI 掃過去、cost 跟 latency 都炸。修法：`Scan` 是 *程式碼錯誤訊號*、不是 capacity 不夠；review code 看 GSI 為什麼沒被當 query 路徑用、通常是 GSI PK 設計沒對齊 access pattern。

#### Case 6：把 DAX 當預設配置

寫密集 workload / cache hit rate 低的場景加 DAX、cache invalidation 成本超過 cache 收益、cost 上升 latency 沒降。修法：DAX 是「讀峰值持續高」的補位、不是預設（Lemino 揭露的觸發條件、Capcom 是 derive 不是 case fact）；先觀察 read pattern + 評估 cache hit rate 預期、再決定。

**Anti-recommendation**：access pattern < 3 個、主表 PK 已能覆蓋 → 不要預先建 GSI；GSI 從少到多容易、從多到少要 application 端配合 cutover。

## 容量與觀測

CloudWatch metric：

- 每個 GSI 獨立 `ConsumedReadCapacityUnits` / `ConsumedWriteCapacityUnits`
- `ReplicationLatency`：GSI async replication 延遲、p99 通常 < 1s（無 SLA）
- DAX：`CacheHits` / `CacheMisses` / `CacheHitRate`、`ItemCacheHits` / `QueryCacheHits`

`ReturnConsumedCapacity` flag：query 時帶 `INDEXES` 看 GSI consumption；`TOTAL` 看 base + GSI 合計、debug 時切換用。

**Cost monitoring**：

- 每個 GSI 都重複收 storage + WCU；GSI 多時 cost 容易超過 base table
- 用 AWS Cost Explorer 按 GSI 維度看、不是只看 table-level 總 cost
- DAX cost 是 instance-hour 計、不是 per-request；只在 read peak 持續高才划算

> **Scope warning**：「GSI 多時 cost 超過 base table」屬通用工程知識、`9.C27 Disney+` / `9.C19 Capcom` case 沒揭露具體 GSI cost ratio。

**DAX 觀測重點**（新增）：

- `CacheHitRate` < 70% 應重新評估 DAX 是否該存在
- cache size utilization 看 DAX instance class 是否足夠
- 觀察 cache miss 後 fallback 到 DynamoDB 的 latency、確認 DAX 真的減少 base 路徑壓力

> **Scope warning**：「70% hit rate 閾值」屬通用工程估算、case 未揭露具體閾值。

接回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 的 NoSQL index cost section、[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。

## 邊界與整合

### Disney+ / Capcom 的 access pattern 對照

`9.C27 Disney+` 跟 `9.C19 Capcom` 是兩種 GSI 用法：

- Disney+ watchlist + 播放進度 + cross-device sync 全用主表 + 少量 GSI、避免 GSI 爆炸；cross-device sync 透過 [Global Tables](/backend/01-database/vendors/dynamodb/global-tables-conflict/) 處理、不是 GSI
- Capcom 玩家 leaderboard / 戰績用 GSI 反向查詢（跨遊戲共用平台、player_id 為 base PK、game_id 為 GSI PK）；leaderboard 是否該走 GSI 還是 Redis sorted set 是另一個取捨

兩個 case 都 *沒有公開揭露* 具體 GSI 數量、projection 配置、DAX 是否使用。引用 case 時要分層 — 概念是 case 揭露、實作數字是通用工程估算。

### Sibling 與 cross-link

- [single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/) — GSI 是 single-table 沒覆蓋的 access pattern 補位
- [partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) — GSI 自己也會 hot partition、GSI PK 設計獨立 review
- [consistency-model-optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/) — GSI 強制 eventual、對應 consistency 軸
- [on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) — GSI 多時 cost 跟 mode 互動
- 替代路由：access pattern 變動頻繁 → 考慮 OpenSearch / Aurora、單純 search 不要拿 GSI 當 inverted index
- 跟 [Capcom 9.C19](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) 互引：leaderboard 用 GSI vs Redis sorted set 的選擇；DAX 是 derive 不是 case fact、引用要明示
- 跟 [Lemino 9.C29](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 互引：DAX 作為讀峰值補位的 case 揭露
