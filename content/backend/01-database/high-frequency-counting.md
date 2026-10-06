---
title: "1.18 高頻計數的寫入與彙總：熱點列的鎖、只新增的事件、可以重跑的彙總與重送的事件"
date: 2026-10-06
description: "熱點列更新的吞吐量上限與它的成因、拆成多列／只新增事件／先在記憶體裡合併的差別、只新增事件搬去哪裡的成本、累加與重算在什麼條件下漏算或重複計算、讓彙總排程互斥的建議鎖與連線池的交互，以及重送事件的冪等寫入、推導事實的存放位置，以及 Redis 承擔即時計數、跨小時不重複數、去重與互斥時各自的邊界"
weight: 18
tags: ["backend", "database", "postgresql", "lock", "aggregation", "idempotency"]
---

這篇整理「每一次發生都要記下來、事後要統計」這類資料的寫法：連結的點擊、文章的瀏覽、商品頁的曝光、API 的呼叫次數。它們的共同形狀是寫入很頻繁、單筆不重要、讀的人要的是彙總後的數字。寫入當下要檢查上限的數字（庫存、配額、帳戶餘額）不在這篇的範圍：它們每一次扣減都要在交易裡確認結果不小於 0，不能延後彙總，也不能接受遺失，做法見 [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/) 與 [1.3 Transaction 與一致性邊界](/backend/01-database/transaction-boundary/)。範例用 PostgreSQL 17，MySQL（InnoDB）的對應行為在各節註明；程式片段對照 Go、PHP（Laravel）與 Python。

文中的吞吐量與耗時是在一台筆電的 Docker 裡量的，每種設定交錯跑三輪、列出範圍。絕對值與倍數都隨磁碟寫入的延遲而變，能帶走的是哪一種寫法快、瓶頸落在哪裡；要知道自己的環境，用文末〈量測用的建表語句與 pgbench 腳本〉在那台機器上跑一次吞吐量的比較。

## 熱點列：同一列更新的排隊機制

最直接的寫法是每發生一次就把計數加一：

```sql
UPDATE link_counters SET clicks = clicks + 1 WHERE link_id = 1;
```

`UPDATE` 要先取得那一列的列鎖，**列鎖一直持有到交易提交為止**；另一個要更新同一列的交易只能等前一個提交完。所以同一列上的更新是一個接一個進行的，而每一次提交要等交易紀錄（WAL）寫進磁碟才算完成。這一列每秒能承受的更新次數，上限大約是「一秒除以一次提交寫盤的時間」，加開連線也提高不了。這種所有寫入都集中在同一列上的情形叫熱點列（hot row），找出它的查詢與其他分散它的做法見 [1.1 高併發下的 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/)。

用 PostgreSQL 附的壓測工具 pgbench 比較同一列更新、拆成多列、新增事件三種寫法；同一列更新另外量了單一連線與關掉同步提交的版本。量測環境是筆電上的 Docker、沒有寫入快取的磁碟，絕對值隨寫盤延遲變動；表中每一行是三輪、每輪 15 秒的範圍：

| 寫法與連線數                                                      | 每秒完成的交易數 | 平均延遲      |
| ----------------------------------------------------------------- | ---------------- | ------------- |
| 同一列更新，1 條連線                                              | 769 到 1,180     | 0.8 到 1.3 ms |
| 同一列更新，32 條連線                                             | 653 到 908       | 35 到 49 ms   |
| 計數拆成 10 列、每次隨機挑一列加一，32 條連線                     | 2,488 到 2,655   | 12 到 13 ms   |
| 每次新增一列事件（`INSERT`），32 條連線                           | 11,473 到 14,793 | 2.2 到 2.8 ms |
| 同一列更新，32 條連線，關掉同步提交（`synchronous_commit = off`） | 28,926 到 49,480 | 0.6 到 1.1 ms |

表中有兩個結果要另外解釋：

- **連線從 1 條加到 32 條，吞吐量沒有增加，延遲放大約四十倍**。多出來的 31 條連線都在排隊：PostgreSQL 讓等同一列的交易依序取得列鎖，第一個等待者等的是持有者的交易結束（`pg_stat_activity` 顯示 `wait_event_type = Lock`、`wait_event = transactionid`），排在它後面的等待者先在一個專門用來排隊的 tuple 鎖上等（`wait_event = tuple`）。壓測中途查一次，32 條連線裡有 30 條在等 tuple 鎖。每一筆更新的延遲因此是「前面每一筆的提交時間相加」。
- **關掉同步提交之後快了數十倍**。這證明瓶頸是「持有列鎖的期間包含了寫盤」，不是更新本身：熱點列上每一筆交易各寫一次盤，而新增事件的 32 條連線平均約十幾筆交易共用一次寫盤。倍數由寫盤的延遲決定，在有寫入快取的伺服器磁碟上會小很多。同步提交關掉的代價是資料庫當機時，最後一小段已經回報成功的交易會遺失（預設最多約是 `wal_writer_delay` 的三倍，也就是幾百毫秒），只有能接受遺失少量計數的資料才值得考慮，而這個設定改變的是整個連線或交易的持久性，不只這一個計數。

熱點列不斷被更新，也會快速累積死元組（dead tuple，被新版本取代、還沒被清理的舊列）；HOT 更新與調低 fillfactor 能減少索引的寫入與表的膨脹（見 [PostgreSQL autovacuum tuning：預設 cost-based throttle 在 write-heavy 表上追不上 bloat](/backend/01-database/vendors/postgresql/autovacuum-tuning/)），但改變不了列鎖的排隊。

MySQL（InnoDB）的列鎖同樣持有到提交，`innodb_flush_log_at_trx_commit = 1`（預設）時提交同樣要等 redo log 寫盤，所以熱點列的吞吐量同樣受提交寫盤的時間限制。

## 把寫入分開的三種做法：拆成多列、只新增事件、先在記憶體裡合併

熱點列的根源是所有寫入搶同一列。三種常見做法都是讓寫入落在不同的地方，差別在於數字在什麼時候、在哪裡加總：

- **拆成多列（counter shard）**：一個計數拆成 N 列，每次隨機挑一列加一，讀取時加總。pgbench 那一組壓測裡，拆成 10 列的吞吐量約是同一列的 3 倍，到不了 10 倍，差距的成因這次實驗沒有拆開。它保留了「一個數字」的形狀，查詢最簡單；代價是只能回答事先設計好的那一個數字，要依國家、裝置、客群拆分時就要更多計數器。Firestore 這類對單一文件有寫入上限的資料庫用同一個做法，見 [Firestore 高頻寫入與 distributed counter：單 document contention 邊界與分片計數](/backend/01-database/vendors/firestore/distributed-counter-high-frequency-write/)。
- **只新增（append-only）事件，事後彙總**：每發生一次就 `INSERT` 一列事件（下文的事件表是 `click_events (id, link_id, clicked_at)`，`clicked_at` 由程式在事件發生時給值），事件之間沒有共用的列，彼此不必等鎖，多個交易的提交也能合併成一次寫盤（group commit）。原始事件留著，彙總的維度可以事後再決定、規則改了可以重算；代價是要另外寫彙總，而且事件表會一直長大。
- **先在記憶體裡合併，定期寫回**：在 Redis 用 `INCR` 計數，或在每個應用程式實例的記憶體裡累加，每分鐘（或每秒）把數字寫回資料庫，熱點列的更新因此降到每個實例每個週期一次。寫入最快；代價是寫回之前那段時間的計數可能遺失，而且和拆成多列一樣只能回答事先設計好的數字。寫回的語意要先決定：寫回「這段時間的增量」（例如 Redis 的 `GETDEL` 取出再歸零）時，資料庫寫入失敗就遺失那一段；寫回「目前的總數」時，Redis 的鍵被淘汰或過期之後，會用一個很小的數字覆蓋資料庫裡的總數。單一熱門計數在 Redis Cluster 上本身也會成為熱點鍵（[Hot Key](/backend/knowledge-cards/hot-key/)）。只需要一個顯示用的數字（例如文章頁上的瀏覽數），而且能接受少量遺失時，這是最簡單的選擇；要排除同一人重複瀏覽時，用 Redis 的 HyperLogLog 估計不重複數（見 [2.11 Redis data types 實作](/backend/02-cache-redis/redis-data-types/)）。

要回答的問題會隨時間增加（今天看總點擊，下個月要依客群拆、再下個月要排除機器人的點擊）時，三種做法裡只有「只新增事件」不必改寫入路徑。只需要一個數字時，拆成多列或先在記憶體裡合併比較省事。Redis 承擔熱點計數、跨小時的不重複數、去重與互斥時，各自的邊界見〈Redis 在計數、去重與互斥裡的位置〉。下面各節處理這個做法帶來的問題。

## 只新增事件的成本：索引、保存期限、清理與寫入路徑

只新增事件讓寫入變便宜，成本搬到了索引維護、舊事件的刪除、清理（VACUUM）與寫入路徑上：

- **每一列事件都要更新每一個索引**：事件表上每多一個索引，每次 `INSERT` 就多寫一次。給彙總用的時間欄索引、給查詢用的外鍵索引都有理由存在；其他索引服務的查詢，先確認能不能改查彙總表，能的話那個索引就不必建在事件表上。
- **表只會變大**：保存期限到了要刪除舊事件。逐筆 `DELETE` 會留下大量死元組；依時間分區（[Table Partitioning](/backend/knowledge-cards/table-partitioning/)）之後，整個分區直接刪除快得多（見 [PostgreSQL declarative partitioning：partition 不是切表、是讓 planner pruning](/backend/01-database/vendors/postgresql/declarative-partitioning/)）。事件表若存了 IP、User-Agent 這類個人資料（[PII](/backend/knowledge-cards/pii/)），保存期限要依個資的規定訂（見 [Retention](/backend/knowledge-cards/retention/)），而「刪除某一個人的資料」的請求在只新增的表上要跨分區逐筆刪除。以連結或日期為單位的彙總表不帶個資；以人為單位的推導事實（例如每位收件人每天一列，見〈由事件推導出的事實與事件的保存期限〉）本身就是個資，刪除請求也要涵蓋它。
- **只新增的表也要清理**：PostgreSQL 的清理除了回收死元組，還要更新可見性資訊並凍結夠舊的交易編號。PostgreSQL 13 以前，只新增的表沒有死元組可回收，要等到防止交易編號回繞的那次強制清理，才一次凍結累積下來的全部資料；PostgreSQL 13 起，自動清理也依「新增了多少列」觸發（`autovacuum_vacuum_insert_threshold`、`autovacuum_vacuum_insert_scale_factor`），凍結分散在多次清理裡進行。清理的節流參數與 write-heavy 表的調法見 [PostgreSQL autovacuum tuning：預設 cost-based throttle 在 write-heavy 表上追不上 bloat](/backend/01-database/vendors/postgresql/autovacuum-tuning/)。
- **寫入路徑**：處理請求的程式每次同步 `INSERT` 一列，尖峰時會和其他查詢搶連線；常見的下一步是處理請求的程式只把事件推進佇列，由背景程序批次寫入。這一步帶來「同一筆事件可能被寫兩次」的問題，見〈重送的事件：識別碼的產生位置與 ON CONFLICT 的寫法〉。

## 彙總的兩種寫法：累加新的事件，或重算一段時間

彙總表（[Rollup](/backend/knowledge-cards/rollup/)，例如每條連結每天一列）有兩種維護方式。

**累加**：記住「上次處理到哪一筆事件」，這裡稱為已處理位置（high-water mark；訊息消費端記錄處理進度的 [Checkpoint](/backend/knowledge-cards/checkpoint/) 是同一個概念，和 PostgreSQL 把資料頁寫回磁碟的 checkpoint 無關），每一輪只讀之後的事件，把數量加到既有的數字上，成本最低。下面的 `progress` 表存已處理位置，`click_daily` 是每條連結每天一列的彙總表。累加在一個交易裡先固定這一輪的上界，計數與推進已處理位置都用同一個上界；推進時若重新取一次 `max(id)`，計數之後才提交的事件會被一起跳過：

```sql
CREATE TABLE click_daily (link_id bigint, day date, clicks bigint NOT NULL, PRIMARY KEY (link_id, day));
CREATE TABLE progress (name text PRIMARY KEY, last_id bigint NOT NULL);
INSERT INTO progress VALUES ('click_daily', 0);

BEGIN;
SELECT last_id FROM progress WHERE name = 'click_daily';   -- 上一輪處理到的位置，例如 100
SELECT max(id) FROM click_events;                          -- 這一輪的上界，例如 250
INSERT INTO click_daily (link_id, day, clicks)
SELECT link_id, (clicked_at AT TIME ZONE 'UTC')::date, count(*) FROM click_events
WHERE id > 100 AND id <= 250                               -- 程式把上面兩個值帶進來
GROUP BY 1, 2
ON CONFLICT (link_id, day) DO UPDATE SET clicks = click_daily.clicks + EXCLUDED.clicks;
UPDATE progress SET last_id = 250 WHERE name = 'click_daily';
COMMIT;
```

**重算**：每一輪把一段時間（例如今天）的事件重新數一次，覆寫既有的數字。範圍的邊界寫明時區（`+00`），和分組用的 UTC 日期一致；只寫 `'2026-10-06'` 的話，PostgreSQL 依連線的時區設定解讀，連線的時區不是 UTC 時，一輪重算會算出兩個 UTC 日期各一部分的計數：

```sql
INSERT INTO click_daily (link_id, day, clicks)
SELECT link_id, DATE '2026-10-06', count(*) FROM click_events
WHERE clicked_at >= '2026-10-06 00:00+00' AND clicked_at < '2026-10-07 00:00+00'
GROUP BY link_id
ON CONFLICT (link_id, day) DO UPDATE SET clicks = EXCLUDED.clicks;
```

兩種寫法在「重跑」時的行為不同。下面的實驗準備了 3 筆事件（連結 1 兩筆、連結 2 一筆）。累加的那一輪執行了 `INSERT`、在 `UPDATE progress` 之前中斷（交易沒有包住這兩句的版本），下一輪從同一個已處理位置再跑一次；重算則直接跑兩次：

```text
累加，中斷後重跑：link 1 = 4、link 2 = 2
重算，跑兩次：    link 1 = 2、link 2 = 1
```

累加重複算了一次，重算的結果和跑幾次無關。累加的這個問題修得掉：把累加與推進已處理位置放在同一個交易裡（上面的寫法），中斷時兩者一起撤銷。但累加還有一個問題出在已處理位置本身，修正它的代價比改用重算高。

### 已處理位置與交易的提交順序

已處理位置通常是事件的遞增編號（identity）或寫入時間。編號在 `INSERT` 執行時配發，`DEFAULT now()` 的時間是交易開始的時刻，兩者都早於交易提交，而交易提交的順序不一定照它們的順序。用兩條連線實測：

| 時間    | 晚提交的連線                       | 立刻提交的連線                 | 彙總                                                                                  |
| ------- | ---------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------- |
| 第 0 秒 | 開始交易，新增一筆事件，拿到編號 1 |                                |                                                                                       |
| 第 1 秒 | （還沒提交）                       | 新增一筆事件，拿到編號 2，提交 |                                                                                       |
| 第 1 秒 | （還沒提交）                       |                                | 看不到未提交的編號 1，把編號 2 算進去，已處理位置推進到 2（累加與推進在同一個交易裡） |
| 第 4 秒 | 提交                               |                                |                                                                                       |
| 下一輪  |                                    |                                | 只讀編號大於 2 的事件                                                                 |

下面的 `counted` 是彙總表裡連結 1 的點擊數，`events` 是事件表的列數：

```text
counted | events
--------+--------
      1 |      2
```

表裡有 2 筆事件，彙總只算到 1 筆，編號 1 那一筆永遠不會被算到，資料庫與彙總程式都不會報錯。拿 `DEFAULT now()` 的時間當已處理位置有同樣的問題，而且交易從 `BEGIN` 到 `INSERT` 之間的時間也會算進去，因為 PostgreSQL 的 `now()` 是**交易開始**（`BEGIN` 執行）的時間；`clock_timestamp()` 才是呼叫那一刻的時間。下面另建一張用 `DEFAULT now()` 由資料庫填入時間的事件表示範：

```sql
CREATE TABLE click_log (
  id          bigint GENERATED ALWAYS AS IDENTITY,
  link_id     bigint NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now()
);

BEGIN;
SELECT pg_sleep(3);
INSERT INTO click_log (link_id) VALUES (1) RETURNING received_at, clock_timestamp() AS inserted_at;
COMMIT;
```

```text
          received_at          |          inserted_at
-------------------------------+-------------------------------
 2026-10-06 08:52:30.278114+00 | 2026-10-06 08:52:33.299518+00
```

寫入的那一刻是 33 秒，存下來的時間是 30 秒。一個執行較久的交易寫入的列，時間可能早於彙總已經推進過的已處理位置。MySQL 的 `NOW()` 取的是陳述句開始執行的時間，不是交易開始，但交易提交得晚的問題一樣存在；`AUTO_INCREMENT` 同樣在寫入時配號，和提交順序無關。

以時間記錄的已處理位置要修，就要留重疊區間：每一輪從「已處理位置減去一段時間」開始讀，這段時間要長過最長的寫入交易；重疊區間裡被讀到兩次的事件，要用事件產生時就帶著的識別碼排除（見〈重送的事件：識別碼的產生位置與 ON CONFLICT 的寫法〉），否則又會重複累加。以編號記錄的已處理位置沒有可靠的重疊寬度（編號的落差取決於同時有多少交易在寫），通常改用時間或改用重算。這些條件湊齊之後，由彙總程式另外維護已處理位置的累加，已經比重算複雜得多。事件由背景程序批次寫入時，還有一種不需要已處理位置的累加，見〈在批次寫入的交易裡累加〉。

### 重算的成本與以小時為單位的彙總

重算不需要已處理位置：同一段時間的事件不論何時提交，下一輪重算都會數到。它的代價是每一輪都要重讀整段時間。實測一天 300 萬筆事件、1 萬條連結，`clicked_at` 有索引：

| 每一輪重算的範圍               | 耗時（兩次）   |
| ------------------------------ | -------------- |
| 今天一整天（每天一列的彙總表） | 599 ms、637 ms |
| 一個小時（每小時一列的彙總表） | 56 ms、95 ms   |

每天一列的彙總表，重算今天就要讀今天到目前為止的全部事件，越接近午夜越慢，事件量成長時成本跟著成長；排程每分鐘跑一次的話，資料庫每分鐘都要掃一次當天的事件。改成每小時一列，每一輪只重算目前與前一個小時（上表一小時的兩倍左右），讀的量固定在兩小時的事件；每日的數字由 24 列加總，或由另一個較低頻的排程從小時表算出。每小時一列也讓不同時區的「今天」都組得出來（台北的一天是 UTC 前一天 16 時到當天 16 時）；時差不是整小時的時區（例如 +5:30）組不出來，需要更細的粒度。

重算的範圍要對齊整點、而且涵蓋「事件最晚會晚多久寫進來」。範圍取成「現在往前一小時」這種滑動的區間是錯的：它只涵蓋前一個小時的一部分，重算會用部分的計數覆寫完整的計數。事件經佇列由背景程序批次寫入、落後幾秒時，前一個完整的小時就足以涵蓋；可能落後到隔天（例如佇列積壓）時，範圍要跟著放寬，而程式要知道落後了多少才能放寬。兩種做法擇一：寫入端每一批記下它碰到哪些小時（例如寫進一張「待重算的小時」表），重算改成處理這些小時；或監控寫入延遲（寫入當下的時間減去事件的 `clicked_at`，或佇列未消費的數量），超過重算範圍就告警。兩者都沒有的話，積壓超過重算範圍的事件會被靜默漏算，和〈已處理位置與交易的提交順序〉的漏算是同一種形態。各實例由程式給 `clicked_at` 時，時鐘之間的差距（[Clock Skew](/backend/knowledge-cards/clock-skew/)）讓事件落進「已經不再重算的小時」，效果和晚到的事件相同，同樣由重算範圍的寬度吸收。

TimescaleDB 的 continuous aggregate 在它的更新策略涵蓋的時間範圍內，會追蹤晚到的事件並重算對應的時段；更早的資料晚到時，一樣要手動重算。事件量大到手寫重算難以維護時可以考慮（見 [TimescaleDB Deep Dive：Hypertable / Continuous Aggregate / Compression 把 PG 變 Time-Series DB](/backend/01-database/vendors/postgresql/timescaledb-deep-dive/)）。

重算的另一個成本：`ON CONFLICT DO UPDATE` 即使值沒有變，也會把每一列改寫一次，改寫幾列就留下幾個死元組。實測重算 1 萬列兩次，彙總表有 1 萬個死元組。加上「值有變才更新」的條件就能避開（下例以每天一列的表示範，日期是這一輪要重算的那一天，實際程式由參數帶入）：

```sql
INSERT INTO click_daily (link_id, day, clicks)
SELECT link_id, DATE '2026-10-06', count(*) FROM click_events
WHERE clicked_at >= '2026-10-06 00:00+00' AND clicked_at < '2026-10-07 00:00+00'
GROUP BY link_id
ON CONFLICT (link_id, day) DO UPDATE SET clicks = EXCLUDED.clicks
WHERE click_daily.clicks IS DISTINCT FROM EXCLUDED.clicks;
```

加上 `WHERE` 之後再重算一次，更新的列數是 0，沒有新的死元組。

## 同一時間只讓一個實例彙總：建議鎖與連線池

服務有多個實例、每個實例都有排程時，同一份彙總會被同時執行好幾份。重算本身可以重跑，但兩份同時跑時，較早讀取資料的那一份可能較晚提交，用舊的結果覆蓋新的結果。最直接的做法是只讓一個地方排程：在資料庫裡用 pg_cron 執行、Kubernetes CronJob 設 `concurrencyPolicy: Forbid`，或只在指定的一個實例上啟動排程。排程跟著每個實例一起部署時，常見的做法是用 PostgreSQL 的建議鎖（advisory lock，見 [Advisory Lock（建議鎖）](/backend/knowledge-cards/advisory-lock/)）：一個由應用程式自己決定意義的鎖，排程開始時先試著取得，取不到就表示別的實例正在跑，這一輪跳過。它保證的是「同一時間只有一份在跑」，不是「每一輪只跑一次」：一個實例跑完釋放之後，另一個實例的排程照樣會再跑一次，所以彙總本身仍要能重跑。框架也有自己的互斥機制，例如 Laravel 排程的 `onOneServer()` 與 `withoutOverlapping()` 用的是預設快取儲存（Redis、Memcached 或資料庫裡的快取表）上的鎖；同一份彙總由兩種語言的程式排程時（例如 Go 與 Laravel 兩個後端），兩邊要用同一種鎖，Laravel 的快取鎖和 Go 的建議鎖彼此看不見對方。兩邊改用 Redis 上的鎖時，Laravel 排程的鎖在收尾時不比對持有者就刪除，還要加上租約長度的選擇，見〈Redis 在計數、去重與互斥裡的位置〉。

建議鎖有兩種，持有的範圍不同。**session 層級**的 `pg_try_advisory_lock` 綁在取得它的那一條資料庫連線上，要同一條連線呼叫 `pg_advisory_unlock` 才會釋放；**交易層級**的 `pg_try_advisory_xact_lock` 在交易結束時自動釋放，沒有解鎖的函式。

應用程式透過 [Connection Pool](/backend/knowledge-cards/connection-pool/) 使用資料庫時，session 層級的鎖會出問題：取鎖與解鎖是兩次呼叫，連線池不保證兩次拿到同一條連線。下面的 Go 程式模擬這個情形（池裡同時有兩條連線，取鎖用其中一條，解鎖時拿到另一條）。`7234001` 是這份彙總專用的鎖鍵：同一個資料庫裡所有使用建議鎖的功能共用同一個鍵空間，所以鍵要登記在一份所有服務共用的清單裡，每個功能各佔一個值；migration 工具這類第三方套件也會用建議鎖，用兩個 int 的形式（`pg_try_advisory_xact_lock(應用程式代號, 功能代號)`）可以和套件常用的單一 bigint 鍵分開（本文的範例為了簡短用單一的 `7234001`）；不要用 `hashtext('名稱')` 臨時算出鍵，它是 PostgreSQL 的內部函式，不保證不同大版本算出一樣的值。

```go
var ok bool
c1, _ := db.Conn(ctx)
c2, _ := db.Conn(ctx)
c1.QueryRowContext(ctx, "SELECT pg_try_advisory_lock(7234001)").Scan(&ok)   // 取鎖
c2.QueryRowContext(ctx, "SELECT pg_advisory_unlock(7234001)").Scan(&ok)     // 解鎖
c1.Close() // 還回池裡，連線本身沒有關閉
c2.Close()
db.QueryRowContext(ctx, "SELECT pg_try_advisory_lock(7234001)").Scan(&ok)   // 下一輪
```

輸出的最後一行，是程式另外查 `pg_locks` 裡 `locktype = 'advisory'` 的列數：

```text
c1 lock: true
c2 unlock: false
next run lock: false
advisory locks held: 1
```

解鎖回傳 `false`，PostgreSQL 的伺服器日誌（server log）多一行 `WARNING: you don't own a lock of type ExclusiveLock`，鎖仍然由還回池裡的那條連線持有。之後只有剛好拿到那條連線的輪次會取鎖成功（session 層級的鎖可以重複取得，取幾次就要解幾次），其餘輪次都取不到而跳過，彙總時有時無，程式沒有報任何錯；要等那條連線被關掉才會恢復。連線池多久關掉一條連線各不相同：Go 的 `database/sql` 預設不會因為存活太久而關閉連線（`SetConnMaxLifetime` 預設是 0），只在連線還回池時、閒置連線超過上限（`SetMaxIdleConns`，預設 2）才關掉多出來的那幾條，恢復的時間點因此不固定，忙碌的服務常常要等到重啟；Python 的 `psycopg_pool` 預設一條連線最長用一小時（`max_lifetime`）；PHP-FPM 多半每個請求自己連線、請求結束就斷開，session 層級的鎖隨之釋放，但開了持久連線或改成常駐 worker（Laravel Octane、佇列 worker）時就和 Go 一樣。

應用程式和 PostgreSQL 之間還有 PgBouncer 這類交易模式的連線池代理時，情形更進一步：即使應用程式固定借出一條連線（Go 的 `db.Conn`）做完取鎖、工作、解鎖，代理每個交易仍可能換一條資料庫連線，session 層級的鎖照樣落在不同的連線上（見 [PostgreSQL pgBouncer 配置 + 連線池治理](/backend/01-database/vendors/postgresql/pgbouncer-config/)）。交易層級的鎖不受影響，因為它和交易一起開始、一起結束。

所以把鎖改成交易層級，並和彙總放在同一個交易裡，取鎖、彙總、推進已處理位置（如果有）就一起成功或一起撤銷，交易結束時鎖自動釋放。下面是一條連線在交易裡取交易層級的鎖，另一條連線分別在交易開著時與提交之後試著取同一把鎖：

```text
xact lock: true
other conn while tx open: false
other conn after commit: true
```

三種語言的寫法：

```go
// Go（database/sql）
err := func() error {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback()
	var ok bool
	if err := tx.QueryRowContext(ctx, "SELECT pg_try_advisory_xact_lock($1)", 7234001).Scan(&ok); err != nil {
		return err
	}
	if !ok {
		return nil // 別的實例正在彙總，這一輪跳過
	}
	// ... 在 tx 上重算 ...
	return tx.Commit()
}()
```

```php
// PHP（Laravel）
DB::transaction(function () {
    if (! DB::selectOne('SELECT pg_try_advisory_xact_lock(?) AS ok', [7234001])->ok) {
        return; // 別的實例正在彙總，這一輪跳過
    }
    // ... 重算 ...
});
```

```python
# Python（psycopg 3）：連線上沒有進行中的交易時，transaction() 是一個獨立的交易（autocommit=True 保證這一點）；
# 連線上已經有未結束的交易時，它只建立 savepoint，鎖要等外層交易結束才釋放
with conn.transaction():
    (ok,) = conn.execute("SELECT pg_try_advisory_xact_lock(%s)", (7234001,)).fetchone()
    if ok:
        ...  # 重算；ok 為 False 時別的實例正在彙總，這一輪跳過
```

交易層級的鎖也有它的靜默失效：持有鎖的實例卡住（例如停在 `idle in transaction`）時，其他實例每一輪都取不到鎖而跳過，沒有任何紀錄。兩個對策一起用：彙總的連線設 `statement_timeout` 與 `idle_in_transaction_session_timeout`，讓卡住的交易被資料庫切斷、鎖跟著釋放；並把「最後一次成功重算的時間」或「已重算到的最新小時與現在的差距」做成監控指標，超過預期就告警，跳過的輪次才會被人看見。

交易層級的鎖要求整份彙總在一個交易裡完成，彙總很長時，那個交易就會長時間開著，期間產生的死元組無法被清理。這是〈重算的成本與以小時為單位的彙總〉把每一輪讀的事件縮小到一兩個小時的另一個理由。分類規則改了之後的全量重算（見〈由事件推導出的事實與事件的保存期限〉）也要取同一把鎖，否則它和例行的重算會互相覆寫。全量重算很長，要切成一天一個交易，每個交易各自取鎖，而且用會等待的 `pg_advisory_xact_lock`：用 `pg_try_advisory_xact_lock` 的話，剛好碰上例行重算的那一天會被跳過，而且沒有任何錯誤。

MySQL 對應的是 `GET_LOCK(名稱, 0)`，它也綁在連線上、要用 `RELEASE_LOCK` 釋放，沒有交易層級的版本；用連線池時要先把一條連線借出來固定使用，取鎖、彙總、解鎖都在那條連線上做完再還回去，而且這條連線不能經過交易模式的連線池代理。

## 重送的事件：識別碼的產生位置與 ON CONFLICT 的寫法

事件改成「處理請求的程式推進佇列、背景程序批次寫入」之後，同一筆事件可能被寫入兩次。多數佇列提供的是至少一次（at-least-once，各種送達保證見 [Delivery Semantics](/backend/knowledge-cards/delivery-semantics/)）：背景程序處理到一半當掉、或處理完了還沒回報完成，佇列會把那筆事件再交給另一個消費者（見 [Redelivery](/backend/knowledge-cards/redelivery/)；消費端的去重與處理進度怎麼設計見 [3.4 consumer 設計與去重](/backend/03-message-queue/consumer-design/)，本節只處理寫進資料庫的那一步）。要讓重送不造成重複，寫入要冪等（idempotent，見 [Idempotency](/backend/knowledge-cards/idempotency/)），而冪等的前提是事件自己帶著一個識別碼，第二次寫入時認得出「這筆已經寫過」。

識別碼由資料庫配發（identity）時做不到，因為每一次 `INSERT` 都會配一個新的編號：

```text
同一筆事件重送兩次，id 由資料庫配號：count = 2
事件帶著程式產生的 click_id，ON CONFLICT (click_id) DO NOTHING：count = 1
```

所以識別碼要在事件產生的當下由程式產生，跟著事件一起進佇列。用 UUID v7 這類依時間遞增的 UUID，當索引的鍵時新值集中寫在索引的尾端，不像完全隨機的 UUID v4 分散在整棵索引樹上。集中有實際的差別：PostgreSQL 在每次 checkpoint 之後第一次改到某一頁時，要把整頁寫進 WAL（`full_page_writes`），隨機的鍵每次落在不同的頁，WAL 量明顯放大。識別碼只用來去重，不要拿它當已處理位置：它依產生的時間遞增，和 identity 一樣不等於提交的順序，各實例的時鐘也不一致。產生的寫法：Go 用 `github.com/google/uuid` 的 `uuid.NewV7()`，Laravel 用 `Str::uuid7()`，Python 3.14 起標準庫有 `uuid.uuid7()`。各種識別碼的大小與取捨見 [1.2 Schema Design 與資料建模](/backend/01-database/schema-design/)〈ID 類型選型矩陣〉。事件發生的時間（例如 `clicked_at`）也一樣，要在事件產生時由程式決定、跟著事件進佇列，不要等寫入時才用 `now()` 取，依時間分區之後的唯一約束會用到這一點。佇列自己給的訊息編號（例如 Valkey stream 的 entry ID）擋得住消費端的重送，擋不住推進佇列那一步的重試（推進逾時、程式重送一次，佇列裡就有兩筆不同編號的同一個事件），所以識別碼要在推進之前由程式產生。

由程式產生還有一個好處：寫進資料庫之前就有值，所以可以交給別的系統。例如短網址服務在轉址時把點擊識別碼附在目標網址上，電商在訂單成立時帶著它回報（postback），訂單就接得回那一次點擊。這時要預期別的系統的回報可能比事件本身更早寫進資料庫（事件還在佇列裡），所以存回報的那一張表不對事件表設外鍵，兩者在彙總時才對起來。

批次寫入時，`ON CONFLICT` 的寫法決定一批裡有重複時會發生什麼：

```text
同一個 INSERT 裡出現同一個 click_id 兩次，DO NOTHING：成功，只寫入一列
同一個 INSERT 裡出現同一個 click_id 兩次，DO UPDATE：ERROR: ON CONFLICT DO UPDATE command cannot affect row a second time
沒有寫 ON CONFLICT，批次裡有一筆已經寫過：ERROR: duplicate key value violates unique constraint，整批都沒寫入
```

沒有寫 `ON CONFLICT` 的那一種最危險：整批失敗，背景程序重試同一批，同一筆重複的事件讓整批永遠寫不進去，後面的事件跟著排隊（見 [Redelivery Loop](/backend/knowledge-cards/redelivery-loop/)）。所以事件的批次寫入用 `ON CONFLICT (識別碼) DO NOTHING`，並寫明衝突的目標是哪一個唯一約束；多個背景程序並行寫入時，每一批先依識別碼排序，避免兩批以相反的順序插入重疊的事件而死結。大批量的寫入常用 `COPY`，它不支援 `ON CONFLICT`，做法是先 `COPY` 進一張暫時表（`CREATE TEMP TABLE`），再 `INSERT INTO click_events SELECT ... FROM 暫時表 ON CONFLICT (click_id) DO NOTHING`；一批在數千筆以上、`INSERT` 的解析成本開始明顯時才值得這樣做。Laravel 的 `insertOrIgnore` 在 PostgreSQL 上產生的是沒有指定目標的 `on conflict do nothing`，表上任何一個唯一約束的衝突都會被靜默略過。事件表上除了事件識別碼，沒有其他可能衝突的唯一約束時（資料庫配號的主鍵不會衝突），它和指定目標的寫法結果相同；有的話，改寫成指定目標的 SQL，否則其他約束的衝突也會被當成重送而略過。MySQL 對應的是 `INSERT IGNORE` 與 `ON DUPLICATE KEY UPDATE`：前者除了略過重複，還會把其他錯誤（例如字串太長被截斷）降成警告，冪等寫入用後者把識別碼設回自己（`ON DUPLICATE KEY UPDATE click_id = click_id`）比較安全。

事件表改成依時間分區之後，PostgreSQL 要求唯一約束包含分區欄位（MySQL 也一樣），原本只含 `click_id` 的唯一約束要換成 `(click_id, clicked_at)`，寫入的衝突目標也跟著改成 `ON CONFLICT (click_id, clicked_at)`（只改約束、不改 SQL 的話，PostgreSQL 回 `there is no unique or exclusion constraint matching the ON CONFLICT specification`）；表上若還有 identity 的 `id` 主鍵，它也要改成包含 `clicked_at`，而改用重算或寫入時累加之後 `id` 已經沒有用途，可以拿掉，直接以 `(click_id, clicked_at)` 當主鍵，少維護一個唯一索引。重送的事件時間相同，所以仍然擋得住，前提是 `clicked_at` 跟著事件一起進佇列；寫入時才用 `DEFAULT now()` 取時間的話，重送那一次的時間不同，同一個 `click_id` 會寫成兩列。依識別碼查詢事件（例如把回報對回事件）也要多帶一個時間範圍，否則每個分區都要查一次。

## 在批次寫入的交易裡累加

〈已處理位置與交易的提交順序〉的問題，來自「寫入」與「彙總」是兩個各自進行的程序，彙總要自己判斷哪些事件還沒算過。事件本來就由背景程序批次寫入時（〈重送的事件：識別碼的產生位置與 ON CONFLICT 的寫法〉的寫入方式），可以把累加放進寫入的同一個交易裡：`INSERT ... ON CONFLICT DO NOTHING RETURNING` 只回傳這一次真正寫進去的列，用它累加到每條連結每小時一列的小時表。小時表的 `hour` 要宣告成 `timestamptz`：宣告成不帶時區的 `timestamp` 時，寫入會依連線的時區轉換，整點就不再是 UTC 的整點。

```sql
CREATE TABLE click_hourly (link_id bigint, hour timestamptz, clicks bigint NOT NULL, PRIMARY KEY (link_id, hour));
```

```sql
WITH ins AS (
  INSERT INTO click_events (click_id, link_id, clicked_at) VALUES
    ('0192f1c4-0000-7000-8000-000000000001', 1, '2026-10-06 09:10+00'),
    ('0192f1c4-0000-7000-8000-000000000002', 1, '2026-10-06 09:20+00'),
    ('0192f1c4-0000-7000-8000-000000000003', 2, '2026-10-06 09:30+00')
  ON CONFLICT (click_id) DO NOTHING
  RETURNING link_id, clicked_at
)
INSERT INTO click_hourly (link_id, hour, clicks)
SELECT link_id, date_trunc('hour', clicked_at, 'UTC'), count(*) FROM ins GROUP BY 1, 2 ORDER BY 1, 2
ON CONFLICT (link_id, hour) DO UPDATE SET clicks = click_hourly.clicks + EXCLUDED.clicks;
```

實測同一批寫兩次（模擬佇列重送），小時表的連結 1 仍是 2、連結 2 仍是 1：第二次的 `INSERT` 全部撞上 `click_id`，`RETURNING` 回傳零列，累加也就是零。晚提交的事件在它寫進來的那一刻就被算進去，不需要已處理位置，也沒有提交順序的問題。`date_trunc` 的第三個參數讓整點的計算固定用 UTC，不受連線時區影響。

它的條件與代價：

- **寫入路徑要是批次的**：每一次請求各自寫一列事件時，每一次寫入都去更新小時表的那一列，又回到熱點列；批次寫入時，一批只更新每個（連結、小時）一次。
- **分類規則改了仍要重算**：例如要排除機器人的點擊，過去的數字只能從原始事件重算，所以重算的程式還是要有，只是不必每一輪都跑。
- **多個寫入程序之間要防死結**：兩批事件碰到同一個（連結、小時）、而更新的順序不同時，PostgreSQL 可能回 `deadlock detected`。事件依 `click_id` 排序的理由同〈重送的事件：識別碼的產生位置與 ON CONFLICT 的寫法〉；小時表的累加由上面 SQL 的 `ORDER BY 1, 2` 依（連結、小時）排序，`GROUP BY` 本身不保證輸出的順序。

事件先寫進一張「待寫入事件表」、再由背景程序搬進事件表時，另一種寫法是 `DELETE FROM 待寫入事件表 WHERE id IN (SELECT id FROM 待寫入事件表 ORDER BY id LIMIT 1000 FOR UPDATE SKIP LOCKED) RETURNING ...`，一次取走一批並累加，多個實例可以平行處理不同的批次，不需要〈同一時間只讓一個實例彙總：建議鎖與連線池〉的建議鎖。

## Redis 在計數、去重與互斥裡的位置

前面各節用 PostgreSQL 處理四件事：熱點列上的計數、不重複數的彙總、重送事件的去重、彙總排程的互斥。Redis（以及與它相容的 Valkey）是把資料放在記憶體裡、由一個主執行緒依序執行命令的資料庫，Redis 對四件事都有對應的命令，而每一件能交給 Redis 到什麼程度各不相同。本節的實測用 Valkey 8.1，和前面的 pgbench 在同一台筆電的 Docker 裡，壓測程式 `valkey-benchmark` 跑在同一個容器裡、沒有經過網路，所以和 pgbench 的數字只比量級。

### 計數：INCR 的執行方式與持久化設定

`INCR` 在 Redis 裡不需要鎖：主執行緒一次只執行一個命令，同一個鍵上的遞增自然一個接一個進行，而一次遞增只是改記憶體裡的一個整數。寫盤由持久化設定決定。AOF（append-only file，把每個寫入命令附加到檔案的持久化方式）的寫盤時機由 `appendfsync` 控制：`everysec` 每秒寫盤一次，`always` 每一輪事件迴圈寫盤一次。50 條連線對同一個鍵 `INCR`，各跑三輪：

| 持久化設定                  | 每秒完成的 `INCR` 數 |
| --------------------------- | -------------------- |
| 不開 AOF（預設）            | 151,000 到 183,000   |
| AOF，`appendfsync everysec` | 98,000 到 200,000    |
| AOF，`appendfsync always`   | 5,500 到 6,500       |

`always` 也比 PostgreSQL 的熱點列（同一列更新、32 條連線，每秒 653 到 908 次）多出數倍，差別在寫盤能不能合併：Redis 在一輪事件迴圈裡處理完所有連線送來的命令，再一次寫盤，一次寫盤涵蓋很多次遞增；PostgreSQL 的熱點列上，下一個交易要等前一個交易提交、放開列鎖才能更新，每一次提交各自等一次寫盤。這和〈熱點列：同一列更新的排隊機制〉裡只新增事件比熱點列快的理由相同，事件之間沒有共用的列，提交才能合併成一次寫盤。

Redis 計數快的代價是計數的持久性。`everysec` 每一輪事件迴圈都把命令寫進 AOF 檔，Redis 程序當掉時不會遺失，主機斷電或作業系統當機時，最多遺失約一秒（背景寫盤變慢時約兩秒）的寫入；主從複寫是非同步的，主節點故障、切換到從節點時，還沒複寫過去的遞增也一起遺失；記憶體用滿時，淘汰策略（[Eviction](/backend/knowledge-cards/eviction/)）可能刪掉計數的鍵。所以 Redis 裡的計數只有兩種用法：當作要寫回資料庫的增量，或當作最近一段時間的即時數字。要寫回的增量是〈把寫入分開的三種做法：拆成多列、只新增事件、先在記憶體裡合併〉的先在記憶體裡合併，寫回的語意在那一節。即時數字不寫回，權威的數字仍然由原始事件重算：

```text
HINCRBY clicks:{連結 ID}:{UTC 整點，例如 2026-10-06T09} total 1
EXPIRE  clicks:{連結 ID}:{UTC 整點} 7200
```

轉址時累加，鍵依連結與 UTC 的整點分開、保留兩小時；保留時間要大於重算可能落後的最長時間，否則重算落後超過那個長度時，最舊那個小時的鍵已經過期而重算還沒算到。後台查「目前這個小時與前一個小時」時讀 Redis，更早的時段讀資料庫裡依原始事件重算的小時表；兩者的界線取「重算已經完成到的最新小時」，不取「現在減一小時」這類固定值，否則重算落後時，落後的那一段兩邊都沒有。Redis 遺失資料時，即時的數字偏低，下一輪重算算到那一段就被取代。這種分成兩條路徑計算的做法叫 [Lambda Architecture（批次層與即時層）](/backend/knowledge-cards/lambda-architecture/)。兩條路徑的口徑要一致或標示出來：重算時排除機器人的點擊，而轉址當下還不知道一次點擊是不是機器人，即時的數字就會比報表大。

### 跨小時的不重複數：HyperLogLog 的合併

〈重算的成本與以小時為單位的彙總〉把彙總切成每小時一列之後，「一天的不重複點擊者」不能由 24 個小時的不重複數相加得到：同一個人在兩個小時各點一次，相加會算成兩個。HyperLogLog 是估計不重複元素數量的資料結構，每個鍵在元素多時固定約 12 KB、標準誤差約 0.81%，而且兩個鍵可以合併成一個（見 [2.11 Redis data types 實作](/backend/02-cache-redis/redis-data-types/)〈HyperLogLog：基數估計〉）。實測 09 時與 10 時兩個鍵各加入 60,000 個不重複的值、其中 20,000 個兩個鍵都有（真正的聯集是 100,000）：

| 計算方式                                  | 結果    | 與真實值的差 |
| ----------------------------------------- | ------- | ------------ |
| 09 時的鍵 `PFCOUNT`                       | 59,907  | -0.2%        |
| 10 時的鍵 `PFCOUNT`                       | 59,414  | -1.0%        |
| 兩個鍵的估計值相加                        | 119,321 | +19.3%       |
| `PFCOUNT 兩個鍵`（或 `PFMERGE` 之後再數） | 100,372 | +0.4%        |

合併後的鍵佔 14,360 bytes（`MEMORY USAGE`）。所以每小時存一個 HyperLogLog，查一天時把 24 個小時的合併再數，就得到跨小時正確去重的估計值；相加則重複計算了跨小時出現的人。代價是它只給估計值、取不出成員，也無法刪掉某一個人的貢獻。HyperLogLog 放在哪裡，照〈計數：INCR 的執行方式與持久化設定〉的分法：要當權威的數字，放在資料庫的彙總表裡跟著重算，PostgreSQL 有同類的擴充套件 `postgresql-hll`（欄位型別 `hll`，查詢時用它的聚合函式合併）；Redis 裡的 HyperLogLog 只當即時數字。Redis Cluster 上，`PFCOUNT` 與 `PFMERGE` 一次操作的多個鍵要落在同一個 slot，鍵名用同一個 hash tag（例如 `uv:{連結 ID}:2026-10-06T09`），否則回 `CROSSSLOT` 錯誤。

### 去重：SET NX 的檢查與唯一約束的分工

處理請求的程式可以在推進佇列之前，用 `SET dedup:{click_id} 1 NX EX 86400` 檢查這個識別碼是否已經出現過，回 `nil` 就不推。它擋得住大部分的重送，而它的失效分兩種，後果相反。**放過重複**：標記的鍵過期或被淘汰之後，同一個識別碼會再通過一次；這一種由〈重送的事件：識別碼的產生位置與 ON CONFLICT 的寫法〉的唯一約束擋下，所以唯一約束仍然要留。**擋掉沒寫進去的事件**：標記設成功、推進佇列卻失敗時，事件沒有進到任何地方，而之後的重送又被標記擋下，這筆事件就遺失了，唯一約束補不回一筆從來沒寫進去的事件。處置是推進佇列失敗時刪掉這個標記，或改成事件寫進資料庫之後才設標記，讓 Redis 只擋已經確定寫入的重送。兩種處置都只把遺失的機會縮小：兩個步驟之間的程式中斷時，標記仍可能留下而事件沒有寫入，所以 Redis 的檢查只用來減少撞上唯一約束的次數，不當作去重的保證。

### 互斥：租約鎖與交易層級的建議鎖

Redis 上的鎖是一個帶過期時間的鍵：`SET 鎖名 隨機值 NX PX 毫秒數` 回 `OK` 就是取得，釋放時用一段 Lua 腳本比對值是不是自己放的再刪除。過期時間讓持有者當掉時鎖會自己消失，這種有期限的持有叫租約（lease，見 [Distributed Lock](/backend/knowledge-cards/distributed-lock/)）。租約的長度要事先選，選得比工作短或比工作長得多，各有一種失效：

- **租約比工作短**：實測原本的持有者取得 1 秒的租約，1.2 秒時接手的實例取得成功；原本的持有者若還在跑，兩份彙總同時在寫，正是鎖要防的情形。原本的持有者收尾時用比對值的腳本釋放，回傳 0；若直接 `DEL`，會刪掉接手的實例的鎖。GC 停頓、慢查詢都會讓工作超過租約。
- **租約比工作長得多**：持有者被強制結束（`SIGKILL`、記憶體不足被系統終止）時，鎖要等到過期才消失，期間每一輪都被跳過。Laravel 排程的 `withoutOverlapping()` 預設租約是 1440 分鐘；排程正常跑完時會釋放，被強制結束時，只有收到 `SIGTERM`、`SIGINT`、`SIGQUIT` 才會主動釋放（而且排程不是 `runInBackground()`、PHP 有載入 `pcntl` 擴充時才會）；`onOneServer()` 的鎖名帶著排程的時與分，租約 3600 秒，它防的是同一分鐘的排程在兩台機器上各跑一次，不防一份還沒跑完、下一分鐘的又開始。

交易層級的建議鎖沒有租約要選，前提是彙總的寫入和取鎖在同一個交易裡。交易提交或回滾時鎖跟著釋放；PostgreSQL 偵測到連線斷開時（用戶端正常關閉連線，或 TCP keepalive、`idle_in_transaction_session_timeout` 判定連線已經沒有回應），把交易回滾、同時釋放鎖。失去鎖的那一方，寫入隨著交易回滾而不會生效，所以不需要另外檢查持有者是不是過期的。彙總的互斥防的是兩份重算同時寫、舊結果蓋過新結果，這是正確性的問題；用租約鎖保護正確性時，要在寫入的那一端檢查遞增的編號、拒絕過期持有者的寫入（[Fencing Token](/backend/knowledge-cards/fencing-token/)），而寫入的那一端就是 PostgreSQL，鎖直接放在 PostgreSQL 比較省事。租約鎖適合重複執行只是浪費的工作，例如兩個實例同時預熱同一份快取。租約鎖的雙重持有、Redlock 與單節點的取捨、fencing token 的做法見 [2.4 distributed lock 與租約](/backend/02-cache-redis/distributed-lock/)。

同一份彙總由兩種語言排程時（〈同一時間只讓一個實例彙總：建議鎖與連線池〉裡的 Go 與 Laravel），Laravel 排程的 `withoutOverlapping()` 不適合拿來和 Go 共用一把 Redis 的鎖。它在排程結束時用 `forceRelease()` 釋放，也就是不比對值、直接 `DEL`，Go 正持有的鎖也會被它刪掉；而它寫進 Redis 的鍵名前面還有快取儲存的 prefix 與 Redis 連線設定的 prefix（`createMutexNameUsing()` 只決定 prefix 後面那一段），Go 要照完整的鍵名取鎖才看得到它。真的要兩邊共用 Redis 的鎖，Laravel 端改在工作內用 `Cache::lock()` 取鎖，它的 `release()` 會比對持有者再刪除，Go 用同一個完整鍵名、同樣比對值再刪除；即使這樣，租約比工作短與租約比工作長得多的失效也一起帶進來。

## 由事件推導出的事實與事件的保存期限

有些統計要知道「這是不是第一次」：電子報的每位收件人第一次點擊的那一天算一次不重複點擊、每位使用者第一次購買算一次新客。判斷第一次要看更早的資料，而原始事件有保存期限，超過期限就被刪掉了。在保存期限之內判斷，結果會隨時間改變：一位收件人 100 天前點過、今天又點，只保留 90 天事件的系統會把今天當成第一次。

所以這類推導出來的事實，要存在不隨事件刪除的地方：彙總表本身（每位收件人每天一列的表，「第一次」就是這張表裡最早有點擊的那一天），或者在對應的實體上記一個欄位。判斷時讀彙總表，不讀原始事件。

同一個限制也決定了全量重算（分類規則改了之後，把過去每一天都重算一次，有別於每一輪只重算最近一段時間）能涵蓋的範圍：只能涵蓋原始事件還完整存在的日期。保存期限最邊緣的那一天可能已經被刪了一部分，重算它會少算；重算時不碰保存期限以外的日期，那些日期維持原值。

## 量測用的建表語句與 pgbench 腳本

這一節重現〈熱點列：同一列更新的排隊機制〉那張吞吐量表。`-n` 是每輪開始前不清理資料表，`-c` 是連線數，`-j` 是 pgbench 用的執行緒數，`-T` 是秒數，最後一個參數是資料庫名稱；`-U` 的帳號與資料庫名稱換成手上那一台的：

```sql
CREATE TABLE link_counters (link_id bigint PRIMARY KEY, clicks bigint NOT NULL DEFAULT 0);
INSERT INTO link_counters VALUES (1, 0);
CREATE TABLE link_counter_shards (link_id bigint, shard int, clicks bigint NOT NULL DEFAULT 0, PRIMARY KEY (link_id, shard));
INSERT INTO link_counter_shards SELECT 1, g, 0 FROM generate_series(0, 9) g;
CREATE TABLE click_events (
  id         bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  link_id    bigint      NOT NULL,
  clicked_at timestamptz NOT NULL
);
```

```text
update.sql：UPDATE link_counters SET clicks = clicks + 1 WHERE link_id = 1;
shard.sql： \set s random(0, 9)
            UPDATE link_counter_shards SET clicks = clicks + 1 WHERE link_id = 1 AND shard = :s;
insert.sql：INSERT INTO click_events (link_id, clicked_at) VALUES (1, now());   -- 壓測用 now() 代替程式給的時間
```

```bash
pgbench -U postgres -n -c 1  -j 1 -T 15 -f update.sql postgres   # 同一列更新，1 條連線
pgbench -U postgres -n -c 32 -j 4 -T 15 -f update.sql postgres   # 換成 shard.sql、insert.sql 量另外兩種
PGOPTIONS='-c synchronous_commit=off' pgbench -U postgres -n -c 32 -j 4 -T 15 -f update.sql postgres
```

〈Redis 在計數、去重與互斥裡的位置〉的 `INCR` 吞吐量用 `valkey-benchmark` 量（Redis 對應的是 `redis-benchmark`），在 Redis 所在的機器或容器裡執行。`-t incr` 只跑 `INCR` 這一種命令，而且全部打在同一個鍵上；`-n` 是總請求數，`-c` 是連線數。持久化設定用 `CONFIG SET` 在兩輪之間切換。打開 AOF 會先觸發一次背景重寫，等 `INFO persistence` 的 `aof_rewrite_in_progress` 回到 `0` 再量，否則量到的是重寫期間的數字；正文 `everysec` 那一列的區間很寬，可能就混了這段雜訊。兩輪的 `-n` 不同，是因為 `always` 每秒只有幾千次，總請求數少一點讓一輪在半分鐘內跑完；比較的是每秒次數，不受總數影響。量完把兩個設定都改回原值：

```bash
valkey-benchmark -q -t incr -n 200000 -c 50                       # 不開 AOF
valkey-cli CONFIG SET appendonly yes
valkey-cli CONFIG SET appendfsync everysec                        # 換成 always 量另一列
valkey-benchmark -q -t incr -n 100000 -c 50
valkey-cli CONFIG SET appendfsync everysec
valkey-cli CONFIG SET appendonly no
```
