---
title: "1.13 應用層查詢反模式與 Query 預算"
date: 2026-05-27
description: "整理 N+1、select *、缺索引、ORM lazy load、long transaction 等查詢反模式與每請求的 query 預算判讀"
weight: 13
tags: ["backend", "database", "query", "anti-patterns"]
---

應用程式變慢、第一個直覺常常是「資料庫不夠力」。多數團隊的真實瓶頸卻不在資料庫本身、而在應用程式發給資料庫的查詢方式：N+1、select \*、缺索引、ORM lazy load、長 transaction。本章把這些反模式列成可診斷、可修正的清單、並提出「每請求的 query 預算」作為發布前的判讀基準 — 讓讀者在資料層撞牆之前、先在應用層發現問題。

## 為什麼查詢反模式比 vendor 細節更重要

多數團隊面對「資料庫變慢」時，會先去看 vendor 的調校（buffer pool、配置升級、replica 加開）。這些調校通常把基礎效能拉高 1-2 倍；一個 N+1 query 反模式可以讓回應時間慢 10-1000 倍（具體倍數取決於 N 跟 RTT — N=100 + RTT=1ms 約慢 100 倍）。先解掉應用層的反模式、再去調 vendor 配置，整體效益遠高於反過來。

這條優先序也對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 的精神：先定位真正的瓶頸再決定是否加資源。應用層 query 是最常被忽略的瓶頸來源。

## N+1 Query：最常見也最隱性的反模式

N+1 query 指「先發一個 query 取回 N 筆資料、再對每一筆各發一個 query 取相關資料」，總共 1 + N 次 round trip。N 越大、整體越慢。

典型範例：列出 100 個訂單跟每筆訂單的客戶資料。錯誤寫法是先 `SELECT * FROM orders LIMIT 100` 拿到 100 筆訂單、再對每一筆訂單做 `SELECT * FROM customers WHERE id = ?`，總共 101 次 query。正確寫法是 JOIN 或 IN 一次取回：`SELECT o.*, c.* FROM orders o JOIN customers c ON o.customer_id = c.id LIMIT 100`，1 次 query 完成。

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

缺索引的徵兆是 query 在小資料量時很快、資料一多就突然慢。原因是 query 走了 full table scan，資料量小時 scan 還快、資料量上百萬筆就慢。

判讀方式是用 `EXPLAIN` 看查詢計畫：

- `type=ALL` 或 `Seq Scan` 代表沒走索引
- `rows` 估計值跟實際表大小接近，代表掃描範圍過大
- `Using filesort` / `Using temporary` 代表排序或暫存資料的成本

修正方向不是「對每個 WHERE 條件都建索引」，這會讓寫入變慢、索引變大。要建索引的判讀條件：

- 該 query 是熱路徑（頻率高、影響 user）
- 該欄位有足夠選擇性（distinct 值多）
- 該欄位沒有跟其他索引重複覆蓋
- 寫入路徑能承受多一個索引的維護成本

複合索引的欄位順序也要對齊 query 的 WHERE 條件。`WHERE a = ? AND b = ?` 適合 `(a, b)` 複合索引，不適合 `(b, a)`。這部分屬於 [1.2 schema design 與資料建模](/backend/01-database/schema-design/) 的範圍、本章只標出徵兆跟診斷起點。

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

上面五個是讀路徑高頻反模式。實務上其他幾類在 slow log 出現頻率不低、要一併列入發布前檢查：

- **Cardinality explosion / cross join 誤用**：兩個多對多關聯 join 沒加 filter、結果集從 N 行炸成 N×M 行。判讀訊號：query 結果行數遠超業務直覺、`EXPLAIN` 估計 rows 異常大。修正方向：補 filter、改 EXISTS / IN 半連接、或拆兩段 query。
- **OFFSET-based pagination on large tables**：`LIMIT 20 OFFSET 100000` 在大表退化成「掃描 100020 行 + skip 100000 行」。修正方向：用 keyset / cursor pagination（`WHERE id > last_seen_id LIMIT 20`）— 一致 O(LIMIT) 而非 O(OFFSET + LIMIT)。
- **隱式型別轉換讓 index 失效**：`WHERE varchar_col = 123` 把 column 轉成 int 比較、index 失效退到 full scan。判讀訊號：EXPLAIN 顯示 index 沒命中但 schema 上有 index。修正方向：明示型別（`WHERE varchar_col = '123'`）。
- **應用層做大結果集排序 / 聚合**：把 100 萬行拉回應用、在記憶體 sort 或 group。應該 push 給 DB 做 `ORDER BY` / `GROUP BY` + `LIMIT`。判讀訊號：應用程式記憶體用量隨 endpoint 流量線性升高。
- **N+1 write**：在 loop 內單筆 insert / update 而非 bulk insert。每筆觸發一次 round trip + 可能的 fsync。修正方向：用 `INSERT ... VALUES (), (), ()` 或 `executemany` / `bulk_create`。

NoSQL / KV DB 也有 sibling 反模式（hot partition、read amplification、scan-and-filter），不在本章 SQL 範疇但邏輯類似 — 詳見 [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)。

## 每請求的 Query 預算

把上面這些反模式收斂成一個發布前可檢查的判準：每個 API request 允許發多少個 query。

| API 類型              | 建議 query 預算 | 判讀說明                                             |
| --------------------- | --------------- | ---------------------------------------------------- |
| 簡單 read（取單筆）   | 1–3 個          | 主資源 1 個 + 相關資源 join 或 1–2 個額外            |
| List read（取列表）   | 1–5 個          | 主列表 1 個 + filter / pagination / 關聯 batch query |
| Write（單筆操作）     | 2–5 個          | check 1 個 + write 1 個 + 觸發後續 query             |
| Complex（多步驟業務） | 5–15 個         | 視業務複雜度，但每多 1 個都要能講出為什麼            |

超過預算不一定錯，但需要解釋。CI / staging 可以加 middleware 統計每個 endpoint 的 query 數，超過閾值在 PR review 時觸發討論。這比事後從 slow log 找問題更有效。

這張表以 OLTP API 為主。Dashboard / report / search endpoint 常需要 10-30 query 解 join / aggregation、用「Complex」涵蓋不夠精確；batch / bulk write（一次寫入 1000 筆訂單）不該用 query count 評估、應該看 batch size 跟 transaction 範圍。預算是判讀工具、不是硬閾值。

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

1. 與 [1.1 高併發下的 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/) 的交接：1.1 處理連線池與 read replica 機制、1.13 處理 query 寫法本身。高併發場景下兩者要同步檢查。
2. 與 [1.2 schema design](/backend/01-database/schema-design/) 的交接：索引設計是 schema 層的事、本章只指出徵兆。
3. 與 [04 observability](/backend/04-observability/) 的交接：slow query log、APM、query trace 是判讀反模式的主要訊號來源。
4. 與 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 的交接：先在應用層查反模式，再考慮 DB 配置升級。
5. 與 [9.13 擴展軸](/backend/09-performance-capacity/scaling-axes/) 的交接：規模成長路線上、9.13 解擴展軸選擇後、1.13 是緊接著的下一站 — 在加機器或加 replica 前、先用本章反模式清單收回單機能撐住的容量。
6. 與 [0.18 服務拆分](/backend/00-service-selection/service-decomposition-boundaries/) 的交接：拆服務常被用來「解決 DB 慢」，但本章的反模式優化通常比拆服務 ROI 更高、應該優先嘗試。

## 下一步路由

**規模成長路線下一站 → [1.1 高併發下的 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/)**：query 反模式收完後、處理連線池與 read replica 的擴展。

其他延伸方向：

- Schema 與索引設計 → [1.2 schema design 與資料建模](/backend/01-database/schema-design/)
- Transaction 範圍收斂 → [1.3 transaction 與一致性邊界](/backend/01-database/transaction-boundary/)
- 瓶頸定位完整流程 → [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
