---
title: "DynamoDB Partition Key 反模式與 Write Sharding：composite key 修復跟 mode × partition 交叉判讀"
date: 2026-05-27
description: "DynamoDB partition 上限 1000 WCU 是 hot partition 的根因；composite key（event_id + shard suffix）跟 calculated shard（hash % N）兩種修法、mode × partition 在 provisioned / on-demand 不同表現，以及 9.C15 Tixcraft 6750x 擴展的工程細節"
weight: 31
tags: ["backend", "database", "dynamodb", "partition-key", "hot-partition", "write-sharding", "deep-article"]
---

> 本文是 [DynamoDB](/backend/01-database/vendors/dynamodb/) overview 的 implementation-layer deep article。寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

售票網站開賣前一小時把 DynamoDB capacity 從 200 WCU 拉到 5000、心想「容量加 25 倍應該夠」。開賣瞬間還是看到 `ThrottledRequests` 拉警報、CloudWatch 顯示總 capacity 才用了 1500 WCU。打開 partition-level metric 才看到某一個 partition 已經達到 1000 WCU 上限、其他 partition 閒置 — `event_id` 當 PK、單一熱門場次把所有寫入集中到同一個 partition。Capacity 加再多都救不了，因為單 partition 上限是 1000 WCU / 3000 RCU、跟 table 總容量無關。這就是 hot partition 的本質：partition key 設計問題、不是 capacity 不夠。

本文展開 partition key 反模式的識別、composite key / write sharding 兩種修法、mode × partition 在 provisioned / on-demand 下的不同表現、以及 9.C15 拓元 6750x IOPS 擴展案例的工程細節。

> **DynamoDB 適用度前置判讀**：本篇假設 workload 已通過 DynamoDB 適用度 4 軸（PK 天然均勻 / control plane vs data plane / consistency 可接受 eventual / access pattern 穩定）— 詳見 [single-table-design-pattern 開頭 4 軸前置判讀](../single-table-design-pattern/#dynamodb-適用度前置判讀4-軸)、本篇不重複展開。Partition key 反模式是 *已選 DynamoDB 後* 的 schema 修補議題；若 4 軸不成立、改回 SQL 比補 composite key 更合理。

## 核心機制：partition 上限是工程硬天花板

DynamoDB 把 capacity 抽象成 RCU / WCU、但底下仍是物理 partition。理解 partition 的 4 條硬規則：

- **單 partition 上限**：3000 RCU、1000 WCU、10GB storage；超過任一個觸發 partition split
- **總容量公式**：`partition 數量 × 每 partition 上限`、partition 數量由 vendor 自動管理
- **Adaptive Capacity**：跨 partition 重新分配閒置容量、但 *單 partition 仍硬上限*；不解 single-key 集中
- **Splitting on heat**：vendor 偵測 hot partition 後自動 split、有分鐘級延遲；突發流量來不及 split 就先 throttle

`9.C5 Amazon Ads` 揭露同一 frame：「容量 = 每 partition 上限 × partition 數量、最熱 partition saturation 是工程天花板」。Amazon Ads 90M reads/sec 不是把單 partition 推到極限、是 *partition key 設計讓流量散到極多 partition*、每個 partition 都在合理區間。

對應 knowledge card：[hot partition](/backend/knowledge-cards/hot-partition/)、[database-sharding](/backend/knowledge-cards/database-sharding/)。

## Mode × Partition 交叉判讀

Hot partition 在 capacity mode 不同下表現不同、但根因都是 schema。這是 single-table / partition-key / capacity-mode 三篇 deep article 的交叉軸 — mode 切換不解 partition 設計問題、partition 設計也不解 mode 選擇問題。

| 表現面           | Provisioned 模式                                  | On-demand 模式                                                        |
| ---------------- | ------------------------------------------------- | --------------------------------------------------------------------- |
| Throttle 可見性  | `WriteThrottleEvents` 立即可見、CloudWatch 直接抓 | 不顯示 throttle event、表現為 `SuccessfulRequestLatency` p99 突然跳高 |
| Application 表現 | `ProvisionedThroughputExceededException` 立即拋   | timeout / retry 加劇、看起來像「DynamoDB 變慢」                       |
| 工程誤判風險     | 低（exception 明顯）                              | 高（latency spike 容易被誤判成網路 / 應用層 / 下游服務問題）          |
| 解法             | 改 PK schema（composite key / write sharding）    | 改 PK schema（同左、不是切 mode）                                     |

`9.C15 Tixcraft` 警惕段明示這個 frame：「DynamoDB 寫入排隊本身就是隱性限流」— provisioned 看得到、on-demand 看不到，但都是同一個 schema 問題。

**核心 frame**：on-demand 不是 partition key 設計的逃避路徑。看到 on-demand 模式 latency spike 但 throttle 為零，*第一個懷疑就是 hot partition*、不是網路或應用層。

跟 [on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) 共軸閱讀：本篇從 schema 視角切入、那篇從 mode 選擇視角切入、合起來才是完整判讀。

## 修復流程

從 access pattern audit 到 composite key 設計的 5 步流程。

#### Step 1：識別寫入集中的 logical key

審視 access pattern 表、抓出 *寫入集中* 的 key：

- 單一 event / single user 寫入比例 > 10%（如熱門場次售票、bot 帳號）
- 時間 bucket（`PK = date` / `PK = hour`）— 寫入永遠打當下 partition、舊 partition 閒置
- 少數枚舉值（`PK = status` / `PK = country` 但只有 5-10 個值）

`9.C15 Tixcraft` 揭露的具體場景：演唱會某一熱門場次的 `event_id` 為 PK、開賣瞬間 200K 用戶同時搶該場次、所有寫入集中到單一 partition。

#### Step 2：選 shard 數

把單一 logical key 切成 N 個物理 shard。N 的估算邏輯：

```text
單 partition WCU 上限 = 1000
留 20% buffer            = 800
N = 單 logical key 預期峰值 WCU / 800（最小 shard 數）
```

> **Scope warning**：「shard 數 10-100」、「800 WCU 留 buffer」這些具體數字是通用工程估算、9.C15 case *沒有* 揭露 Tixcraft 用幾個 shard。case 揭露的是「composite key 分散」概念跟「IOPS 從 20 衝到 135K」的結果、不是具體 shard 數量。寫進你自己的設計時、shard 數依預期單 logical key 峰值估算、不要照搬本文數字。

#### Step 3：composite key 設計（random shard）

[Composite Partition Key](/backend/knowledge-cards/composite-partition-key/) 把 logical key 加上 random suffix、把 hot logical 值分散到多個 partition：

```python
import random

def write_order(event_id: str, user_id: str, order_data: dict):
    # 寫入端：random suffix 分散到 N shard
    shard = random.randint(0, N - 1)
    pk = f"{event_id}#{shard}"
    sk = f"USER#{user_id}#{timestamp}"
    table.put_item(Item={"PK": pk, "SK": sk, **order_data})
```

讀取時 fan-out 到所有 shard：

```python
def query_event_orders(event_id: str):
    results = []
    for shard in range(N):
        pk = f"{event_id}#{shard}"
        page = table.query(KeyConditionExpression=Key("PK").eq(pk))
        results.extend(page["Items"])
    return results
```

#### Step 4：calculated shard（讓同 user 仍可預測讀取）

random shard 的代價是讀取要 fan-out N 次。當你需要「同 user 寫入分散、但讀取 *該 user* 自己的資料時不要 fan-out」、改用 calculated shard：

```python
import hashlib

def shard_for_user(user_id: str, n: int) -> int:
    h = hashlib.md5(user_id.encode()).hexdigest()
    return int(h, 16) % n

def write_user_event(user_id: str, event_data: dict):
    shard = shard_for_user(user_id, N)
    pk = f"USER#{user_id}#{shard}"
    # 同一 user_id 永遠拿到同一 shard
```

讀單一 user 只 query 一個 shard、讀全平台 user 才 fan-out N 個 shard。

選擇：

- **random shard**：寫入完全均勻、但所有讀路徑都要 fan-out；適合 *flash-sale / 緩衝層*（讀路徑是後端慢消費、不在乎 fan-out latency）
- **calculated shard**：寫入按 hash 均勻、user-level 讀路徑單 shard；適合 *user-facing OLTP*（user 讀自己資料延遲敏感）

#### Step 5：驗證點

- Contributor Insights 看 top-N PK 訪問是否平均分布
- CloudWatch partition-level throttle = 0
- Application 端 read fan-out latency 在預算內

**Rollback boundary**：composite key 寫入端可雙寫舊 + 新 key 一段時間（雙寫窗口）、application read 端 fallback 到舊 PK；不可逆動作只在「移除舊 key」階段。

## 失敗模式

5 個 production 常見踩雷：

#### Case 1：時間序 PK 集中

`PK = date` 或 `PK = hour` — 寫入永遠打當下 partition、舊 partition 閒置。每日凌晨換 partition 時瞬間冷啟動、寫入 latency spike。修法：`date#shard` 把當下 partition 拆 N 個物理 shard、或改用 event-stream pattern（每個 event 獨立 ID 為 PK）。

#### Case 2：bot user 集中

PK = `user_id`、某個 bot 帳號每秒寫 1000 次、單 user_id 達 1000 WCU 上限。修法：

- 偵測高頻 user 後動態加 shard suffix（`user_id#shard0` … `user_id#shardN`）
- 或在 application 層 rate limit、不讓 bot 直接打 DynamoDB

#### Case 3：composite key 但 read 端忘記 fan-out

寫入分散到 100 shard、讀取只 query 一個 shard、結果不完整。修法：讀取必須 N 次 query 並 application 端合併、或建反向 GSI（GSI PK = `event_id`、不加 shard suffix；但 GSI 自己也會 hot partition）。

#### Case 4：shard 數選太多 read fan-out latency 爆

N 過大時讀取 fan-out latency 從 5ms 變 200ms（具體數字隨網路延遲跟並行度變動、9.C15 case 未揭露 Tixcraft 用幾個 shard）。修法：shard 數依「單 logical key 預期峰值 / 800」估算、不是越多越好；read latency 跟寫入分散度是 trade-off。

#### Case 5：on-demand 模式以為不會 hot partition

on-demand 仍受單 partition 1000 WCU 限制、只是 throttling 表現為 latency spike 而非 exception。team 看到「沒有 ThrottledRequests」就以為沒問題、實際 p99 已經從 5ms 跳到 50ms。修法：on-demand 不是 partition key 設計的逃避路徑、依然要做 composite key；觀測上看 `SuccessfulRequestLatency` p99 不只看 throttle。跟 [on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) 共軸閱讀。

**Anti-recommendation**：access pattern 寫入分散自然均勻（如 UUID 為 PK、無 logical hot key），不要預先 sharding；增加 read 端 fan-out 複雜度沒帶來收益。

## 容量與觀測

CloudWatch metric：

- `WriteThrottleEvents` / `ReadThrottleEvents`：按 table 跟 GSI 分；provisioned 模式直接訊號
- `SuccessfulRequestLatency` p99：on-demand 模式下 hot partition 的訊號（throttle 為零但 latency 跳高）
- partition-level metric 透過 Contributor Insights 看，不是 CloudWatch 預設 panel

**Contributor Insights 必開**：top-N partition key by access frequency；每月 cost ~$0.02 per million event、值得開。沒開 Contributor Insights 你看不到 partition-level 分布、只能從總 capacity 跟 throttle 反推。

DynamoDB Streams：可用來抓 hot key debugging — 寫入事件落 Lambda 後統計 PK 頻率。

**Mode × partition 觀測差異**（重申交叉判讀）：

- Provisioned 模式：看 `WriteThrottleEvents`、立即可見
- On-demand 模式：看 `SuccessfulRequestLatency` p99、看 partition-level Contributor Insights、看 application 端 timeout / retry trend

接回 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 的 partition 章節。

## 邊界與整合

### 9.C15 Tixcraft 6750x 擴展的工程拆解

`9.C15 Tixcraft` 揭露的數字：IOPS 從 20 衝到 135K（6750 倍）、6 servers 變 800 servers、總成本 $4200、throttle rate 0.26%。但「6750x 擴展」不是 DynamoDB 自己的魔法、是 *partition key 均勻分散 + 架構解耦* 的組合結果：

- **partition key 均勻**：composite key（`event_id` 加分散 suffix）把單一熱門場次散到多個 partition、每個 partition 都在合理區間（case 揭露概念、未揭露具體 shard 數）
- **架構解耦**：DynamoDB 當 durable queue、後端傳統 server（金流 / 票庫）用自己節奏消費、不被前端 130x 流量拖垮（見 [single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/) 的 durable queue 段）
- **付款層獨立**：付款不是 DynamoDB、是另一層獨立服務、避免搶票流量影響付款

讀者該學的不是「DynamoDB 能撐 6750x」、是「composite key + 架構解耦 + 服務分層」三件事一起做才能撐。

### Sibling 與 cross-link

- [single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/) — PK 設計上游、本篇是 PK 不天然均勻時的補救
- [on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) — capacity mode 對 hot partition 表現的影響、mode × partition 交叉判讀的另一視角
- [gsi-lsi-design](/backend/01-database/vendors/dynamodb/gsi-lsi-design/) — GSI 自己也會 hot partition、GSI PK 設計獨立 review
- Migration playbook：composite key migration 屬「topology re-layout」、寫入需雙軌；對應 [migration playbook methodology](/posts/migration-playbook-methodology/)
- 跟 [Tixcraft 9.C15](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 互引：售票模式的 6750x 擴展細節、composite key 是工程選擇而非 vendor 魔法
- 跟 [Amazon Ads 9.C5](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) 互引：容量 = 每 partition 上限 × partition 數量、最熱 partition saturation 是容量天花板
- 跟 [Lemino 9.C29](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 互引：connection-free scale 的另一面是 partition 設計責任
