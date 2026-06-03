---
title: "DynamoDB Streams 與 Lambda 事件驅動：CDC、shard 順序保證、消費模式與失敗處理"
date: 2026-06-02
description: "DynamoDB Streams 不是免費的可靠事件流；本文展開 stream record 的四種 view type、shard 對應 partition 的順序保證邊界、Lambda event source mapping vs Kinesis 消費模式、at-least-once 下游冪等需求，以及 batch 失敗時的 bisect / DLQ 處理"
weight: 37
tags: ["backend", "database", "dynamodb", "streams", "cdc", "event-driven", "lambda", "deep-article"]
---

> 本文是 [DynamoDB](/backend/01-database/vendors/dynamodb/) overview 的 implementation-layer deep article。寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

訂單寫進 DynamoDB 後、搜尋索引要更新、快取要失效、要推一筆通知、要寫一筆 audit。第一版 application 在寫訂單的同一段 code 裡同步做完這四件事、結果單一步驟（推通知的外部 API）變慢、整個寫訂單路徑被拖垮。第二版改成「另一個 service 每 10 秒輪詢 table 撈新資料」、輪詢既貴（全表 scan）又慢（最差 10 秒延遲）。兩個痛點都指向同一個缺口 — 資料變更需要一條可靠、低延遲、不污染寫路徑的下游通道。這正是 DynamoDB Streams 的責任。本文展開 Streams 的 record 結構、順序保證的真實邊界、消費模式選擇與失敗處理。

> **事件機制前提：先確認 workload 適配 DynamoDB**：事件驅動機制是已選 DynamoDB 後的議題；選型本身先過 workload 適配 4 軸 — PK 天然均勻 / control plane vs data plane / consistency 可接受 eventual / access pattern 穩定。判讀軸詳見 [single-table-design-pattern 開頭 4 軸前置判讀](../single-table-design-pattern/#dynamodb-適用度前置判讀4-軸)。本文聚焦 *已選 DynamoDB* 後、把資料變更導向下游的事件機制。

## 核心機制：Stream record 與 view type

DynamoDB Streams 是 table 的 [change data capture](/backend/knowledge-cards/change-data-capture/) 通道 — 把 item 層級的 insert / modify / delete 變成一條時間排序的事件流。開啟後、每筆寫入產生一筆 stream record。

**view type 決定 record 帶什麼**：

| StreamViewType       | record 內容          | 典型用途                    |
| -------------------- | -------------------- | --------------------------- |
| `KEYS_ONLY`          | 只有被改 item 的 key | 下游自己回查、最省          |
| `NEW_IMAGE`          | 寫入後的完整新 item  | 同步到搜尋索引 / 快取       |
| `OLD_IMAGE`          | 寫入前的舊 item      | audit「改了什麼」、刪除留底 |
| `NEW_AND_OLD_IMAGES` | 新舊都帶             | 算 diff、條件性下游處理     |

view type 在開 stream 時定、改要重開 stream。選 `NEW_AND_OLD_IMAGES` 最方便但 record 最大（影響 Lambda payload 與成本）；下游只需 key 就回查的、選 `KEYS_ONLY`。

> **Scope warning**：「stream record 保留 24 小時」、「Lambda 單次 batch 上限」這些屬 AWS vendor 規格、會隨版本調整、實作時 cross-verify 官方 doc。本文不含 production case 揭露的 stream 配置數字。

對應 knowledge card：[change-data-capture](/backend/knowledge-cards/change-data-capture/)、[idempotency](/backend/knowledge-cards/idempotency/)。

## 順序保證的真實邊界

這是 Streams 最常被誤解的點 — 「stream 是有序的」這句話只在特定範圍成立。

**保證範圍**：

- stream 切成多個 shard、每個 shard 對應 table 的一組 partition
- **同一 partition key 的所有變更、進同一個 shard、在 shard 內嚴格時間排序**
- 跨 shard *沒有* 全域順序保證

這代表：同一筆訂單（同 PK）的 create → update → delete 一定按序到下游；但訂單 A 跟訂單 B（不同 PK、可能不同 shard）的相對順序不保證。下游若依賴「跨實體的全域順序」、會踩雷。

**shard split / merge**：

table partition 會隨資料量與流量 split、stream shard 跟著變動。消費端要能處理 shard 生命週期（Lambda event source mapping 自動處理；自己用 SDK 拉的要處理 shard iterator 的 parent-child 關係）。

**順序 + 冪等的組合**：

Lambda 消費 stream 是 *at-least-once* — 同一筆 record 可能被送兩次（retry、shard 重平衡）。下游處理必須冪等：用 record 的 sequence number 或業務鍵去重、不能假設「每筆只處理一次」。每筆訊息帶獨立 message_id 的事件流天然適合 — message_id 當冪等鍵、重送不重複發。

> **Scope warning**：上述順序與 at-least-once 語意屬 Streams vendor 規格 + 通用事件處理工程、非 production case 揭露。

## 消費模式：Lambda vs Kinesis

兩條主要消費路徑、責任與運維成本不同：

| 維度      | Lambda event source mapping  | Kinesis Data Streams for DynamoDB |
| --------- | ---------------------------- | --------------------------------- |
| 模式      | push（DynamoDB 觸發 Lambda） | pull（消費端自己拉）              |
| retention | stream 原生較短              | 較長（可重播更久）                |
| 消費者數  | 適合單一 / 少量消費者        | 適合多消費者 fan-out              |
| 運維      | 幾乎零（managed trigger）    | 要管 Kinesis consumer / KCL       |
| 重播能力  | 受 stream retention 限制     | retention 內可重播                |

多數「寫入後觸發一個下游動作」用 Lambda event source mapping 最簡單。需要長 retention、多消費者 fan-out、或要重播歷史變更的、用 Kinesis Data Streams for DynamoDB。

**Lambda event source mapping 的關鍵旋鈕**：

- batch size：一次給 Lambda 幾筆 record（吞吐 vs 延遲）
- batch window：湊滿 batch 或等多久才觸發（低流量時的延遲控制）
- parallelization factor：一個 shard 並行幾個 Lambda（提升單 shard 吞吐、但犧牲 shard 內嚴格順序）

> **Scope warning**：parallelization factor > 1 會在單 shard 內並行處理、放寬順序保證；需要嚴格順序的維持 factor = 1。具體上限屬 vendor 規格。

## 操作流程

從開 stream 到下游上線的 6 步流程。

#### Step 1：選 view type

依下游需要什麼決定。同步到搜尋索引要完整新 item → `NEW_IMAGE`；audit 要看改動 → `NEW_AND_OLD_IMAGES`；下游自己回查 → `KEYS_ONLY`。

#### Step 2：開 stream

```bash
aws dynamodb update-table \
  --table-name orders \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES
```

#### Step 3：接 Lambda event source mapping

```python
def handler(event, context):
    for record in event["Records"]:
        event_name = record["eventName"]      # INSERT / MODIFY / REMOVE
        if event_name == "REMOVE":
            old = record["dynamodb"]["OldImage"]
            delete_from_search_index(old)
        else:
            new = record["dynamodb"]["NewImage"]
            upsert_to_search_index(new)
        # 冪等：用 sequence number 或業務鍵去重
        seq = record["dynamodb"]["SequenceNumber"]
```

#### Step 4：設定 batch 與失敗處理

```text
BatchSize: 依下游處理能力與延遲目標
MaximumBatchingWindowInSeconds: 低流量湊批、控制延遲
BisectBatchOnFunctionError: true   # 失敗時二分批、隔離壞 record
MaximumRetryAttempts: 有限次       # 避免毒丸 record 無限重試
DestinationConfig.OnFailure: DLQ   # 超過重試送 DLQ
```

#### Step 5：下游冪等設計

下游 upsert 用業務鍵（PK）做 idempotent write、刪除用「刪不存在不報錯」；確保同一 record 處理兩次結果相同。

#### Step 6：驗證點

```python
# 灌一筆寫入、確認下游在預期延遲內收到對應 record
# CloudWatch: Lambda IteratorAge（消費落後程度）應接近 0
# 製造一筆會失敗的 record、確認進 DLQ 而非卡住整個 shard
```

**Rollback boundary**：關 stream 即停止產生新 record；已產生的 record 在 retention 內仍存在。下游邏輯出錯時、修好 Lambda 後可在 retention 內讓未處理 record 重新消費（或從 DLQ 重放）。

## 失敗模式

production 常見的 5 個踩雷：

#### Case 1：下游非冪等、重送導致重複副作用

at-least-once 重送、下游每次都發一筆通知、用戶收到重複推播。修法：下游用業務鍵冪等、sequence number 去重；副作用（發通知 / 扣款）必須 idempotent。

#### Case 2：依賴跨實體全域順序

下游假設「所有訂單事件按全域時間到達」、實際跨 shard 無此保證、算錯聚合。修法：只依賴「同 PK 內有序」；需要跨實體順序的、在下游用 event timestamp 重排、或重新設計不依賴全域順序。

#### Case 3：毒丸 record 卡住整個 shard

某筆 record 讓 Lambda 永遠拋例外、預設行為是重試整個 batch、shard 卡死、IteratorAge 無限上升。修法：開 `BisectBatchOnFunctionError` + `MaximumRetryAttempts` + DLQ、隔離壞 record 讓其餘繼續。

#### Case 4：consumer 落後、record 過期遺失

下游處理太慢、IteratorAge 超過 stream retention、未處理 record 被清掉。這個 Case 的代價跟前三個不同層級：前三個是「重複副作用 / 算錯聚合 / shard 卡住」、都還在 stream 裡留有 record、修好邏輯後可重新消費或從 DLQ 重放。Case 4 是 record 本身已被 retention 清除、那段時間的資料變更在 stream 這條通道上永久消失、沒有回退路徑。要補回只能反向比對 table 當前狀態跟下游狀態（若下游存得了），或在源頭重跑一次寫入觸發新 record — 兩者都是事故後的人工修復、成本遠高於前三個 Case 的設定旋鈕。

因為不可逆、防線要前置在「逼近 retention 之前」而非「過期之後」：IteratorAge alarm 的閾值設在遠低於 retention 的水位、留出擴容反應時間；吞吐不足時加 parallelization factor 或改 Kinesis（更長 retention、爭取更大的落後緩衝）；下游設計要能水平擴、讓落後可被快速追平。

#### Case 5：parallelization factor 開了還抱怨順序錯

為提吞吐把 factor 開 > 1、又依賴 shard 內嚴格順序、兩者矛盾。修法：需要嚴格順序維持 factor = 1；要並行吞吐就接受順序放寬、或把順序敏感的處理移到下游用 PK 分組。

**Anti-recommendation**：只有單一同步下游、且寫路徑延遲容忍度高 → 直接在 application 寫入後同步處理可能更簡單、不必引入 stream 的運維與冪等複雜度。Streams 的價值在「多下游 / 解耦寫路徑 / 低延遲 CDC」。

## 容量與觀測

CloudWatch metric：

- `IteratorAge`（Lambda）：消費落後程度、最關鍵指標、持續上升代表下游跟不上
- Lambda `Errors` / `Throttles`：下游處理失敗 / 被限流
- DLQ 訊息數：毒丸 record 累積、需要人工介入
- stream `ReadProvisionedThroughputExceeded`（Kinesis 模式）：消費端讀超限

**判讀**：

- `IteratorAge` 接近 retention 上限 → 資料變更即將遺失、緊急擴消費端
- DLQ 持續累積 → 有系統性壞 record、查 Lambda 邏輯或上游資料
- Errors 尖峰但 IteratorAge 正常 → transient 失敗、retry 有在吸收

> **Scope warning**：本文未引用 production case 的 stream metric 數字；上述指標與判讀屬 vendor 規格 + 通用事件處理觀測。

接回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)、[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)。

## 邊界與整合

### Streams 跟 03 訊息佇列的責任切分

DynamoDB Streams 是 *資料庫變更* 的 CDC 通道、不是通用訊息佇列。兩者責任不同：

- **Streams**：源頭是 table 寫入、record 由 DynamoDB 自動產生、生命週期綁 table、retention 短
- **訊息佇列（SQS / SNS / Kafka）**：源頭是 application 主動 publish、用於通用解耦、retention 與語意更彈性

典型組合：Streams 捕捉 table 變更 → Lambda 處理 → 需要扇出到多個獨立服務時、再 publish 到 SNS / EventBridge。當事件來源不是「資料庫變更」而是「業務事件」、直接用 [03 訊息佇列模組](/backend/03-message-queue/) 的 queue / topic、不要硬塞進 table 再用 stream。

### Sibling 與 cross-link

- [transactions-conditional-writes](/backend/01-database/vendors/dynamodb/transactions-conditional-writes/) — transaction 寫入也觸發 stream、下游處理要冪等
- [single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/) — single-table 下不同 entity 共用 stream、下游用 type 欄位分流
- [global-tables-conflict](/backend/01-database/vendors/dynamodb/global-tables-conflict/) — Global Tables 跨 region 複製本身基於 stream 機制
- 替代路由：通用業務事件 / 多消費者扇出 / 長 retention → [03 訊息佇列模組](/backend/03-message-queue/)
- 搜尋索引同步下游 → OpenSearch / Elasticsearch（DynamoDB 不適合做全文檢索）
- 跟 [PayPay 9.C26](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/) 互引：訊息事件 message_id 天然冪等、適合 stream 下游處理
