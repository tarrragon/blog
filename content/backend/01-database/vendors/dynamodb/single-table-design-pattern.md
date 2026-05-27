---
title: "DynamoDB Single-Table Design：從適用度前置判讀到 access pattern 反推 PK/SK"
date: 2026-05-27
description: "DynamoDB single-table 設計不是「資料表越少越好」，而是 access pattern 反推 PK/SK 跟 GSI；本文先做 DynamoDB 適用度 4 軸前置判讀（PK 天然均勻 / control plane vs data plane / consistency / access pattern 穩定），再展開設計流程、failure modes 與 durable queue 正向用例"
weight: 30
tags: ["backend", "database", "dynamodb", "single-table-design", "access-pattern", "deep-article"]
---

> 本文是 [DynamoDB](/backend/01-database/vendors/dynamodb/) overview 的 implementation-layer deep article。寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

team 用 RDBMS 設計思維建多個 DynamoDB table（`user` / `order` / `order_item`）跑了一季、第二季開始撞「每個 query 要打 2-3 個 table、application 端拼接邏輯爆炸、latency 跟 cost 線性上升」。最直覺的補救是再加 GSI、結果 GSI 數量超過 5 個還是抓不到 access pattern。這時 team 通常開始問「DynamoDB 怎麼 join」— 那是 *誤問*。DynamoDB 不做 join，要嘛把相關 entity 放同 PK 用 SK 前綴區分（single-table design），要嘛這個 workload 根本不該用 DynamoDB。本文先回答後者（DynamoDB 適用度前置判讀），再展開前者（single-table 設計流程）。

## DynamoDB 適用度前置判讀（4 軸）

進到 single-table 設計細節之前要先判讀 workload 是否在 DynamoDB 適用區。下面 4 個維度同時成立、single-table 才有意義；任一條不成立、改回 SQL / 多 vendor 組合可能更便宜。9 個 production case（Zoom / Disney+ / Capcom / PayPay / Tixcraft / Lemino / Amazon Ads / Genesys / Zomato）跨 case 重複揭露這 4 軸是適用度的真實邊界。

### 軸 1：Partition key 是否天然均勻

DynamoDB 容量 = 每 partition 上限 × partition 數量、最熱 partition saturation 就是 workload 的天花板。`meeting_id`（Zoom）/ `player_id`（Capcom）/ `message_id`（PayPay）/ `user_id`（Disney+）這類 ID 天然散布、不會集中在少數 partition；反之 `event_id`（Tixcraft 售票）/ `date`（時間序）/ `status`（少數枚舉值）這類 PK 天然不均勻、要 composite key 修補才能 single-table。修補成本見 [partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)。

`9.C18 Zoom`、`9.C19 Capcom`、`9.C26 PayPay`、`9.C27 Disney+` 4 個 case 都揭露 partition key 天然均勻是 DynamoDB 「能撐」的前提之一。

### 軸 2：Workload 是 control plane 還是 data plane

DynamoDB 適合存 metadata / state，實際大流量（影音串流 / 大型 BLOB / 全文搜尋）走 CDN / WebRTC / object store。`9.C18 Zoom` 把媒體串流放 P2P + edge servers、DynamoDB 只承擔會議 metadata；`9.C27 Disney+` 把 content 放 S3 + CDN、DynamoDB 只承擔 watchlist + 播放進度；`9.C19 Capcom` 把即時遊戲邏輯放 EKS、DynamoDB 處理持久狀態。讀者該問的不是「DynamoDB 能撐多大流量」、是「我的系統哪一層該放 DynamoDB」。

如果 workload 是 data plane（單筆 payload 上 MB、要做全文搜尋、要存 BLOB），用 DynamoDB 是反模式 — single item 上限 400KB 直接擋掉 BLOB 場景。

### 軸 3：Consistency 需求是否可接受 eventual

DynamoDB 預設 eventually consistent read、strong read 也只在同 region quorum 內成立。最終一致性可接受的 workload 才適合；strong consistency 必要（跨 entity 原子寫入 / 跨 region 強一致 / 全局單調遞增 ID）必須走 SQL / NewSQL。本軸屬通用工程判讀、case 沒有揭露具體 staleness 閾值；判讀工具是 [consistency-model-optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/) 的 per-call site review。

### 軸 4：Access pattern 是否穩定

access pattern 數量穩定且窮舉可列（典型 10-30 個）single-table 才能精準設計 PK/SK 跟 GSI；查詢仍在探索期、pattern 頻繁變動，SQL 多 table 較容易演化、改 query 不用改 schema。本軸也屬通用工程判讀、case 沒明示 access pattern 數量閾值，但 9 個 case 寫進 production 的 access pattern 多半是 *業務契約已凍結* 的場景（會議 metadata、watchlist、玩家戰績、訊息推送）。

任一軸不成立、回 [PostgreSQL vendor](/backend/01-database/vendors/postgresql/) 或考慮多 vendor 組合。4 軸都成立、再進 single-table 設計。

## 核心概念：access pattern 先於 schema

Single-table design 的 first-class concept 是 *access pattern 先於 schema*：先列 15-30 個 query 才開始設 key、不是先設 schema 再想怎麼 query。

DynamoDB 的 key 結構：

- **PK（partition key）**：決定資料散布到哪個 partition；同 PK 的 item 物理共置（item collection）
- **SK（sort key）**：決定同 partition 內排序與範圍查詢；composite SK 用 `#` 分隔層級（如 `ORDER#2026-05-27#001`）
- **同 PK 不同 SK 前綴**：把相關 entity 物理共置、用一次 `Query` 拿回多個 entity；對應 RDB 的 JOIN

實際範例（Disney+ 9.C27 揭露的 access pattern）：

```text
PK             SK                          Entity
USER#u123      PROFILE                     用戶資料
USER#u123      WATCHLIST#m456              觀看清單項目
USER#u123      PROGRESS#device-iPad#m456   播放進度
USER#u123      PROGRESS#device-TV#m456     播放進度（跨裝置）
```

一次 `Query PK=USER#u123` 拿回該 user 的所有資料、不需要 join。SK 前綴 `PROFILE` / `WATCHLIST#` / `PROGRESS#` 區分 entity type、range query 還能限定「只取 watchlist」（`begins_with(SK, "WATCHLIST#")`）。

對應 knowledge card：[hot partition](/backend/knowledge-cards/hot-partition/)、[workload model](/backend/knowledge-cards/workload-model/)。

## 設計流程

從 access pattern 反推 PK/SK 跟 GSI 的 5 步流程。

#### Step 1：access pattern 表窮舉

每個 user story 寫成一條 query：

```text
| #  | User story                          | Query                                 | Latency | Consistency |
| -- | ----------------------------------- | ------------------------------------- | ------- | ----------- |
| 1  | 顯示用戶 profile                    | GetItem PK=USER#{id} SK=PROFILE       | p99 5ms | eventual    |
| 2  | 取用戶所有觀看清單                  | Query PK=USER#{id} begins_with(SK, "WATCHLIST#") | p99 10ms | eventual |
| 3  | 跨裝置同步播放進度（最新）          | GetItem PK=USER#{id} SK=PROGRESS#{movie}#latest | p99 15ms | strong |
```

15-30 條 query 全列出，這是 single-table 的契約。漏列等於設計時看不到、上線後撞。

#### Step 2：entity-relationship → PK/SK 映射

常見模式：

- 主 entity 用 `{ENTITY}#{id}` 當 PK（USER / ORDER / PRODUCT）
- 子 entity 用同 PK + 不同 SK 前綴（`PROFILE` / `ORDER#{timestamp}` / `ITEM#{id}`）
- 1-N 關係（user 有多個 watchlist）用同 PK + 不同 SK
- N-N 關係（user 跟 friend）用兩條 item（A→B 與 B→A）或單獨 relationship entity

#### Step 3：GSI 補反向查詢

主 PK 覆蓋不到的 access pattern 用 GSI 補：

- 「依 status 查所有 order」→ GSI PK = `status`、SK = `created_at`
- 「依 product 查所有買家」→ GSI PK = `product_id`、SK = `user_id`

GSI 數量上限 20、實務 < 5；過多時表示主 PK 設計沒覆蓋夠多 access pattern、應重新設計。詳見 [gsi-lsi-design](/backend/01-database/vendors/dynamodb/gsi-lsi-design/)。

#### Step 4：CloudFormation / Terraform DDL

```yaml
Resources:
  SingleTable:
    Type: AWS::DynamoDB::Table
    Properties:
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
        - AttributeName: GSI1PK
          AttributeType: S
        - AttributeName: GSI1SK
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: GSI1
          KeySchema:
            - AttributeName: GSI1PK
              KeyType: HASH
            - AttributeName: GSI1SK
              KeyType: RANGE
          Projection:
            ProjectionType: INCLUDE
            NonKeyAttributes: [status, created_at]
```

#### Step 5：驗證點

- 每個 access pattern 對應一個 `Query` / `GetItem`、沒有 `Scan`、沒有 application-side join
- Contributor Insights 看 top-N PK 訪問是否均勻
- CloudWatch `ConsumedReadCapacityUnits` / `ConsumedWriteCapacityUnits` 按 partition 分布觀察

**Rollback boundary**：access pattern 改動可加 GSI 補；entity 拆 table 比合 table 容易，先合再拆。

## 失敗模式

5 個 production 常見踩雷：

#### Case 1：late-binding access pattern

production 上線半年後 PM 要新 query「按地區列訂單」、PK 沒包 region、只能 `Scan` 或加 GSI。根因是 access pattern 沒在設計階段窮舉，這是 single-table design 的核心責任。修法：access pattern 表列完整、不可省略；新需求進來先回 access pattern 表 review、再決定加 GSI 還是重設計 PK。

#### Case 2：SK 排序衝突

同 PK 下兩種 entity（`ORDER#{timestamp}` 與 `PAYMENT#{timestamp}`）混用同 SK 空間、range query 拿 `BETWEEN '2026-01-01' AND '2026-12-31'` 時 entity 邊界錯亂。修法：SK 前綴必須能 *用 `begins_with` 完全區隔* entity（`ORDER#2026-...` vs `PAYMENT#2026-...`）。

#### Case 3：item collection 超過 10GB

單 PK 下所有 item 加起來超過 10GB 上限、DynamoDB 拒絕新寫入。常見於「user 為 PK + user 有大量歷史 event」場景。修法：歷史 event 改用 `USER#{id}#YYYYMM` 當 PK 把時間 bucket 切開、或把歷史 event 寫進另一張 archive table（cold path）。

#### Case 4：GSI 反向變主表

開始 GSI 只補 1-2 個 query，半年後 GSI 流量超過主表、cost 翻倍。根因是主 PK 沒設計好、GSI 變成 *實質的主存取路徑*。修法：重新設計 PK、把 GSI 流量主要的 access pattern 升為主表 query；GSI 從多到少要 application 端配合 cutover。

#### Case 5：DynamoDB 當 RDBMS 用

把 normalize 過的 schema 直接搬、每個 business query 要 2-3 個 `GetItem`、latency 從 5ms 變 30ms。修法：normalize 適合 SQL、不適合 KV；single-table 是把 normalize 拍平、用 denormalize 換 read latency。

**Anti-recommendation**：access pattern < 5 個、entity 間關聯弱、查詢仍在探索期 → 用 SQL 或 multi-table 先寫、access pattern 穩定再 single-table。

## 容量與觀測

CloudWatch metric：

- `ConsumedReadCapacityUnits` / `ConsumedWriteCapacityUnits`：按 partition 分布看是否均勻
- `ThrottledRequests`：早期 hot partition 訊號（provisioned 模式立即可見）
- `SuccessfulRequestLatency` p99：on-demand 模式下 hot partition 表現為 latency spike（見 [partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) 的 mode × partition 交叉判讀）

Contributor Insights：top-N partition key 訪問頻率，揭露 single-table 設計後是否仍均勻；每月 cost ~$0.02 per million event、值得開。

GSI 觀測：每個 GSI 獨立 RCU/WCU、projection type（`KEYS_ONLY` / `INCLUDE` / `ALL`）決定 storage cost。

TTL 是 storage cost 防爆的標配（特別在 message-class workload）— PayPay `9.C26` 揭露 3 億 / 天 × 30 天 = 90 億筆記錄、不清理會撐死 storage 預算；設 TTL attribute 讓 DynamoDB 自動刪過期 item、消耗 0 WCU。

接回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 跟 [9.5 Bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)。

## 邊界與整合

### Frame 3：DynamoDB 在 fleet 治理 frame 的退化

跨 vendor 共通 frame：production scale 走 *fleet of clusters*（Aurora 200 cluster / CockroachDB 380+ cluster / MongoDB Atlas 20 DB 都是這個 frame）。DynamoDB 在這 frame 退化得最徹底 — *不走 fleet of clusters*、是用 partition 內部自動切。

對照其他 vendor：

| Vendor      | Scale-out 拓樸                                      | 容量決策層                             |
| ----------- | --------------------------------------------------- | -------------------------------------- |
| DynamoDB    | 單 table、partition 自動 split / merge              | mode 選擇 + PK 均勻 + GSI 補位         |
| Aurora      | Fleet of clusters（business / microservice / 合規） | Cluster boundary + replica 數量        |
| CockroachDB | Fleet of clusters or 邏輯一個 cluster + locality    | Per-app vs shared cluster 決策         |
| MongoDB     | Sharded cluster + 多 cluster（blast radius）        | Shard key + cluster ownership boundary |

**DynamoDB 退化點**：partition 是 *vendor 內部物理層*、不暴露給應用 — application 看到的永遠是「一張 table」、不需要規劃 cluster boundary。代價是 *partition key 設計責任全壓在 schema 上*（[partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)）、不能用「拆 cluster 解 blast radius」當逃避路徑。

**例外情境**：DynamoDB 在 *合規場景* 仍可能走「多 table per market」拓樸（見 Frame 5 [global-tables-conflict](/backend/01-database/vendors/dynamodb/global-tables-conflict/) region-pinned 段）— 但動機是合規 boundary 而非 capacity scale、跟 Aurora fleet driver 結構不同。

### DynamoDB 在系統中的角色：control plane / metadata / state

DynamoDB 不是 universal store、不是 SQL 替代品。3 個 case 重複揭露同一定位：

- **9.C18 Zoom**：媒體串流走 P2P + edge servers、DynamoDB 只承擔會議 / 用戶 metadata。control plane 跟 data plane 分離是 30x DAU surge 能撐的工程前提（不是 DynamoDB 自己魔法）。
- **9.C27 Disney+**：content 走 S3 + CDN、DynamoDB 只承擔 metadata / watchlist / cross-device 進度。
- **9.C19 Capcom**：EKS 跑 game server / 處理即時遊戲邏輯、DynamoDB 處理持久狀態。

### Durable queue / write-buffer 作為正向非 OLTP access pattern

`9.C15 Tixcraft` 揭露 DynamoDB 的另一種正向用法 — *寫入緩衝層*、不是 OLTP：

- 拓元用 DynamoDB 接「訂單」寫入、不是即時生效、是讓 traditional server（金流 / 票庫）用自己能承受的速度消費
- 架構上 DynamoDB 扮演 durable queue、不是傳統 OLTP DB；這層解耦讓「前端可擴 130 倍、後端不用同步擴」
- 對比 RDBMS：RDB 寫入要即時可讀、即時索引、即時 transaction commit；DynamoDB 寫入可以「先 durable、之後處理」
- 寫進你的設計時要明示：這是 *非預設* access pattern、是 flash-sale / 高峰寫入解耦的工程選擇、不是 DynamoDB 預設定位

這個 access pattern 跟 single-table 設計兼容 — PK 仍是 `event_id#shard`、SK 是 `ORDER#{user_id}#{timestamp}`、寫入時直接寫，後端傳統 server 慢消費；只是讀路徑是 *後端服務 batch 取* 而非 user-facing query。

### RDB connection limit 機制對照

`9.C29 Lemino` 揭露為什麼 DynamoDB 在 surge 下不會踩 RDB 的隱性天花板：

- 「connection limits became bottlenecks when experiencing a rapid increase in access」— PostgreSQL/MySQL 每連線吃記憶體 / process、pool 上限 1K-5K、connection 是 RDB 在 surge 下 *第一個爆點*（不是 CPU / disk）
- DynamoDB 的 HTTP API（無 long-lived connection state）天然解這個問題；client 不需要維護 connection pool、AWS SDK 用 connection-less HTTP request

選 DynamoDB 不只是 schema 選擇、是 connection model 選擇。single-table 設計 *外部* 的容量優勢、寫進邊界判讀條件。

### Sibling 與 cross-link

- [partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) — 軸 1 不天然均勻時的 composite key 補救
- [gsi-lsi-design](/backend/01-database/vendors/dynamodb/gsi-lsi-design/) — 主 PK 覆蓋不到的 access pattern 補位
- [on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) — access pattern 影響 capacity mode 選擇
- [consistency-model-optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/) — 軸 3 的 per-call site review
- [global-tables-conflict](/backend/01-database/vendors/dynamodb/global-tables-conflict/) — 跨 region 多寫入時 single-table 仍適用、但 conflict resolution 加一層
- 反向路由：access pattern 探索期 / strong consistency 必要 / data plane workload → 回 [PostgreSQL vendor](/backend/01-database/vendors/postgresql/)
