---
title: "1.13 應用層查詢反模式與 Query 預算"
date: 2026-05-27
description: "整理 N+1、select *、缺索引、ORM lazy load、long transaction 等查詢反模式與每請求的 query 預算判讀"
weight: 13
tags: ["backend", "database", "query", "anti-patterns"]
---

這篇整理應用程式發給資料庫的查詢裡常見的反模式——N+1、`SELECT *`、缺索引、ORM lazy load、長 transaction——各自的徵兆、判讀方式與修法，並提出「每請求的 query 預算」作為發布前的檢查標準。

查詢本身的語意為什麼是這樣——連接讓列數變多、條件放 `ON` 與放 `WHERE` 差在哪、`IN` 與 `EXISTS` 各自描述什麼——在 [SQL 分類](/backend/01-database/sql/)。本章處理的是寫對之後的次數與代價。

## 為什麼查詢反模式比 vendor 細節更重要

多數團隊面對「資料庫變慢」時，會先去看 vendor 的調校（buffer pool、配置升級、replica 加開）。這些調校通常把基礎效能拉高 1-2 倍；一個 N+1 query 反模式可以讓回應時間慢 10-1000 倍（具體倍數取決於 N 跟 RTT — N=100 + RTT=1ms 約慢 100 倍）。先解掉應用層的反模式、再去調 vendor 配置，整體效益遠高於反過來。

這條優先序也對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 的精神：先定位真正的瓶頸再決定是否加資源。應用層 query 是最常被忽略的瓶頸來源。

## N+1 Query：最常見也最隱性的反模式

N+1 query 指「先發一個 query 取回 N 筆資料、再對每一筆各發一個 query 取相關資料」，總共 1 + N 次 round trip。N 越大、整體越慢。

典型範例：列出 100 筆訂單與每筆訂單的客戶名稱。N+1 的寫法先取訂單、再對每一筆訂單各查一次客戶，100 筆訂單就是 101 次 query；JOIN 一次取回，`IN` 兩次取回：

```sql
-- N+1：先取訂單（1 次）
SELECT id, customer_id FROM orders ORDER BY id LIMIT 100;
-- 再對每一筆訂單各查一次客戶（100 次），? 換成那筆訂單的 customer_id
SELECT id, name FROM customers WHERE id = ?;

-- JOIN：1 次取回訂單與客戶名稱
SELECT orders.id, orders.status, customers.name
FROM orders JOIN customers ON customers.id = orders.customer_id
ORDER BY orders.id LIMIT 100;

-- IN：取完訂單之後，把這一頁出現過的 customer_id 收成一次查詢（共 2 次）
SELECT id, name FROM customers WHERE id IN (?, ?, ?);
```

N+1 在 ORM 環境特別隱性，因為它常被框架的 lazy loading 機制隱藏。Django ORM 的 `order.customer` 看起來像存取 attribute，背後對應一次 query。寫程式時看不到 SQL，發布後才從 slow log 發現問題。

判讀方式：開啟 ORM 的 query log（debug mode）、看一個 API request 跑出幾個 query。預期是個位數；若 query 數隨著資料集大小線性成長（例如 list 100 筆觸發 100 query、list 1000 筆觸發 1000 query），這條 scaling 訊號就是 N+1 — 比固定閾值更可靠的判讀。

修正方向：

- ORM 端用 eager loading（Django `select_related` / `prefetch_related`、Rails `includes`、SQLAlchemy `joinedload`）
- 自己寫 SQL 用 JOIN 或 IN 條件批次取
- 確認 ORM 預設不是 lazy（有些 ORM 的設計鼓勵 lazy，需要明確標示 eager）

## Select * 與超量讀取

`SELECT *` 把表的所有欄位都拉出來，包含可能很大的欄位（content、blob、JSON）跟根本用不到的欄位。代價有三：

1. **網路傳輸成本**：query 結果在 DB 跟應用之間傳輸，欄位越多越大。
2. **記憶體成本**：應用程式要 deserialize 整個 row，物件越大記憶體佔越多。
3. **隱性耦合**：欄位有變動（新增、刪除、改型別）時，所有 `SELECT *` 的 query 都會被影響。

修正方向是明確列出需要的欄位：`SELECT id, name, status FROM orders`。如果擔心欄位列表太長，問自己是不是 query 試圖一次處理太多責任。

例外是 ad-hoc query 跟 DB tool 環境，可以接受 `SELECT *`。production code 不應該有。

## 缺索引：查詢計畫沒走索引

> 計畫沒走索引有兩種成因，本節處理的是「索引根本沒建」。另一種是索引建了而條件的形狀讓它用不上（欄位被包進函式或運算裡），兩者在 `EXPLAIN` 上都顯示沒走索引，修法卻完全不同——判斷標準與改寫方法（拆成範圍條件、把運算搬到比較的另一邊、建運算式索引）在 [Sargable（可走索引的條件形狀）](/backend/01-database/sql/knowledge-cards/sargable/)。

缺索引的徵兆是 query 在小資料量時很快、資料一多就突然慢。原因是 query 走了 full table scan，資料量小時 scan 還快、資料量上百萬筆就慢。

判讀方式是用 `EXPLAIN` 看查詢計畫。下面是 MySQL 8.4 對一張一萬列、`customer_id` 沒有索引的 `orders` 表的輸出：

```sql
EXPLAIN SELECT id, status FROM orders WHERE customer_id = 42 ORDER BY created_at DESC;
-- type: ALL      整張表逐列掃描，沒走索引
-- rows: 10266    預計要讀的列數，接近整張表的大小（這是估計值，實際是 10000 列）
-- Extra: Using where; Using filesort
--                Using filesort 表示結果要另外排序；Using temporary 表示要另建暫存表

CREATE INDEX orders_customer_created ON orders (customer_id, created_at);
EXPLAIN SELECT id, status FROM orders WHERE customer_id = 42 ORDER BY created_at DESC;
-- type: ref   key: orders_customer_created   rows: 20   Extra: Backward index scan
```

PostgreSQL 的 `EXPLAIN` 用 `Seq Scan on orders` 表示整張表掃描。它每個節點上的 `rows` 是預計**輸出**的列數（同一個查詢在 PostgreSQL 16 顯示 `Seq Scan on orders ... rows=20`），不是要讀的列數，所以「`rows` 接近表大小」這個讀法只適用於 MySQL。

修正方向不是「對每個 WHERE 條件都建索引」，這會讓寫入變慢、索引變大。要建索引的判讀條件：

- 該 query 是熱路徑（頻率高、影響 user）
- 該欄位有足夠選擇性（distinct 值多）
- 該欄位沒有跟其他索引重複覆蓋
- 寫入路徑能承受多一個索引的維護成本

複合索引的欄位順序要對齊 query 的條件，而兩個欄位都是等值條件時順序沒有差別：`WHERE a = ? AND b = ?` 用 `(a, b)` 或 `(b, a)` 都能把兩個條件放進索引查找。順序的差別出在只有一個欄位有條件、或其中一個是範圍條件的時候：

```sql
-- MySQL 8.4，表 t 有 5000 列
-- 只有 (b, a) 索引時
EXPLAIN SELECT * FROM t WHERE a = 1 AND b = 2;  -- type: ref, key: t_ba, ref: const,const
EXPLAIN SELECT * FROM t WHERE a = 1;            -- type: ALL，a 不是索引的第一欄，索引用不上
EXPLAIN SELECT * FROM t WHERE a = 1 AND b > 2;  -- type: ALL，優化器沒有選 t_ba

-- 只有 (a, b) 索引時
EXPLAIN SELECT * FROM t WHERE a = 1 AND b = 2;  -- type: ref, key: t_ab, ref: const,const
EXPLAIN SELECT * FROM t WHERE a = 1;            -- type: ref, key: t_ab（最左前綴）
EXPLAIN SELECT * FROM t WHERE a = 1 AND b > 2;  -- type: range, key: t_ab，等值欄在前、範圍欄在後
```

複合索引欄位順序的設計屬於 [1.2 schema design 與資料建模](/backend/01-database/schema-design/) 的範圍、本章只標出徵兆跟診斷起點。

## ORM Lazy Load 陷阱

ORM 的 lazy load 預設行為是「存取 attribute 時才發 query」，這在開發時讓 code 很乾淨，但隱藏了 query 的數量。

常見陷阱：

- **跨 transaction 邊界存取 lazy attribute**：query 在原 transaction 已關閉後才發，連線狀態錯誤。
- **在 template / serializer 裡存取 lazy attribute**：一個 page render 觸發數十個額外 query。
- **lazy load 跨服務邊界**：DTO 傳遞時不知道哪些 attribute 是 lazy、哪些是 eager，前端拿到 DTO 後 trigger 額外 query。

修正方向：

- 明確標示 eager loading 邊界，serializer 之前完成所有需要的資料載入
- ORM 配置改成 default eager 或 strict mode（query 太多會 warning）
- DTO 出 service 邊界前做 fully materialized

## Long-Running Transaction

長時間佔住的 transaction 會擋住其他 query、產生 lock 等待、消耗連線池資源。

常見成因：

- 在 transaction 內做 HTTP call 或外部 API 呼叫
- 在 transaction 內做檔案 I/O 或長計算
- 用 transaction 包住整個 request handler（從 request 開始到 response 結束都在 transaction）
- ORM 設定 default transaction-per-request 但業務只需要短交易

修正方向是把 transaction 範圍縮到最小：只包住「需要原子性」的那幾個 SQL 操作。外部呼叫、計算、檔案 I/O 都要在 transaction 之外。詳見 [1.3 transaction 與一致性邊界](/backend/01-database/transaction-boundary/)。

## 其他常見反模式

N+1、`SELECT *`、缺索引、ORM lazy load 與長 transaction 之外，還有幾類反模式在 slow log 出現頻率不低、要一併列入發布前檢查：

- **[Cardinality explosion](/backend/knowledge-cards/cardinality-explosion/) / cross join 誤用**：兩個多對多關聯 join 沒加 filter、結果集從 N 行炸成 N×M 行。判讀訊號：query 結果行數遠超業務直覺、`EXPLAIN` 估計 rows 異常大。修正方向：補 filter、改 EXISTS / IN 半連接、或拆兩段 query。
- **OFFSET-based pagination on large tables**：`OFFSET` 要先讀過被跳過的每一列，才輪到要回傳的那幾列。修正方向是 [keyset / cursor pagination](/backend/knowledge-cards/keyset-pagination/)：用上一頁最後一筆的 id 當起點，讀的列數只跟這一頁的筆數有關。下面是 PostgreSQL 16 對 20 萬列的表依主鍵分頁的實測，`actual rows` 是索引實際讀出的列數：

  ```sql
  SELECT id, status FROM big_orders ORDER BY id LIMIT 20 OFFSET 100000;
  -- Index Scan using big_orders_pkey (actual rows=100020)：讀出 100020 列、丟掉前 100000 列

  SELECT id, status FROM big_orders WHERE id > 100000 ORDER BY id LIMIT 20;
  -- Index Scan using big_orders_pkey (actual rows=20)，Index Cond: (id > 100000)
  -- 100000 是上一頁最後一筆的 id；ORDER BY id 決定「下一頁」是哪 20 列，省掉它 LIMIT 取到的是任意 20 列
  ```

  keyset 與 cursor 回答的是兩個不同層次的問題（定位機制 vs 對外表示），對外介面要不要一起換、以及 offset 在哪些條件下該留著，見 [分頁之爭](/backend/11-api-design/pagination-debate/)。
- **隱式型別轉換讓 index 失效**：MySQL 拿字串欄位與數字常數比較時，把欄位值逐列轉成數字再比，欄位上的索引因此用不上。判讀訊號：EXPLAIN 顯示 index 沒命中但 schema 上有 index。修正方向：常數的型別對齊欄位。

  ```sql
  -- MySQL 8.4，accounts.code 是 VARCHAR(20)、有索引 accounts_code，表有 5000 列
  EXPLAIN SELECT * FROM accounts WHERE code = 123;    -- type: ALL, key: NULL, rows: 5000
  EXPLAIN SELECT * FROM accounts WHERE code = '123';  -- type: ref, key: accounts_code, rows: 1
  ```

  PostgreSQL 不做這個轉換，`code = 123` 直接報錯 `operator does not exist: character varying = integer`，所以這一條是 MySQL 的反模式。
- **應用層做大結果集排序 / 聚合**：把 100 萬行拉回應用、在記憶體 sort 或 group。應該 push 給 DB 做 `ORDER BY` / `GROUP BY` + `LIMIT`。判讀訊號：應用程式記憶體用量隨 endpoint 流量線性升高。
- **N+1 write**：在 loop 內單筆 insert / update 而非 bulk insert。每筆觸發一次 round trip + 可能的 fsync。修正方向：用 `INSERT ... VALUES (), (), ()` 或 `executemany` / `bulk_create`。

NoSQL / KV DB 也有 sibling 反模式（hot partition、read amplification、scan-and-filter），不在本章 SQL 範疇但邏輯類似 — 詳見 [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)。

## 每請求的 Query 預算

把上面這些反模式收斂成一個發布前可檢查的判斷標準：每個 API request 允許發多少個 query。

| API 類型              | 建議 query 預算 | 判讀說明                                             |
| --------------------- | --------------- | ---------------------------------------------------- |
| 簡單 read（取單筆）   | 1–3 個          | 主資源 1 個 + 相關資源 join 或 1–2 個額外            |
| List read（取列表）   | 1–5 個          | 主列表 1 個 + filter / pagination / 關聯 batch query |
| Write（單筆操作）     | 2–5 個          | check 1 個 + write 1 個 + 觸發後續 query             |
| Complex（多步驟業務） | 5–15 個         | 視業務複雜度，但每多 1 個都要能講出為什麼            |

超過預算不一定錯，但需要解釋。CI / staging 可以加 middleware 統計每個 endpoint 的 query 數，超過閾值在 PR review 時觸發討論。這比事後從 slow log 找問題更有效。

這張表以 OLTP API 為主。Dashboard / report / search endpoint 常需要 10-30 query 解 join / aggregation、用「Complex」涵蓋不夠精確；batch / bulk write（一次寫入 1000 筆訂單）不該用 query count 評估、應該看 batch size 跟 transaction 範圍。預算是判讀工具、不是硬閾值。

## `SELECT *`、N+1 與缺索引的成因常在 schema

本章的修法都改在查詢與 ORM 的寫法上，而其中幾條的成因在更上游：`SELECT *` 的代價由那張表裝了多寬決定（長文字欄位與短欄位同表時，不碰它的查詢也要掃過它的頁面）、N+1 的可修性由常一起取的資料切在幾張表決定、缺索引那一條裡有一種是索引建了而條件的形狀讓它用不上，而條件寫成那個形狀往往是因為比較規則沒有寫在欄位上。

這幾個上游決定各自替查詢定了什麼價，逐條實測在 [1.16 設計時下的每一個決定，替往後每一次查詢定價](/backend/01-database/design-decisions-price-every-query/)。

## 判讀訊號

| 訊號                              | 判讀重點                                 | 對應動作                                                                                    |
| --------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------- |
| API 在資料量增加後突然變慢        | 缺索引或查詢計畫退化                     | 跑 EXPLAIN、檢查 query plan                                                                 |
| 同一個 API 跑出 dozens 個 query   | N+1 反模式                               | 加 eager loading 或改寫成 JOIN                                                              |
| 應用程式記憶體用量隨流量線性升高  | `SELECT *` 載入過多資料                  | 改成明確欄位、加 pagination                                                                 |
| DB connection 等待時間升高        | long transaction 或 connection pool 不足 | 縮 transaction 範圍、評估 [connection pool](/backend/knowledge-cards/connection-pool/) 上限 |
| Lock wait timeout 變多            | long transaction 或 hot row 競爭         | 拆 transaction、檢查 hot row 設計                                                           |
| Slow query log 集中在某類 SQL     | 該 query 走了 full scan 或 join 順序錯誤 | EXPLAIN + 加索引或改寫 query                                                                |
| ORM debug log 顯示 hundreds query | lazy load 失控                           | 換 eager loading 策略、檢視 serializer 邊界                                                 |

## 常見誤區

把「資料庫變慢」直接解讀成「該升級資料庫」。先看應用層 query。多數效能問題是反模式造成的、而不是 DB 規格不夠。

把索引當「想加就加」。每個索引都有寫入成本跟空間成本。索引太多會讓 INSERT/UPDATE 變慢、backup 變大。要建索引前先驗證該 query 是熱路徑。

把 N+1 當「在 ORM 環境無解」。多數 ORM 都有 eager loading 選項，只是預設 lazy。問題是團隊沒把這當作預設策略。設定 ORM 為 default eager 或在 CI 加 query 數量檢查就能避免。

把 transaction 範圍當「越大越安全」。長 transaction 是 lock 風險來源，不是一致性保證。一致性靠正確的 isolation level 跟業務邏輯，不是靠長 transaction 鎖住整個流程。

## 定位邊界

本章專注「應用層發給資料庫的 query 反模式」。當問題進入 schema 設計（要不要拆表？要不要 partition？）交給 [1.2 schema design](/backend/01-database/schema-design/)；進入 transaction 語意（什麼時候用 SERIALIZABLE？怎麼 retry？）交給 [1.3 transaction boundary](/backend/01-database/transaction-boundary/)；進入跨服務的查詢責任拆分（哪些查詢屬於該服務？）交給 [1.8 state ownership 與 query boundary](/backend/01-database/state-ownership-query-boundary/)；進入瓶頸定位的工程流程交給 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)。

## 案例回寫

09 案例庫的主軸是規模、vendor 與容量壓力，直接以「query 反模式」為主題的案例較少。下列案例可以反向讀：每一個都展示了「在沒有先用 query 反模式優化收回壓力的前提下、團隊直接走 vendor 遷移或 scale-out 路徑」的決策。讀者讀完應追問：這些 case 啟動遷移前、是否有可能用本章的反模式清單先收回一部分容量？

- [9.C39 DoorDash：Aurora Postgres 寫入瓶頸 → CockroachDB](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/) — DoorDash 撞到 Aurora single-primary write 天花板（瓶頸在 primary CPU + WAL flush rate）、用 PostgreSQL wire protocol 相容的 CockroachDB 換成多主寫入、ORM 不必重寫。對照本章可問：寫入熱點是否伴隨長 transaction 或熱 row 競爭？這些是 vendor 遷移前可以先用本章「Long-Running Transaction」清單檢查的點。
- [9.C20 Zomato：TiDB 遷到 DynamoDB](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — Zomato 判斷 billing 事件本身可接受 eventually consistent、用一致性語意換取 4 倍吞吐 + 50% 成本。對照本章可問：遷移前每筆業務動作平均發了多少 query、是否有 N+1 或 select \* 在放大壓力？把這條問題擺進「每請求 Query 預算」段一起讀。
- [9.C14 Standard Chartered：Aurora 4000 TPS 合規容量](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — Standard Chartered 在 7 個受監管市場各跑獨立 Aurora cluster（資料不能跨境）、容量規劃單位是「per 市場」、合規邊界決定了 cluster 拓樸。對照本章可問：query 預算假設是否進入容量模型？預算寫鬆、規劃出的 per-cluster TPS 上限會偏低。

DoorDash 案例是這條反向追問最直接的應用 — 寫入瓶頸的判讀不該停在 vendor 規格、而是先檢查 transaction 範圍跟熱 row 競爭。Zomato 跟 Standard Chartered 的反向追問則退一步問「query 預算假設是否進入容量模型」。三條追問共享同一條診斷邏輯：應用層 query 不是事後解釋的細節、是事前可以收回的容量。這個讀法承認案例本身不直接示範 query 反模式、是用反向追問把案例當成 query 反模式重要性的反證。

## 跨模組路由

1. 與 [1.1 高併發下的 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/) 的交接：連線池與 read replica 機制在那一篇，query 寫法本身在本章。高併發場景下兩者要同步檢查。
2. 與 [1.2 schema design](/backend/01-database/schema-design/) 的交接：索引設計是 schema 層的事、本章只指出徵兆。
3. 與 [04 observability](/backend/04-observability/) 的交接：slow query log、APM、query trace 是判讀反模式的主要訊號來源。
4. 與 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 的交接：先在應用層查反模式，再考慮 DB 配置升級。
5. 與 [9.13 擴展軸](/backend/09-performance-capacity/scaling-axes/) 的交接：[規模成長路線](/backend/scale-growth-walls/)上、擴展軸選定之後、本章是緊接著的下一站 — 在加機器或加 replica 前、先用本章反模式清單收回單機能撐住的容量。
6. 與 [10.1 服務拆分](/backend/10-system-evolution/service-decomposition-boundaries/) 的交接：拆服務常被用來「解決 DB 慢」，但本章的反模式優化通常比拆服務 ROI 更高、應該優先嘗試。

## 下一步路由

**規模成長路線下一站 → [1.1 高併發下的 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/)**：query 反模式收完後、處理連線池與 read replica 的擴展。

其他延伸方向：

- Schema 與索引設計 → [1.2 schema design 與資料建模](/backend/01-database/schema-design/)
- Transaction 範圍收斂 → [1.3 transaction 與一致性邊界](/backend/01-database/transaction-boundary/)
- 瓶頸定位完整流程 → [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
