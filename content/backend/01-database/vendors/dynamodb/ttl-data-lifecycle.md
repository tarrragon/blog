---
title: "DynamoDB TTL 資料生命週期：自動過期、數天內的刪除延遲、過期仍可讀與 storage 成本"
date: 2026-06-02
description: "DynamoDB TTL 不是即時刪除也不是查詢過濾器；本文展開 TTL attribute 的 epoch 語意、AWS 背景刪除的延遲特性、過期但未刪 item 仍會被讀到且仍計費的陷阱、TTL 刪除免 WCU 與觸發 stream 的整合，含 PayPay 訊息過期清理的案例"
weight: 38
tags: ["backend", "database", "dynamodb", "ttl", "data-lifecycle", "cost-optimization", "deep-article"]
---

這篇整理 [DynamoDB](/backend/01-database/vendors/dynamodb/) TTL 管理資料生命週期的方式：TTL attribute 的 epoch 語意、背景刪除的延遲、過期但未刪的 item 仍可讀的窗口、TTL 刪除與 stream 的整合，以及 storage 成本的判讀。

DynamoDB TTL 是 *最終會刪除* 的背景機制，不是即時刪除，也不是查詢層的過濾器。設了 TTL 之後 storage 不會馬上下降，要等背景程序實際刪除；而在過期到刪除之間，item 仍會被查詢讀到，報表 query 沒有自行排除過期 item 時，就會把它們算進數字裡。

> **生命週期前提：先確認 workload 適配 DynamoDB**：資料生命週期管理是 *已選 DynamoDB* 之後才浮現的議題 — TTL 解的是「資料存進來之後怎麼自動退場」、而非「資料該不該存進 DynamoDB」。後者由 4 軸前置判讀決定：PK 天然均勻 / control plane vs data plane / consistency 可接受 eventual / access pattern 穩定、判讀軸詳見 [single-table-design-pattern 開頭 4 軸前置判讀](../single-table-design-pattern/#dynamodb-適用度前置判讀)。本文承接該前提、聚焦用 TTL 管理資料生命週期與 storage 成本。

## 核心機制：TTL attribute 與背景刪除

DynamoDB TTL 讓 item 在指定時間後自動被刪除、不消耗寫容量。機制很簡單，但語意上有三個容易踩的邊界：刪除非即時、過期仍可讀、刪除免 WCU。

**設定方式**：在 item 上放一個數值 attribute、值是 *Unix epoch 秒數*（不是毫秒、不是 ISO 字串）、並在 table 啟用 TTL 指向該 attribute：

```python
import time
table.put_item(Item={
    "PK": f"MSG#{msg_id}",
    "SK": "META",
    "body": "...",
    "expireAt": int(time.time()) + 30 * 86400,  # 30 天後過期、epoch 秒
})
```

**三個關鍵語意**：

| 語意       | 內容                                                       | 後果                              |
| ---------- | ---------------------------------------------------------- | --------------------------------- |
| 刪除非即時 | 過期後由 AWS 背景程序刪除、通常在過期後數天內、不保證準時  | 不能用 TTL 做即時失效邏輯         |
| 過期仍可讀 | 過期但尚未被刪的 item 仍出現在 GetItem / Query / Scan 結果 | read 路徑要 application 端 filter |
| 刪除免 WCU | TTL 刪除不消耗 write capacity                              | 大量過期清理不增寫成本            |

「過期仍可讀」那一列是報表算錯的根因：**TTL 不是查詢過濾器**。過期到實際刪除之間有一段窗口、這期間 item 還在、還會被讀到。需要「過期立刻不可見」的、application 必須在讀取後自己比對 `expireAt` 過濾。

> **Scope warning**：「TTL 通常在過期後數天內刪除」屬 AWS vendor 規格描述（截至 2026-09 的官方文件原文為 typically within a few days）、AWS 不保證準時、實際延遲視 table 大小與背景負載而定、實作時 cross-verify 官方 doc。`9.C26 PayPay` case 揭露「TTL 機制可自動清理過期訊息」的 *用途*、未揭露刪除延遲的具體數字。

對應 knowledge card：[ttl](/backend/knowledge-cards/ttl/)、[soft-ttl](/backend/knowledge-cards/soft-ttl/)。

## 過期可讀窗口與 TTL 刪除的 stream record

TTL 的「最終刪除」特性帶出兩件 application 要處理的事：過期到實際刪除之間的可讀窗口，以及 TTL 刪除時產生的 stream record。

**可讀窗口：過期 → 實際刪除**：

item 的 `expireAt` 已過、但背景程序還沒刪。這段時間 item：

- 仍會被 `Query` / `Scan` / `GetItem` 撈到
- 仍佔 storage、仍計 storage 費
- 仍會被 secondary index 索引到

application 若依賴「過期就消失」、會在這個窗口讀到 stale 資料。正確做法是 read 後 filter：

```python
import time
now = int(time.time())
items = [it for it in response["Items"] if it.get("expireAt", 1 << 62) > now]
```

或在 query 加 `FilterExpression` 排除過期 item（注意 filter 在讀取後套用、仍消耗讀容量）。

**TTL 刪除產生的 stream record**：

TTL 刪除會在 stream 產生一筆 `REMOVE` record、且 `userIdentity` 標記為 DynamoDB 服務本身（principal `dynamodb.amazonaws.com`）。這讓「過期歸檔」成為可能 — 下游 Lambda 收到 TTL 刪除事件、把 item 寫進冷儲存（S3）再讓它從 hot table 消失：

```python
def handler(event, context):
    for record in event["Records"]:
        if record["eventName"] == "REMOVE":
            principal = record.get("userIdentity", {}).get("principalId")
            if principal == "dynamodb.amazonaws.com":  # TTL 刪除、非 application 刪除
                archive_to_s3(record["dynamodb"]["OldImage"])
```

區分「TTL 自動刪除」vs「application 主動刪除」靠 `userIdentity` — 兩者都是 `REMOVE` record、但只有 TTL 刪除帶服務 principal。對應 [streams-lambda-event-driven](/backend/01-database/vendors/dynamodb/streams-lambda-event-driven/)。

> **Scope warning**：stream record 的 `userIdentity` 標記屬 vendor 規格、欄位細節 cross-verify 官方 doc；本段機制描述非 production case 揭露。

## 操作流程

從生命週期需求到上線的操作流程：判斷資料是否適合 TTL、設計 expireAt 計算、啟用 table TTL、在 read 路徑加過期過濾、（可選）接 TTL 刪除歸檔、驗證過期與刪除的行為。

#### 判斷資料是否適合 TTL 管理

適合 TTL 的資料有「自然過期時間」：session、訊息通知、暫存 token、event log、合規保留期到期的資料。不適合的：需要精確即時刪除的、需要刪除前審批的、永久保存的。

#### 設計 expireAt 計算

寫入時算好 epoch 秒數的 `expireAt`；不同資料類型可不同保留期（通知 30 天、session 1 天、audit 依合規要求）。

#### 啟用 table TTL

```bash
aws dynamodb update-time-to-live \
  --table-name messages \
  --time-to-live-specification "Enabled=true, AttributeName=expireAt"
```

#### read 路徑加過期過濾

所有面向用戶的讀取、在 application 端比對 `expireAt`（或加 FilterExpression）；不要假設過期 item 已消失。

#### （可選）接 TTL 刪除歸檔

需要保留過期資料的、接 stream Lambda、用 `userIdentity` 辨識 TTL 刪除、歸檔到 S3。

#### 驗證過期與刪除的行為

```python
# 寫一筆短 TTL item、等過期後確認：
# 1. 過期但未刪窗口內仍可讀到（驗證需要 filter）
# 2. 數小時後背景刪除生效、storage 下降
# 3. 若接歸檔、確認 S3 收到對應 OldImage
```

**Rollback boundary**：關閉 TTL 即停止自動刪除、已刪除的 item 不可恢復（除非有歸檔）；啟用 TTL 前先確認 `expireAt` 計算正確、避免誤設過短把活躍資料刪掉。

## 失敗模式

production 常見的 5 個踩雷：

#### expireAt 用毫秒或 ISO 字串

TTL 只認 Unix epoch 秒；填毫秒（多三位數）會讓過期時間落在遙遠未來、item 永不過期；填字串 TTL 直接不生效。修法：統一用 `int(time.time()) + seconds`、寫測試驗證 attribute 是秒級數值。

#### 以為 TTL 是即時刪除、做即時失效邏輯

用 TTL 當「到點立刻不可用」的開關（如優惠券到期）、實際過期後幾小時還能用。修法：即時失效靠 application 邏輯比對時間、TTL 只負責 *清理 storage*、兩者分開。

#### 報表 / 對帳撈到過期未刪 item

聚合 query 沒過濾過期 item、把可讀窗口內的殘留資料算進去。修法：所有讀取路徑一致地過濾 `expireAt`；[對帳](/backend/knowledge-cards/data-reconciliation/)查詢明確排除過期。

#### 誤設過短保留期刪掉活躍資料

誤設過短保留期的失敗代價跟本節其他踩雷不同層級。其他踩雷多半可回復 — `expireAt` 單位填錯讓 storage 緩漲，可回填正確的 `expireAt`；過期未刪被讀到，可在讀取路徑加 filter；GSI 裡的過期殘留會隨背景刪除自然消退。誤設過短保留期則是 *不可逆* 的：`expireAt` 計算 bug（少乘 86400、用錯時區基準）把保留期算成幾小時、背景程序把仍在使用的活躍資料當成過期 item 刪除、而 TTL 刪除不寫 undo log、刪掉就沒有從 DynamoDB 端救回的途徑、只能靠外部備份（PITR / 另存的 stream archive）回灌、且回灌期間資料缺口已經對線上服務造成影響。

代價的關鍵在於計算錯誤的爆炸半徑：一個錯誤常數會同時套用到所有新寫入 item、刪除是持續發生的背景行為、發現時往往已刪掉大批資料。修法的重心因此放在 *上線前驗證* 而非事後補救：上線前在 staging 用短週期資料驗證 `expireAt` 算出的絕對時間點符合預期、TTL 啟用初期把 `TimeToLiveDeletedItemCount` 跟預估刪除量對照、刪除量明顯偏高就立即停用 TTL 並排查計算、不等 storage 趨勢確認。對保留期敏感的 table 先開 PITR 當不可逆操作的最後防線。

#### 過期 item 仍被 GSI 索引、推高 index 成本

過期未刪 item 仍佔 GSI storage；大量過期堆積時 GSI 成本沒因「邏輯過期」下降。修法：理解 GSI 跟著 base item 生命週期、storage 降要等實際刪除；對成本敏感的 sparse index 設計可讓過期 item 不進 GSI（對應 [gsi-lsi-design sparse index](/backend/01-database/vendors/dynamodb/gsi-lsi-design/)）。

**Anti-recommendation**：資料量小、storage 成本可忽略、或刪除需要審批/合規記錄 → 不必用 TTL；手動或排程刪除更可控。TTL 的價值在「大量有自然過期時間的資料、要低成本自動清理」（如 PayPay 式每日上億訊息）。

## 容量與觀測

CloudWatch metric：

- `TimeToLiveDeletedItemCount`：TTL 背景刪除的 item 數、確認 TTL 真的在運作
- table `ItemCount` / storage size：長期趨勢、確認過期清理讓 storage 趨於穩態
- 過期未刪比例：自行用 `expireAt < now` 的 item 數估算可讀窗口殘留量

**判讀**：

- `TimeToLiveDeletedItemCount` 為零但有設過期資料 → TTL 沒生效（attribute 名稱錯 / 值格式錯）
- storage 持續上漲且 TTL 刪除量遠小於寫入量 → 保留期設太長、或寫入遠超過期速度、要重估保留策略
- 大量過期未刪堆積 → 背景刪除跟不上寫入、storage 成本被殘留拉高

> **Scope warning**：`9.C26 PayPay` 的「3 億/天 × 30 天 = 90 億筆」是 PayPay 案例頁的策略段推算、非 PayPay 官方揭露的精確 item 數；引用時當量級壓力 anchor、不當精確數字。

接回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)。

## 邊界與整合

### TTL vs cache TTL vs 合規保留

「TTL」這個詞在不同層意義不同、不要混用：

- **DynamoDB TTL**：主資料的生命週期管理、最終刪除、本篇主寫
- **cache TTL**（如 DAX item / query cache、Redis TTL）：快取副本的新鮮度邊界、過期是「重新回源」不是「刪除主資料」、主寫於 [02 快取模組](/backend/02-cache-redis/) 與 [dax-caching-strategy](/backend/01-database/vendors/dynamodb/dax-caching-strategy/)
- **合規保留期**：法規要求的最短/最長保存、可用 TTL 實作到期清理、但刪除前的稽核記錄要另外保留（對應 [7.7 audit trail](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)）

### Sibling 與 cross-link

- [streams-lambda-event-driven](/backend/01-database/vendors/dynamodb/streams-lambda-event-driven/) — TTL 刪除觸發 stream REMOVE record、用 userIdentity 辨識、可做過期歸檔
- [single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/) — single-table 下不同 entity 用不同 expireAt 保留期
- [gsi-lsi-design](/backend/01-database/vendors/dynamodb/gsi-lsi-design/) — 過期未刪 item 仍佔 GSI、sparse index 可讓過期不進 GSI
- [on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/) — TTL 刪除免 WCU、不影響寫容量規劃、但 storage 成本要靠 TTL 控制
- 替代路由：快取副本新鮮度 → [02 快取模組](/backend/02-cache-redis/)；合規稽核 → [7.7 audit trail](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)
- [PayPay：行動支付每日 3 億訊息的 DynamoDB 後端](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/)：每日上億訊息用 TTL 自動清理、避免 storage 無限增長的案例
