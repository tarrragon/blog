---
title: "1.7 Schema Migration Rollout 證據（Schema Migration Rollout Evidence）實作示範"
date: 2026-05-11
description: "以訂單付款狀態欄位演進示範 schema migration 如何產出 evidence、release gate 與 incident decision log。"
weight: 7
tags: ["backend", "database", "migration", "implementation", "evidence-package"]
---

Schema migration rollout 證據（Schema Migration Rollout Evidence）的核心責任是把正式狀態的演進拆成可觀測、可放行、可停止與可回寫的服務路徑。這篇以訂單資料表的付款狀態欄位演進為例，示範資料庫變更如何從 schema design、backfill、cutover 交接到 evidence package、release gate 與 incident decision log。

## 服務路徑與狀態責任

這條服務路徑是 `checkout-api -> order-db -> payment-callback -> reconciliation-job`。Checkout 建立訂單時先寫入訂單主檔與付款待確認狀態；payment callback 會更新付款結果；客服後台與對帳 job 會讀取同一筆訂單狀態來判斷是否需要補償、退款或人工處理。

本篇示範的變更是把原本單一 `status` 欄位中的付款語意拆到 `payment_state`。這個欄位屬於正式狀態，會影響使用者看到的訂單結果、付款回呼的冪等更新、客服查詢與對帳流程，因此 rollout 的核心是讓新舊狀態語意在過渡期同時成立；DDL 只是其中一個執行動作。

這條路徑的前置概念來自 [1.2 schema design 與資料建模](/backend/01-database/schema-design/)、[1.3 transaction 與一致性邊界](/backend/01-database/transaction-boundary/) 與 [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/)。1.2 定義欄位責任，1.3 定義哪些更新要在同一個交易邊界內成立，1.6 定義 expand、backfill、cutover 與 contract 的執行節奏。

## Rollout 階段

Migration rollout 的責任是把一次高風險資料變更切成多個可驗證階段。每個階段都要有輸入條件、完成訊號與停止條件，讓團隊能在資料漂移擴大前停下來。

| 階段     | 服務責任                       | 完成訊號                                   |
| -------- | ------------------------------ | ------------------------------------------ |
| Expand   | 新欄位與新程式碼能和舊版本共存 | 新舊程式可同時讀寫，舊欄位仍可支撐服務     |
| Backfill | 歷史訂單補齊 `payment_state`   | checkpoint 穩定前進，mismatch 維持在門檻內 |
| Cutover  | 讀取路徑改以新欄位為主         | 新欄位讀取成功率與對帳結果達到放行條件     |
| Contract | 移除舊語意與舊寫入路徑         | 舊欄位已無服務依賴，回寫與監控已更新       |

這張表的重點是責任轉移。Expand 保護相容性，backfill 保護歷史資料，cutover 保護線上讀取，contract 保護長期維護成本；四者對應不同 evidence，也需要不同 release gate 判讀。

## 實作基準：先寫出狀態契約

狀態契約的責任是讓 migration 先有可驗證的語意邊界。這篇的範例把 `orders.status` 裡混合的訂單生命週期與付款語意拆開：訂單仍用 `status` 表示 `created`、`fulfilled`、`cancelled` 這類流程狀態，付款結果則交給 `payment_state` 表示 `pending`、`authorized`、`captured`、`failed` 與 `refunded`。

| 舊狀態                   | 新欄位 `payment_state` | 判讀理由                         |
| ------------------------ | ---------------------- | -------------------------------- |
| `pending_payment`        | `pending`              | 訂單已建立，付款結果仍未確認     |
| `paid`                   | `captured`             | 付款已完成，可進入出貨或履約流程 |
| `payment_failed`         | `failed`               | 付款失敗，需要重試或取消路由     |
| `refunded`               | `refunded`             | 付款已逆向處理，客服與對帳要可查 |
| `cancelled_before_pay`   | `pending`              | 沒有付款成功事實，只保留流程取消 |
| `manual_review_required` | `pending`              | 付款狀態未完成，等待人工判讀     |

這張 [mapping table](/backend/knowledge-cards/mapping-table/) 是 [validation query](/backend/knowledge-cards/validation-query/)、backfill job 與 incident decision log 的共同語意來源。Mapping table 留在工程師腦中時，後續 mismatch 會變成「資料看起來怪」；mapping table 進入 artifact 後，gate 就能判斷錯誤集中在哪個付款語意，而不是停在總筆數。

## Expand：先建立相容窗口

Expand phase 的核心責任是讓新資料結構先進入 production，同時保留舊程式的可運作性。以 `payment_state` 為例，常見起點是新增 nullable 欄位、補上必要索引，並讓寫入路徑可以在新欄位缺值時仍使用舊 `status` 判讀付款狀態。

```sql
ALTER TABLE orders
  ADD COLUMN payment_state text NULL;

CREATE INDEX CONCURRENTLY idx_orders_payment_state
  ON orders (payment_state)
  WHERE payment_state IS NOT NULL;
```

這段 SQL 的用途是示範 artifact 形狀。Nullable 欄位保留舊資料的相容窗口；partial index 讓新讀取路徑能先被驗證，同時避免把尚未 backfill 的歷史資料全部推進新查詢模型。不同資料庫會有不同線上 DDL 能力，release gate 要把 lock 行為、index build 進度與 replication lag 納入 checks。

應用程式在 expand 階段要支援 [read compatibility](/backend/knowledge-cards/read-compatibility/)。相容性較高的寫法是讀取時優先使用 `payment_state`，缺值時 fallback 到舊 `status` 的付款語意；寫入時則依交易邊界同步更新舊欄位與新欄位，直到 cutover 前都保留一致性檢查。

```text
readPaymentState(order):
  if order.payment_state is not null:
    return order.payment_state
  return mapLegacyStatusToPaymentState(order.status)

applyPaymentCallback(order, callback):
  nextPaymentState = mapCallbackToPaymentState(callback)
  update orders
    set status = mapPaymentStateToLegacyStatus(nextPaymentState),
        payment_state = nextPaymentState
    where id = order.id
```

這段相容讀寫的重點是「同一個 callback 只產生一個付款判讀」。舊欄位與新欄位可以同時存在，但它們要由同一份 mapping function 產生，否則 payment callback、客服修復與 reconciliation job 會各自形成一套隱性規則。

這裡要特別看 [dual write](/backend/knowledge-cards/dual-write/) 的風險。雙寫只表示兩個欄位都有被寫入，仍要用 validation query 驗證兩者語意是否一致。若付款回呼、手動退款與對帳修復走不同程式路徑，雙寫函式也要被這些路徑共同使用。

### Dual-write divergence schema

Dual-write 的責任不只是「兩邊都寫」、是「兩邊寫的結果一致」。要證明這件事、需要明確的 divergence schema、否則事故當下無法區分 mapping bug 跟 race condition。

最小 divergence 紀錄欄位：

| 欄位              | 用途                                                            |
| ----------------- | --------------------------------------------------------------- |
| `order_id`        | 哪一筆訂單                                                      |
| `legacy_value`    | 舊欄位寫入後的值                                                |
| `new_value`       | 新欄位寫入後的值                                                |
| `expected_new`    | 用 mapping function 從 `legacy_value` 推算的預期新值            |
| `divergence_type` | `mapping-mismatch` / `race-condition` / `manual-override`       |
| `write_path`      | 哪個程式路徑寫的（callback / refund / manual / reconciliation） |
| `detected_at`     | 偵測時間                                                        |

`expected_new` 跟 `new_value` 對不上、表示 mapping function 在某些 path 沒被使用、是 mapping bug。`legacy_value` 跟 `new_value` 對不上、且 `expected_new == legacy_value` 對得上、是 dual-write 本身少寫一筆、可能是 race condition 或部分失敗。兩種情況的修法完全不同、不分類會在事故當下亂修。

Dual-write 失敗回退策略：寫舊欄位成功、寫新欄位失敗時、不能直接 retry 新欄位（會跟主寫入競爭）。實務做法是把 divergence 寫進 outbox / repair queue、由 backfill 同類流程補。對應 [9.C16 SeatGeek](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 的 outbox-style 設計。

### 線上 DDL 的 vendor 差異

Expand 階段加欄位 / 加索引、不同資料庫的 *阻塞行為* 差異極大、選錯時機會直接讓 production 鎖表。

- **PostgreSQL**：`ALTER TABLE ADD COLUMN ... NULL` 是 metadata-only、不重寫 table。`ADD COLUMN ... NOT NULL DEFAULT ...` 在 PG 11+ 才是 metadata-only。`CREATE INDEX CONCURRENTLY` 不阻塞寫入、但更慢、且 transaction 中不能用。`ALTER TABLE ALTER COLUMN TYPE` 通常會重寫整張表、要先評估規模。
- **MySQL / Aurora MySQL**：`ALTER TABLE ... ALGORITHM=INSTANT` 是 8.0+ 的 metadata-only、5.7 則靠 `ALGORITHM=INPLACE` / `LOCK=NONE`。Aurora MySQL 還有 fast DDL（部分變更秒級完成、不重寫）。判讀重點是 *explicitly 指定 ALGORITHM*、不要讓 MySQL 自己選（可能掉回 COPY 算法、整張表複製）。
- **Spanner**：schema change 預設非阻塞、後端 async 補欄位。新欄位 read 在 schema change 完成前可能讀不到、應用層要容忍。
- **DynamoDB**：表本身沒 schema、但 *GSI（Global Secondary Index）創建是 async*、可能跑數小時、且新 GSI 在 backfill 完成前查不到完整資料。判讀重點：cutover 不能假設新 GSI 立即可用、要等 `IndexStatus = ACTIVE`。
- **Cosmos DB**：document 級別無 schema、新 indexed path 加進 indexing policy 後、後端 *re-index* 整個 partition、期間 RU consumption 飆升。

各 vendor 的線上 DDL evidence 都要包含：操作開始時間、預估完成時間、是否阻塞讀寫、實際 lock duration。expand gate 通過條件不能只看 DDL 跑完、要看 *所有副效應收斂*（index status active、re-indexing 完成、replica 同步）。

對應 vendor pages：[PostgreSQL](/backend/01-database/vendors/postgresql/)、[MySQL](/backend/01-database/vendors/mysql/)、[Aurora](/backend/01-database/vendors/aurora/)、[Spanner](/backend/01-database/vendors/spanner/)、[DynamoDB](/backend/01-database/vendors/dynamodb/)、[Cosmos DB](/backend/01-database/vendors/cosmosdb/) 的線上 DDL 段。

## Backfill：把歷史資料變成可驗證進度

Backfill phase 的核心責任是把歷史資料補齊成可追蹤、可暫停、可重試的進度。訂單表通常會同時承擔交易查詢、客服查詢與對帳查詢；backfill 若只追求速度，容易和線上流量競爭 I/O、放大 replication lag 或改變查詢計畫。

Backfill job 應以 checkpoint 管理進度。每批選取固定範圍的訂單，轉換 `status` 到 `payment_state`，寫入後立刻產生該批 validation query 結果。批次大小要能依延遲、鎖等待、replication lag 與線上錯誤率調整。

```text
checkpoint:
  migration_id: orders-payment-state-2026-05
  last_order_id: 18420000
  batch_size: 5000
  started_at: 2026-05-11T02:10:00Z
  completed_at: 2026-05-11T02:12:40Z
  rows_scanned: 5000
  rows_updated: 4921
  mismatch_count: 3
```

Checkpoint 的角色是把 backfill 變成可恢復流程。`last_order_id` 告訴下一批從哪裡繼續，`rows_updated` 與 `mismatch_count` 告訴 gate 這批是否可以被納入放行證據，時間欄位則讓 replication lag、slow query 與錯誤率能回到同一個觀察窗口。

[Validation query](/backend/knowledge-cards/validation-query/) 的責任是證明語意一致。最小集合包含總筆數、已補筆數、缺值筆數、新舊語意不一致樣本、每批耗時、慢查詢與 replication lag。這些查詢要保留 [query link](/backend/knowledge-cards/query-link/) 與 [time range](/backend/knowledge-cards/time-range/)，後續才能進入 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。

```sql
SELECT
  count(*) AS total_rows,
  count(*) FILTER (WHERE payment_state IS NULL) AS missing_payment_state,
  count(*) FILTER (
    WHERE payment_state IS NOT NULL
      AND payment_state <> map_legacy_status_to_payment_state(status)
  ) AS mismatch_rows
FROM orders
WHERE id BETWEEN 18415001 AND 18420000;
```

Validation query 要和 mapping table 共用同一個語意。資料庫端缺少同一份 mapping function 時，查詢至少要把 mapping 規則展開成明確 CASE expression，並把 query version 保存在 evidence package；這樣事後才能知道 mismatch 是資料錯誤、mapping 規則改變，還是查詢本身落後。

## Cutover：先切讀取，再收斂寫入

Cutover phase 的核心責任是把服務判讀權交給新欄位，同時保留可回退窗口。對訂單付款狀態來說，切換順序通常先從低風險讀取路徑開始，例如客服後台與內部對帳，再進入 checkout 查詢與使用者可見狀態；每一批切換都要有自己的 [cutover window](/backend/knowledge-cards/cutover-window/)。

讀取 cutover 的 [stop condition](/backend/knowledge-cards/stop-condition/) 要比寫入 cutover 更早觸發。新欄位讀取後出現 mismatch、客服查詢結果漂移、對帳 job 補償量異常時，先回到 [fallback read](/backend/knowledge-cards/fallback-read/)，讓錯誤限制在判讀層，再重新驗證寫入收斂條件。

寫入 cutover 要確認所有更新來源都已對齊。付款回呼、手動修復、退款、訂單取消與 reconciliation job 都可能更新付款狀態；只切主 checkout 寫入路徑會留下長尾漂移。完成 cutover 前，要用 audit query 確認仍在寫舊欄位的程式路徑已經歸零或被納入例外清單。

### Shadow read pattern：cutover 前的讀取驗證

Shadow read 的責任是讓新讀取路徑在 *真實流量* 下被驗證、但 *不影響使用者結果*。這跟 dual-write 是對偶機制：dual-write 證寫入收斂、shadow read 證讀取分歧。

實作模式：

1. 每一筆讀取請求、同時用 *舊邏輯* 跟 *新邏輯* 查一次。
2. 回給用戶的仍是舊邏輯結果（用戶體驗不變）。
3. 在背景把兩個結果差異寫進 divergence log。
4. 收集足夠樣本後、再決定切換 cutover。

```text
readPaymentStateWithShadow(order):
  legacy = mapLegacyStatusToPaymentState(order.status)
  new_result = order.payment_state ?? legacy
  if legacy != new_result:
    asyncLogDivergence({
      order_id: order.id,
      legacy: legacy,
      new: new_result,
      sample_at: now(),
      caller: requestContext.caller,
    })
  return legacy  // 用戶仍拿舊邏輯結果
```

Shadow read 的判讀重點：

- **抽樣率**：1% / 10% / 100% — 高流量場景全量 shadow 會雙倍 DB 讀取、要先評估容量。Cosmos DB / DynamoDB 的 RU 成本要乘 2。
- **分歧分類**：跟 dual-write 一樣、divergence 要分類（mapping bug / race condition / stale read）、不分類無法定位修法。
- **覆蓋條件**：要驗證所有 caller path（checkout / support / reconciliation / external API）都跑過 shadow、否則 cutover 後可能踩到沒測試過的 path。
- **退場條件**：shadow read 不該長期跑、會增加負載。設明確 sunset deadline、cutover 完成後一週內移除。

對應 [9.C20 Zomato TiDB → DynamoDB migration](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — migration 期間用 shadow read 持續驗證 mapping 規則、抓到 mapping drift。

Dual-write 跟 shadow read 的選擇不是互斥、是依風險組合：

| 風險場景                         | 建議組合                                                  |
| -------------------------------- | --------------------------------------------------------- |
| 新邏輯只影響讀取（cache、index） | shadow read 即可、不需要 dual-write                       |
| 新欄位是 source of truth         | dual-write 必要、cutover 前加 shadow read 驗證            |
| 跨 service 共用欄位              | dual-write + shadow read + cross-service contract test    |
| 跨 region migration              | dual-write + shadow read + 跨 region replication evidence |

## Multi-region 與跨服務協調

Migration 跨越 region 或多個 service 時、rollout 順序錯誤是最常見的失敗模式。Service A 切到新欄位、service B 還在讀舊欄位、結果整條業務流量看到不一致。

### Multi-region rollout 順序

跨 region 的 schema migration 要從 *最後寫入點* 開始 expand、從 *最後讀取點* 開始 cutover。先 expand 寫端、再 expand 讀端；先 cutover 讀端、再 cutover 寫端。順序反了會在過渡期讀到沒被寫的新欄位、或寫了沒被讀的新欄位。

實務步驟：

1. **Schema expand**：所有 region 同步加新欄位（先寫端再讀端、不能跳）。確認跨 region replication lag 在新欄位上收斂、再進下一步。
2. **Backfill**：可以平行跑、但每 region 各自 checkpoint、不共用。某 region backfill stuck 不應該卡住其他 region。
3. **Cutover read**：region by region 切讀、用 canary region 先試 24-48 小時、再擴散。
4. **Cutover write**：所有 region 都切完讀、再統一切寫。寫端切換比讀端更敏感、跨 region 寫差異會放大成跨 region inconsistency。

對應 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 的跨 region consistency 段。

### Cross-service migration 協調

當 schema 變更影響多個 service 時、API contract 是 *鬆耦合* 介面、不該讓所有 service 同步切換。

協調機制：

- **新欄位先在 API 是 optional**：API contract 加新欄位、預設 nullable / optional。下游 service 可選擇何時讀。
- **舊欄位保留至少一個版本週期**：API 不能跟 DB schema 同步 contract、否則下游沒時間切。實務上保留 1-2 季、給下游充足 cutover 窗口。
- **owner-by-owner cutover roster**：明確列出每個下游 service 的 owner、預計 cutover 時間、目前狀態。常用工具是共享 dashboard、不是散落的 ticket。
- **Contract test**：每個下游 service 對新欄位都要有 contract test、在 CI gate 跑過。避免上游 cutover 後下游才發現沒讀對。

對應案例：[9.C20 Zomato TiDB → DynamoDB](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — 跨多個 service 的 access pattern 變更、必須每個 service 各自驗證、不能假設「DB 切了就好」。

## Evidence Package

資料庫 migration 的 evidence package 負責證明資料演進是否可判讀。這份 package 要把 validation query、時間窗、資料限制與 owner 包成後續放行與事故判斷可引用的證據，dashboard 只作為摘要入口。

| 欄位                                                   | 訂單欄位演進中的內容                                      |
| ------------------------------------------------------ | --------------------------------------------------------- |
| Source                                                 | validation query、DB metric、migration job log、audit log |
| [Time range](/backend/knowledge-cards/time-range/)     | expand、backfill、cutover 各階段的查詢窗口                |
| [Query link](/backend/knowledge-cards/query-link/)     | row count、mismatch sample、replication lag、slow query   |
| Owner                                                  | database owner、checkout owner、reconciliation owner      |
| [Data quality](/backend/knowledge-cards/data-quality/) | query 延遲、replica freshness、sample completeness        |
| [Confidence](/backend/knowledge-cards/confidence/)     | confirmed / suspected / needs follow-up                   |
| [Known gap](/backend/knowledge-cards/known-gap/)       | 未覆蓋的手動修復路徑、低流量 tenant、延遲回呼             |

Source 欄位要保留資料來源的能力邊界。Validation query 能證明欄位語意一致，DB metric 能看出 latency 與 lag，job log 能追進度，audit log 能判斷是否有高權限修復行為。把這些來源混在一起會讓下游誤判證據的用途。

[Data quality](/backend/knowledge-cards/data-quality/) 欄位要直接寫出限制。若查詢只跑 primary、replica lag 還在回復、某些 tenant 因資料遮罩未被抽樣，這些限制要跟 evidence 一起交給 release gate，讓 gate 能以證據完整度決定是否放行。

```yaml
evidence_package:
  name: orders-payment-state-cutover-batch-37
  source:
    - validation_query: q_orders_payment_state_batch_37
    - db_metric: replication_lag_orders_primary
    - job_log: backfill_orders_payment_state_2026_05
  time_range: 2026-05-11T02:10:00Z/2026-05-11T02:20:00Z
  owner:
    database: data-platform-oncall
    service: checkout-oncall
    reconciliation: finance-ops-owner
  data_quality:
    replica_freshness: "primary only; replica lag still recovering"
    sample_completeness: "tenant tier enterprise covered; sandbox tenants excluded"
  confidence: suspected
  known_gap:
    - "manual refund repair path not yet sampled"
```

這份 package 故意把 `confidence` 標成 `suspected`。原因是 evidence 已能支持 backfill 繼續前進，但還不足以支持使用者可見讀取 cutover；這種中間狀態要被明確寫出，gate 才能做分階段決策。

## Release Gate

Schema migration 的 release gate 負責判斷下一階段是否可以放行。它接收 evidence package，但決策語言要回到 [6.8 Release Gate 與變更節奏](/backend/06-reliability/release-gate/)：`Gate decision`、`Checks`、`Stop condition`、`Rollback window`、`Owner`。

| Gate 欄位                                                | 這條路徑的最小內容                                                    |
| -------------------------------------------------------- | --------------------------------------------------------------------- |
| [Gate decision](/backend/knowledge-cards/gate-decision/) | 放行下一批 backfill、暫停 cutover、回到 fallback read 或 fail-forward |
| Checks                                                   | compatibility result、mismatch rate、replication lag、slow query      |
| Stop condition                                           | mismatch 超門檻、交易錯誤率上升、lag 超窗口、客服查詢漂移             |
| Rollback window                                          | 讀取 fallback 可用時間、舊欄位可支撐多久、contract 前最後回退點       |
| Owner                                                    | migration owner、service owner、on-call owner                         |

[Gate decision](/backend/knowledge-cards/gate-decision/) 要用服務語言書寫。`migration pass` 這種結論對下游不夠具體；`放行 10% 訂單 backfill`、`暫停使用者可見讀取 cutover`、`維持 fallback read 24 小時` 才能讓執行團隊知道下一步。

[Rollback window](/backend/knowledge-cards/rollback-window/) 是資料庫 migration 的關鍵欄位。Expand 與 backfill 階段通常能回到舊讀取；cutover 後仍可 fallback；contract 後舊語意被移除，回退會變成資料修復或 [fail-forward](/backend/knowledge-cards/fail-forward/)。gate 要在每階段說清楚目前還剩哪種退路。

```yaml
release_gate:
  gate_decision: "allow next 10% backfill; block customer-visible read cutover"
  checks:
    mismatch_rate: "0.04%, below 0.1% batch threshold"
    replication_lag: "p95 12s, below 30s stop condition"
    slow_query: "no new support-admin slow query above 500ms"
  stop_condition:
    - "mismatch_rate >= 0.1% for two consecutive batches"
    - "replication_lag >= 30s for 10 minutes"
    - "support-admin query drift confirmed by reconciliation owner"
  rollback_window: "fallback read available until contract phase starts"
  owner: checkout-oncall
```

這份 gate record 把「繼續 backfill」和「暫緩讀取 cutover」拆成兩個決策。資料庫 migration 常見的判讀問題是 evidence 只支撐下一批資料修補，還支撐不了使用者可見行為切換。

## Incident Decision Log

Migration 進入 production 後，pause、rollback 與 fail-forward 都是事故決策。這些決策要同步寫入 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)，讓事中交班與事後復盤能回放當時的證據與限制。

常見決策包括暫停 backfill、降低 batch size、回到舊讀取、停止 contract、手動修補 mismatch、選擇 fail-forward。每筆都要保留 `Timestamp`、`Decision`、`Context`、`Evidence`、`Owner`、`Expected effect` 與 [rollback condition](/backend/knowledge-cards/rollback-condition/)。

例如 cutover 後發現客服查詢 mismatch 升高，decision log 可以寫成：

```yaml
incident_decision:
  timestamp: 2026-05-11T03:05:00Z
  decision: "rollback support-admin read path to legacy status fallback"
  context: "support-admin mismatch increased after internal read cutover"
  evidence:
    - query: q_orders_payment_state_support_mismatch
    - window: 2026-05-11T02:35:00Z/2026-05-11T03:05:00Z
    - interpretation: "suspected callback mapping drift"
  owner: checkout-incident-commander
  expected_effect: "support ticket misclassification returns to baseline"
  rollback_condition: "mismatch remains above threshold after 15 minutes"
```

這種記錄能避免事後只剩「當時有回退」的模糊敘事。後續 [8.23 Control Plane Decision Log and Write-back 實作示範](/backend/08-incident-response/control-plane-decision-log-write-back/) 可承接同一組決策紀錄，把缺少 validation、owner 或 runbook 的地方回寫成改善項。

## 判讀訊號

判讀訊號的責任是讓讀者知道何時該繼續、何時該停、何時該改路線。Migration 訊號要同時看資料正確性、線上健康度與回退窗口。

| 訊號                                   | 判讀重點                             | 對應動作                                  |
| -------------------------------------- | ------------------------------------ | ----------------------------------------- |
| mismatch rate 持續低於門檻             | 新舊欄位語意大致一致                 | 放行下一批 backfill 或低風險讀取 cutover  |
| mismatch 樣本集中在特定 callback       | 轉換函式或特定付款路徑語意不一致     | 暫停 cutover，修 mapping 後重跑該批       |
| dual-write divergence 分布偏向 mapping | mapping function 在某 path 沒被使用  | 找出該 path、強制走共用 mapping function  |
| dual-write divergence 偏向 race        | 部分寫入失敗、寫順序問題             | 切到 outbox-based dual-write、別直連      |
| shadow read 抽樣 RU 飆升               | shadow 讀取沒設抽樣率、雙倍負載      | 降低抽樣率、或改成 off-peak shadow        |
| replication lag 在 backfill 升高       | migration 與線上查詢競爭資源         | 降低 batch size，避開 peak，延長觀察窗口  |
| slow query 出現在客服查詢              | 新欄位索引或查詢模型未對齊           | 回到 fallback read，補 index 或改查詢條件 |
| DynamoDB GSI 仍在 building             | cutover 前依賴未 ACTIVE 的 GSI       | 等 GSI ACTIVE 再切讀、別假設立即可用      |
| 跨 region replica lag 在新欄位上漂移   | expand 階段沒等所有 region 收斂      | 暫停 backfill、等 region 同步             |
| 某下游 service 沒 cutover              | cross-service 協調沒做 contract test | 補 contract test、推遲 contract 階段      |
| contract 前仍有舊欄位寫入              | 更新來源尚未完全收斂                 | 延後 contract，盤點寫入來源與 owner       |

這些訊號要放回服務路徑判讀。Mismatch 要看集中在哪個業務入口；若 mismatch 只出現在延遲付款 callback，它代表外部 provider 回呼語意未對齊。Replication lag 要看是否和 backfill 批次對位；若它只在 backfill 批次出現，gate 應調整 migration 節奏，再判斷 schema 設計是否需要修正。

Dual-write 跟 shadow read 的 divergence 要分開看 — 兩者偵測不同層的問題。Dual-write divergence 偏向 mapping bug 或 race condition；shadow read divergence 偏向讀取邏輯漂移或 stale read。混在同一個 dashboard 會讓 reviewer 看不出問題真正在哪一層。

## 常見誤區

把 schema migration 寫成 DDL 任務，會讓風險集中在切換當下。穩定做法是先建立相容窗口，再用 evidence 證明資料語意已經跟上，最後才收斂舊路徑。

把 validation query 當成事後對帳，也會削弱 rollout 控制。Validation query 適合在 expand、backfill、cutover 每一階段都產生證據，讓 release gate 能在風險擴大前停下來。

把 rollback 寫成單一動作容易誤導團隊。資料庫 migration 的 rollback 會隨階段改變：expand 可回退 schema 使用，backfill 可暫停與重跑，cutover 可回到 fallback read，contract 後多半只能做資料修復或 fail-forward。

把 dual-write 跟 shadow read 當成同一個工具。兩者偵測不同層、結合使用可以互補、互相替代會留下盲點。Dual-write 不跑 shadow read、cutover 後可能踩到沒驗過的讀取 path；shadow read 不跑 dual-write、新欄位可能在某些寫路徑根本沒被寫進去。

把線上 DDL 當「一個 SQL 跑完就好」。各 vendor 的 DDL 語意差異大、PostgreSQL 的 `ADD COLUMN NOT NULL DEFAULT` 在 PG 10 重寫整張表、PG 11+ 是 metadata-only；MySQL 不指定 `ALGORITHM=INSTANT` 可能掉回 COPY。Expand evidence 要包含 *實際 lock duration*、不是只看 DDL 是否回傳成功。

只在主寫入路徑切 cutover、忘記補償流程跟 reconciliation job 也會寫舊欄位。這些長尾寫入會在 contract 階段才暴露、那時候已經沒有 fallback 可走。Cutover 前要 audit 所有寫舊欄位的程式路徑、不只看主流程。

## 案例回寫

[0.C4 營運後技術轉換](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/) 可以回寫這篇的決策層。當服務營運後需要拆欄位、拆庫、分片或升級儲存引擎，先用 0.C4 判斷「為什麼要換」，再用本篇判斷「進入 production 後如何證明每一步成立」。

[GitHub 2018 Oct21 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/) 可以回寫這篇的事故層。該事件顯示資料一致性優先時，團隊需要可回放的 fail-forward / fail-back 判準；本篇則把這個需求落到 migration rollout 的 evidence、gate 與 decision log。

這兩個案例共同支撐的是「資料狀態演進需要證據閉環」。0.C4 提供轉換動機與選型壓力，GitHub 事故提供資料一致性與恢復決策的代價；兩者都不直接替代 validation query、release gate 與 decision log 的實作細節。

## 跨模組路由

1. 與 1.2 的交接：欄位責任、命名與查詢模型回到 [schema design](/backend/01-database/schema-design/)。
2. 與 1.3 的交接：付款回呼、手動修復與對帳更新的交易邊界回到 [transaction boundary](/backend/01-database/transaction-boundary/)。
3. 與 1.6 的交接：expand、backfill、cutover 與 contract 的執行流程回到 [資料庫轉換實作](/backend/01-database/database-migration-playbook/)。
4. 與 4.20 / 4.22 的交接：validation query、row count、lag 與 slow query 進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 與 [Checkout API Evidence Package](/backend/04-observability/checkout-api-evidence-package/)。
5. 與 6.11 / 6.8 / 6.25 的交接：migration 可逆性與放行條件進入 [Migration Safety](/backend/06-reliability/migration-safety/)、[Release Gate](/backend/06-reliability/release-gate/) 與 [Provider Dependency Release Gate](/backend/06-reliability/provider-dependency-release-gate/)。
6. 與 8.19 / 8.23 的交接：pause、rollback、fail-forward 與 write-back 進入 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/) 與 [Control Plane Decision Log and Write-back](/backend/08-incident-response/control-plane-decision-log-write-back/)。

## 下一步路由

要把資料庫 migration 的 evidence 交給 release gate，接著讀 [6.25 Provider Dependency Release Gate 實作示範](/backend/06-reliability/provider-dependency-release-gate/)，並把 provider 依賴示範中的 gate 欄位改寫成 migration gate 欄位。要看下一條分類服務路徑，接著進 [0.16 後端服務路徑實作細綱](/backend/00-service-selection/service-path-implementation-outlines/) 的 02 Cache / Redis：`Cache migration and stampede rollback`。
