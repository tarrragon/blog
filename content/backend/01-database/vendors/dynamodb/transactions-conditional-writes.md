---
title: "DynamoDB Transaction 與 Conditional Write：跨 item 原子性、optimistic locking 與 idempotency"
date: 2026-06-02
description: "DynamoDB 的寫原子性不是免費 ACID；本文展開 TransactWriteItems 跨 item 原子性、ConditionExpression 條件寫、version-based optimistic locking、ClientRequestToken idempotency，以及 transaction 2x 成本邊界與何時用單 item conditional write 取代 transaction"
weight: 35
tags: ["backend", "database", "dynamodb", "transaction", "conditional-write", "idempotency", "deep-article"]
---

> 本文是 [DynamoDB](/backend/01-database/vendors/dynamodb/) overview 的 implementation-layer deep article。寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

[對帳](/backend/knowledge-cards/data-reconciliation/)跑出一筆異常：用戶錢包餘額扣了 100 元、但對應訂單沒建立。追 log 發現 application 先 `PutItem` 扣餘額、再 `PutItem` 建訂單、兩步之間 process 被 OOM kill、第二步沒跑完。另一個系統反向情境：秒殺活動庫存剩 1、兩個請求同時讀到「剩 1」、各自 `PutItem` 扣成 0、實際賣出 2 件。兩個 production 痛點指向同一件事 — DynamoDB 預設的單筆寫入沒有跨 item 原子性、也沒有「讀到的值寫回時還沒被改」的保證。本文展開 DynamoDB 提供的三層寫保護：跨 item transaction、單 item conditional write、version-based optimistic locking。

> **寫一致性前提：先確認 workload 適配 DynamoDB**：本篇假設 workload 已通過 DynamoDB 適配 4 軸（PK 天然均勻 / control plane vs data plane / consistency 可接受 eventual / access pattern 穩定）— 判讀軸詳見 [single-table-design-pattern 開頭 4 軸前置判讀](../single-table-design-pattern/#dynamodb-適用度前置判讀4-軸)。寫一致性是 *已選 DynamoDB* 後的操作層議題；若 workload 需要頻繁跨多表多列複雜交易、那是 relational 的主場、應先回頭問 DynamoDB 是否選錯。

## 核心機制：三層寫保護

DynamoDB 的寫一致性由三種粒度不同的工具組成 — 單 item 寫、conditional write、跨 item transaction，三者解的問題與成本各異，不是單一 ACID 開關：

| 工具               | 解的問題                             | 原子性範圍                     | 成本                              |
| ------------------ | ------------------------------------ | ------------------------------ | --------------------------------- |
| 單 item 寫         | 一筆 item 的 put / update / delete   | 單 item                        | 1x WCU                            |
| Conditional write  | 只在條件成立時才寫（防覆蓋、防重複） | 單 item + 前置條件             | 1x WCU（條件不成立也計費）        |
| TransactWriteItems | 多筆 item 一起成功或一起失敗         | 跨 item（同 region / account） | 2x WCU（prepare + commit 兩階段） |

**TransactWriteItems 的工程語意**：

- 一次 transaction 最多含若干個 action（put / update / delete / condition check）— 上限屬 vendor 規格、實作時 cross-verify AWS doc 當前數字
- 全成功或全失敗：任一 action 的 condition 不成立、整個 transaction roll back、拋 `TransactionCanceledException` 帶 `CancellationReasons`
- 不跨 region、不跨 account：transaction 只在單一 region 單一 account 內成立、Global Tables 多 region 寫不享有跨 region transaction（對應 [global-tables-conflict](/backend/01-database/vendors/dynamodb/global-tables-conflict/)）
- 兩階段（prepare + commit）導致 2x capacity 消耗 — 這是 transaction 不能濫用的成本根源

> **Scope warning**：「TransactWriteItems 100 action 上限」、「transaction 2x WCU」這些具體數字屬 AWS vendor 規格、會隨版本調整、實作時 cross-verify 官方 doc 當前值。本文不含對應 production case 揭露的 transaction 規模數字。

對應 knowledge card：[idempotency](/backend/knowledge-cards/idempotency/)、[transaction boundary](/backend/knowledge-cards/transaction-boundary/)、[isolation level](/backend/knowledge-cards/isolation-level/)。

## Conditional Write：最便宜的一致性工具

跨 item transaction 之前、先看單 item conditional write 能不能解。多數「race condition」其實是單 item 問題、不需要 transaction 的 2x 成本。

ConditionExpression 在寫入前檢查條件、條件不成立則拒絕寫入並拋 `ConditionalCheckFailedException`：

```python
# 防重複建立：只有 item 不存在時才寫
table.put_item(
    Item={"PK": f"ORDER#{order_id}", "SK": "META", "status": "created"},
    ConditionExpression="attribute_not_exists(PK)"
)
```

```python
# 防超賣：只有庫存 > 0 時才扣
table.update_item(
    Key={"PK": f"SKU#{sku}", "SK": "STOCK"},
    UpdateExpression="SET stock = stock - :one",
    ConditionExpression="stock >= :one",
    ExpressionAttributeValues={":one": 1}
)
```

第二個例子是關鍵：`update_item` 帶 condition 是 *原子的 read-modify-write*。DynamoDB 在單 item 上保證「條件檢查 + 寫入」不會被其他寫入插隊。前述「兩個請求同時讀到剩 1」的超賣問題、用單 item conditional update 即可解、不需要 transaction。

## Optimistic Locking：跨讀寫週期的保護

Conditional write 解單次寫的 race；當 application 需要「讀出來、業務邏輯運算、再寫回」、且運算期間不能被別人改、用 version-based optimistic locking。

機制是在 item 上維護一個 `version` attribute、寫回時用 condition 確認 version 沒被改過：

```python
def update_with_optimistic_lock(pk, new_balance, expected_version):
    table.update_item(
        Key={"PK": pk, "SK": "WALLET"},
        UpdateExpression="SET balance = :b, version = version + :one",
        ConditionExpression="version = :expected",
        ExpressionAttributeValues={
            ":b": new_balance,
            ":one": 1,
            ":expected": expected_version,
        },
    )
```

讀出時拿到 `version=5`、運算後寫回時 condition 是 `version = 5`；若期間別人已寫成 `version=6`、condition 失敗、application 收到 `ConditionalCheckFailedException`、retry 整個讀-算-寫週期。

optimistic 的代價是衝突時要重試、不是阻塞等待。高衝突 workload（同一 item 大量並發寫）optimistic locking 會 retry 風暴、這時要回頭問資料模型 — 把熱點 item 拆開、或改用單 item atomic counter（`ADD`）避免 read-modify-write。

> **Scope warning**：optimistic locking 是通用並發控制 pattern、DynamoDB 用 ConditionExpression 實作；本段機制描述屬 vendor 規格 + 通用工程知識、非 production case 揭露。

## Idempotency：transaction 的重複提交保護

分散式系統的寫入會重試（network timeout、client retry）。同一筆 transaction 重送兩次、不能扣兩次款。DynamoDB transaction 提供 `ClientRequestToken` 做 dedup：

```python
client.transact_write_items(
    ClientRequestToken=request_id,  # 同 token 在 dedup window 內視為同一次
    TransactItems=[
        {"Update": {  # 扣錢包
            "TableName": "wallet",
            "Key": {"PK": {"S": f"USER#{uid}"}},
            "UpdateExpression": "SET balance = balance - :amt",
            "ConditionExpression": "balance >= :amt",
            "ExpressionAttributeValues": {":amt": {"N": str(amount)}},
        }},
        {"Put": {  # 建訂單
            "TableName": "orders",
            "Item": {"PK": {"S": f"ORDER#{order_id}"}, "amount": {"N": str(amount)}},
            "ConditionExpression": "attribute_not_exists(PK)",
        }},
    ],
)
```

同一個 `ClientRequestToken` 在 dedup window 內重送、DynamoDB 視為同一次、不會重複執行。這解掉開場的「扣款成功但訂單沒建」問題：兩個 action 在同一 transaction、要嘛都成、要嘛都不成；client 重試帶同 token、不會重複扣款。

> **Scope warning**：「ClientRequestToken dedup window 約 10 分鐘」屬 AWS vendor 規格、實作時 cross-verify 官方 doc；application 層仍應有自己的 idempotency key 設計、不依賴 vendor dedup window 當唯一防線（對應 [idempotency](/backend/knowledge-cards/idempotency/) 卡）。

## 操作流程

從一致性需求判讀到工具選擇的 6 步流程。

#### Step 1：分類寫入的一致性需求

每個寫入路徑標記它真正需要的保護：

- 單筆獨立寫、無前置條件 → 單 item put / update（最便宜）
- 單筆寫但要防覆蓋 / 防重複 / 防超賣 → 單 item conditional write
- 讀-算-寫週期、期間不能被改 → version optimistic locking
- 多筆 item 必須一起成功或失敗 → TransactWriteItems

#### Step 2：先用 conditional write 解單 item race

把「需要 transaction」當成最後選項。多數 race condition 是單 item 問題、conditional update 的 atomic read-modify-write 已足夠、成本 1x 而非 2x。

#### Step 3：跨 item 才上 transaction

只有「多筆 item 的修改必須綁在一起」才用 TransactWriteItems。例：扣錢包 + 建訂單 + 寫流水帳三筆綁定。寫進 transaction 的 item 數量越少越好、每多一個 item 多一份 2x 成本。

#### Step 4：加 idempotency token

所有會被 client 重試的 transaction 帶 `ClientRequestToken`；token 用業務層的唯一鍵（order_id / request_id）、不要用隨機值（隨機值每次重試都不同、dedup 失效）。

#### Step 5：處理失敗例外

```python
from botocore.exceptions import ClientError

try:
    client.transact_write_items(...)
except ClientError as e:
    code = e.response["Error"]["Code"]
    if code == "TransactionCanceledException":
        reasons = e.response["CancellationReasons"]  # 逐 action 失敗原因
        # 區分 ConditionalCheckFailed（業務拒絕、不重試）
        # vs TransactionConflict / ThrottlingError（可重試）
    elif code == "ConditionalCheckFailedException":
        pass  # 單 item condition 失敗、業務層決定
```

關鍵：`ConditionalCheckFailed` 是 *業務拒絕*（庫存不足、訂單已存在）、不該不分原因一律重試；`TransactionConflict` / `ThrottlingError` 才是可重試的 transient error。混為一談會把「庫存真的不夠」當成 transient 一直重試。

#### Step 6：驗證點

```python
# 驗證 conditional write 真的擋住併發
# 啟兩個並發 update 扣同一庫存、確認只有一個成功、另一個拋 ConditionalCheckFailed
response = table.update_item(..., ReturnValues="UPDATED_NEW")
print(response["Attributes"])  # 確認 version / stock 變化符合預期
```

**Rollback boundary**：transaction 本身全成全敗、無 partial state 需要 rollback；但 application 層若在 transaction 外還有副作用（送通知、呼叫外部 API）、那些不在 transaction 保護內、要另行設計補償。

## 失敗模式

production 常見的 5 個踩雷：

#### Case 1：用 transaction 取代本該單 item 的寫

team 把所有寫入都包進 TransactWriteItems「保險」、cost 翻倍、且 transaction 有 throughput 上限比單寫低。修法：transaction 只用於真正跨 item 綁定的場景；單 item 用 conditional write。

#### Case 2：optimistic lock 在高衝突 item 上 retry 風暴

熱點 item（如全站唯一的計數器）大量並發寫、version condition 不斷失敗、application retry 風暴、latency 爆炸。修法：高衝突計數改用 atomic `ADD`（單 item 原子累加、不需 read-modify-write）；或把計數 shard 成多個 item 分散寫入。

#### Case 3：idempotency token 用隨機值

這個 case 的失敗代價跟其他踩雷不同層級。Case 1（cost 翻倍）、Case 2（retry 風暴）、Case 5（跨 region 誤解）都可以在發現後調整設定或改資料模型補救；idempotency token 用隨機值導致的重複扣款是 *財務不可逆* — 每次 client retry 產生新 token、dedup 完全失效、同一筆付款被執行多次、錢已經從用戶帳戶扣走、要靠對帳發現後人工退款，且退款流程本身又是另一條容易出錯的補償路徑。修法：token 綁業務唯一鍵（order_id / payment_id）、同一筆業務操作的所有重試共用同一 token；且不只依賴 DynamoDB 的 dedup window（有時效上限），application 層自己也維護 idempotency 記錄當第二道防線（對應 [idempotency](/backend/knowledge-cards/idempotency/) 卡）。涉及金流的寫入，這道防線要在上線前用「同一 token 重送 N 次只執行一次」的測試明確驗證。

#### Case 4：把 ConditionalCheckFailed 當 transient error 重試

庫存真的為 0、condition 永遠失敗、application 無限重試打爆 capacity。修法：例外分流 — 業務拒絕（ConditionalCheckFailed）回報給呼叫端、transient error（throttle / conflict）才 backoff retry。

#### Case 5：以為 transaction 跨 region 有效

Global Tables 多 region 部署、誤以為 TransactWriteItems 在跨 region 也原子。實際 transaction 只在單 region 成立、跨 region 是 last-writer-wins（對應 [global-tables-conflict](/backend/01-database/vendors/dynamodb/global-tables-conflict/)）。修法：跨 region 一致性需求不能靠 transaction、要重新設計資料 ownership（單一 region 為 write authority）。

**Anti-recommendation**：寫入無併發競爭、或業務本身可接受最終一致（各 message_id 獨立的訊息事件即屬此類）→ 不要為了求保險而加 transaction；transaction 的 2x 成本只在真正需要跨 item 原子性時才值得。

## 容量與觀測

CloudWatch metric：

- `TransactionConflict`：transaction 因併發衝突取消的次數、持續高代表熱點 item 競爭
- `ConditionalCheckFailedRequests`：condition 失敗次數、區分業務拒絕 vs 設計問題
- `ThrottledRequests`：transaction 因 capacity 不足被限流、transaction 的 2x 消耗更容易撞上限

**判讀**：

- `TransactionConflict` 持續上升 → 資料模型有熱點、考慮拆 item 或改 atomic counter
- `ConditionalCheckFailed` 突然飆高 → 可能是業務異常（大量重複請求 / 攻擊）、也可能是 application 邏輯把 version 算錯
- transaction 的 capacity 用量按 2x 計、容量規劃要把 transaction 比例算進去

> **Scope warning**：本文未引用 production case 的 transaction metric 數字；上述 metric 名稱與判讀屬 vendor 規格 + 通用觀測工程。

接回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)、[1.3 transaction 與一致性邊界](/backend/01-database/transaction-boundary/)。

## 邊界與整合

### 跟 relational transaction 的責任差異

DynamoDB transaction 跟 relational transaction 不是同一個東西。Relational transaction 支援任意複雜的多表多列交易、長交易、isolation level 調整；DynamoDB transaction 是「一次性提交一組有限 action、全成全敗、無互動式 transaction、無 SELECT FOR UPDATE」。當 application 需要長交易、複雜 join 內的一致性、或多步互動式 transaction、那是 relational 的場景、不該硬塞進 DynamoDB（回頭看 single-table 4 軸前置判讀）。

### Sibling 與 cross-link

- [consistency-model-optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/) — 該篇主寫 *讀* 一致性（eventual vs strong read）、本篇主寫 *寫* 原子性、兩篇互補
- [single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/) — 跨 item transaction 常用於 single-table 內多 entity 綁定寫
- [global-tables-conflict](/backend/01-database/vendors/dynamodb/global-tables-conflict/) — transaction 不跨 region、多 region 寫衝突另有處理
- [streams-lambda-event-driven](/backend/01-database/vendors/dynamodb/streams-lambda-event-driven/) — transaction 寫入會觸發 stream、下游 event 處理要 idempotent
- 替代路由：頻繁複雜交易需求 → 回 [PostgreSQL](/backend/01-database/vendors/postgresql/) / [Aurora](/backend/01-database/vendors/aurora/)、relational transaction 是主場
- 對應 [1.9 Reconciliation 與 Data Repair](/backend/01-database/reconciliation-data-repair/) — 寫一致性失守後的對帳與修復
