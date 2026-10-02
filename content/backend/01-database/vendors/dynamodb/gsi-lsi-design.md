---
title: "DynamoDB GSI 與 LSI 設計：access pattern 補位、projection、consistency 跟 DAX 補位"
date: 2026-05-27
description: "GSI / LSI 是 single-table 沒覆蓋的 access pattern 補位、不是萬靈丹；本文涵蓋 projection 在 KEYS_ONLY、INCLUDE 與 ALL 之間的選擇、sparse index、GSI 自己會 hot partition、DAX 讀峰值補位的觸發條件"
weight: 32
tags: ["backend", "database", "dynamodb", "gsi", "lsi", "dax", "deep-article"]
---

這篇整理 [DynamoDB](/backend/01-database/vendors/dynamodb/) 在 single-table design 之上用 GSI 與 LSI 補足主表 PK / SK 查不到的 access pattern：兩種 secondary index 的差別、projection 的選擇、sparse index，以及什麼時候該加 DAX 分擔讀峰值。

每個 GSI 都另外收 storage 與 WCU，GSI 加到 cost 超過 base table 時，常見的成因是主表 PK 沒有依 access pattern 設計，讓原本可以用主表 `Query` 解的查詢都落到 GSI 上；這時該回頭檢查的是主表的 PK 設計，single-table 本身不是成因。

> **DynamoDB workload 適配判讀（基本 4 軸）**：PK 天然均勻 / control plane vs data plane / consistency 可接受 eventual / access pattern 穩定 — 判讀軸詳見 [single-table-design-pattern 開頭 4 軸前置判讀](../single-table-design-pattern/#dynamodb-適用度前置判讀)。本文聚焦 GSI / LSI 補位操作層、是 *已選 DynamoDB + access pattern 已穩定* 的 schema 設計議題。

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

DAX（DynamoDB Accelerator）不是 GSI / LSI 同層方案、不是 DynamoDB 預設配置、是「讀峰值持續高時的補位」。決定加 DAX 之前要先確認觸發條件：

**Lemino 案例公開使用 DAX**：「DAX 是 DynamoDB 讀 cache 的標準解法」、觸發條件是「當讀峰值持續高、加 DAX 減少 DynamoDB 讀次數、降低成本」（熱門節目首播時段、共用 metadata）。

**Capcom 案例沒有公開使用 DAX**：Capcom 的 latency 要求是 single-digit ms，由此可以推論它需要 sub-region cache 或 DAX 這類讀路徑加速、不能單靠 DynamoDB；這是推論，案例本身沒有公開使用 DAX。

**跟 GSI / LSI 的職責分離**：

- GSI / LSI 解「無法用主 PK 查」的問題（access pattern 補位）
- DAX 解「同 query 重複打 DynamoDB 太貴或太慢」的問題（讀路徑加速）
- 兩者不互斥、但解不同問題；不要把 DAX 當 GSI 替代品

**DAX 適用觸發條件**：

- 讀峰值持續高（熱門節目 / 共用 leaderboard / 全平台共享 metadata / read:write ratio > 10:1）
- cache 命中率可預期高（重複讀同一組 key）

**DAX 不適用情境**：

- 寫密集 workload（cache invalidation 開銷 > cache 收益）
- 每次讀都不同 key（cache hit rate 預期 < 50%、加 DAX 等於白花錢）
- read-your-write 場景（DAX 仍是 eventual cache、staleness 視 cache TTL 而定）

## 設計流程

從 access pattern 補位到 DAX 評估的設計流程：標記最小成本路徑、選 LSI 還是 GSI、設計 projection、用 sparse index 縮小索引、驗證 query 走的 index、評估 DAX。

#### 標記最小成本路徑

每個 access pattern 標記能用最便宜路徑解：

- 能用主表 PK/SK 直接 `GetItem` / `Query` → 主表（最便宜）
- 同 PK 內不同 SK 排序 + 需要 strong read → LSI（同 partition、strong）
- 跨 PK 或 base table 已建好 → GSI（額外 storage + WCU）

#### 選 LSI 還是 GSI

LSI 只能在 create table 時定義、不能後加。team 經常踩雷：上線後想加 strongly consistent 索引、發現只能重建 table。建 table 前列完 access pattern、不確定走 GSI 不走 LSI 是保守選擇（GSI 隨時可加可移）。

#### 設計 projection

每個 GSI 單獨設 projection、不要全用 `ALL`：

- query 只要回 key → `KEYS_ONLY`
- query 需要常見 3-5 個欄位 → `INCLUDE`（列出實際 column、storage 跟 query 效率平衡）
- 用 GSI 直接顯示資料（不回 base table） → `ALL`（storage 跟 WCU 都翻倍、慎用）

#### sparse index pattern

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

> **Scope warning**：「storage 節省約 90%」是假設 active order 佔 10% 推算出的通用工程估算、依 active subset 比例變動、case 未揭露 sparse index 具體數字。

#### 驗證 query 走的是哪個 index

```python
response = table.query(
    KeyConditionExpression=Key("GSI1PK").eq("STATUS#active"),
    IndexName="GSI1",
    ReturnConsumedCapacity="INDEXES"  # 看每個 query 走 GSI 還是主表
)
print(response["ConsumedCapacity"])
```

CloudWatch GSI metric：看每個 GSI 的 WCU usage 跟主表的比例；GSI WCU > base table WCU 通常是 GSI 設計需要重新檢查的訊號。

#### 評估 DAX

讀峰值持續高 + cache hit rate 可預期、才加 DAX；不要把 DAX 當預設配置（Lemino 揭露的觸發條件）。先觀察 base 路徑的 read pattern、判斷 cache hit rate 預期值、再決定加 DAX。

**Rollback boundary**：GSI 可隨時刪、但 deletion 是 async 且不可逆；建議先 application 切回 base table query、觀察 1 週再刪 GSI。DAX 可隨時 detach、application 端把 DAX endpoint 換回 DynamoDB endpoint 即可。

## 失敗模式

7 個 production 常見踩雷：

#### GSI 寫入 throttle 拖累主表 write

GSI 用了集中型 PK（如 `STATUS#active` 所有 active order 集中）、單 partition 上限 1000 WCU 撞牆、GSI replication 失敗、主表 write retry、整體 latency 上升。修法：GSI PK 設計獨立 review、不可繼承主表 PK 的均勻假設（base PK 均勻 ≠ GSI PK 均勻）；GSI PK 也要做 [partition key 均勻度判讀](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)。

#### GSI eventual read 餵錯資料

application 用 GSI 讀「user 最新 status」、code 假設 strong 一致；實際 100-500ms staleness 導致 UI 顯示舊狀態。修法：read-your-write 場景改回主表 query（主表支援 strong）、或加 application-side write-through cache。

> **Scope warning**：「100-500ms staleness」具體數字屬通用工程估算、case 未揭露 GSI replication latency 具體 p99 數字。

#### projection ALL 把 cost 翻倍

圖省事所有 GSI 用 `ALL`、實際 query 只需要 3 個 column；storage + WCU 都浪費。修法：每個 GSI 單獨設 projection、`INCLUDE` 列出實際 column；只在「用 GSI 直接顯示資料、不回主表」場景才用 `ALL`。

> **Scope warning**：「cost 翻倍」屬通用工程估算、case 未揭露具體 cost ratio。

#### LSI 用完了才發現要的是 GSI

LSI 上限受 vendor 規格限制（建議 cross-verify AWS doc 當前數字）且建 table 時定、半年後想加 strongly consistent 索引發現要重建 table。修法：建 table 前列完 access pattern、不確定就走 GSI（隨時可加可移）；LSI 留給「明確需要同 PK + strong read」場景。

#### GSI 反向 scan 取代 query

application 用 GSI 做 `Scan` 而非 `Query`、全 GSI 掃過去、cost 跟 latency 都炸。修法：`Scan` 是 *程式碼錯誤訊號*、不是 capacity 不夠；review code 看 GSI 為什麼沒被當 query 路徑用、通常是 GSI PK 設計沒對齊 access pattern。

#### 把 DAX 當預設配置

寫密集 workload / cache hit rate 低的場景加 DAX、cache invalidation 成本超過 cache 收益、cost 上升 latency 沒降。修法：DAX 是「讀峰值持續高」的補位、不是預設（觸發條件來自 Lemino 案例；Capcom 案例沒有公開使用 DAX）；先觀察 read pattern + 評估 cache hit rate 預期、再決定。

#### GSI 的 provisioned capacity 跟 base table 沒有對齊

GSI 繼承 base table 的 capacity mode，而 provisioned mode 下每個 GSI 的 RCU / WCU 與 auto-scaling policy 跟 base table 各自獨立設定。base table 調高了 WCU、或 auto-scaling 只設在 base table 上，GSI 的 WCU 沒有跟上時，GSI 的寫入被 throttle，base table 的寫入也跟著被 throttle。屬通用工程議題、case 未直接揭露具體錯配狀況。

徵兆：

- Base table `ConsumedWriteCapacityUnits` 健康、卻看到 GSI `WriteThrottleEvents` 持續觸發、application 端寫入 latency p99 拉高
- Auto-scaling policy 只設了 base table、GSI 沒設、流量上來時 base table 自動擴、GSI 卻 throttle

修法：

- 建 GSI 時把它的 provisioned RCU / WCU 與 auto-scaling policy 當成獨立決策；GSI 的 provisioned WCU 至少等於 base table 的 WCU
- 流量穩定 workload 把 base + 每個 GSI 都設 auto-scaling、auto-scaling target 對齊
- Spiky workload 改 on-demand 時以 table 為單位切換，GSI 隨 base table 一起變成 on-demand
- CloudWatch alarm 對每個 GSI 獨立設 `WriteThrottleEvents` / `ReadThrottleEvents`、不要只盯 base table
- 詳細 mode 切換時機看 sibling [on-demand vs provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/)

**Anti-recommendation**：access pattern < 3 個、主表 PK 已能覆蓋 → 不要預先建 GSI；GSI 從少到多容易、從多到少要 application 端配合 cutover。

## 容量與觀測

CloudWatch metric：

- 每個 GSI 獨立 `ConsumedReadCapacityUnits` / `ConsumedWriteCapacityUnits`
- GSI 的非同步傳播延遲：官方文件寫正常情況下 base table 的變更在一秒內傳到 GSI、罕見故障時會更久（無 SLA），截至 2026-09 沒有對應的 CloudWatch metric；`ReplicationLatency` 屬 Global Tables 的跨 region 複寫、量不到 GSI。GSI 寫不進去造成的回壓看帶 `GlobalSecondaryIndexName` 維度的 `WriteThrottleEvents`
- DAX：`ItemCacheHits` / `ItemCacheMisses` / `QueryCacheHits` / `QueryCacheMisses`（DAX 沒有現成的 hit rate metric，由這四個自己算）

`ReturnConsumedCapacity` flag：query 時帶 `INDEXES` 看 GSI consumption；`TOTAL` 看 base + GSI 合計、debug 時切換用。

**Cost monitoring**：

- 每個 GSI 都重複收 storage + WCU；GSI 多時 cost 容易超過 base table
- 用 AWS Cost Explorer 按 GSI 維度看、不是只看 table-level 總 cost
- DAX cost 是 instance-hour 計、不是 per-request；只在 read peak 持續高才划算

> **Scope warning**：「GSI 多時 cost 超過 base table」屬通用工程知識、Disney+ / Capcom case 沒揭露具體 GSI cost ratio。

**DAX 觀測重點**：

- 算出的 hit rate < 70% 應重新評估 DAX 是否該存在
- cache size utilization 看 DAX instance class 是否足夠
- 觀察 cache miss 後 fallback 到 DynamoDB 的 latency、確認 DAX 真的減少 base 路徑壓力

> **Scope warning**：「70% hit rate 閾值」屬通用工程估算、case 未揭露具體閾值。

接回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 的 NoSQL index cost section、[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。

## 邊界與整合

### Disney+ / Capcom 的 access pattern 對照

Disney+ 跟 Capcom 是兩種 GSI 用法：

- Disney+ watchlist + 播放進度 + cross-device sync 全用主表 + 少量 GSI、避免 GSI 爆炸；cross-device sync 透過 [Global Tables](/backend/01-database/vendors/dynamodb/global-tables-conflict/) 處理、不是 GSI
- Capcom 玩家 leaderboard / 戰績用 GSI 反向查詢（跨遊戲共用平台、player_id 為 base PK、game_id 為 GSI PK）；leaderboard 是否該走 GSI 還是 Redis sorted set 是另一個取捨

Disney+ 與 Capcom 都 *沒有公開揭露* 具體 GSI 數量、projection 配置、DAX 是否使用；上面兩條裡的 index 配置是依案例公開的 access pattern 所做的通用工程推論。

### Sibling 與 cross-link

- [single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/) — GSI 是 single-table 沒覆蓋的 access pattern 補位
- [partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) — GSI 自己也會 hot partition、GSI PK 設計獨立 review
- [consistency-model-optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/) — GSI 強制 eventual、對應 consistency 軸
- [on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) — GSI 多時 cost 跟 mode 互動
- 替代路由：access pattern 變動頻繁 → 考慮 OpenSearch / Aurora、單純 search 不要拿 GSI 當 inverted index
- [Capcom：Resident Evil / Monster Hunter 在 DynamoDB + EKS 上的遊戲後端](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/)：leaderboard 用 GSI vs Redis sorted set 的選擇；案例沒有公開使用 DAX
- [NTT DOCOMO Lemino：3 個月達 500 萬 MAU 的串流後端](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)：DAX 作為讀峰值補位的案例來源
