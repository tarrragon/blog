---
title: "Advisory Lock（建議鎖）"
date: 2026-10-06
description: "多個服務實例的排程要確保同一時間只有一份在跑，或排程每一輪都跳過、PostgreSQL 的伺服器日誌出現 you don't own a lock 時，查建議鎖持有在哪一條連線、哪一個交易上，以及 session 層級與交易層級（pg_try_advisory_xact_lock）的差別"
weight: 463
tags: ["backend", "database", "postgresql", "lock", "knowledge-card"]
---

建議鎖（advisory lock）是資料庫提供、但意義由應用程式自己決定的鎖：它不鎖任何一列或一張表，只鎖一個應用程式指定的鍵（PostgreSQL 是一個 bigint，或兩個 int 組成的鍵，兩種寫法的鍵互不相通），取得與釋放都由程式明確呼叫。「建議」的意思是資料庫不強制：沒有去取這把鎖的程式照樣能讀寫任何資料，只有同樣去取這把鎖的程式會被擋下。其他中文資料常寫作諮詢鎖。最常見的用途是讓多個服務實例上的同一個排程同一時間只有一份在執行，不必另外架設 [Distributed Lock](/backend/knowledge-cards/distributed-lock/) 用的協調服務；它和交易對資料列取得的列鎖是兩套機制，彼此不互相阻擋（各種鎖的分類見 [PostgreSQL MVCC + Lock Model：為什麼 PG 比 MySQL 少 deadlock、但 vacuum 是別的代價](/backend/01-database/vendors/postgresql/mvcc-lock-model/)〈PG 的 lock：row-level、table-level、advisory、predicate〉）。

## 概念位置

PostgreSQL 的建議鎖依持有的範圍分兩種：

| 種類         | 取得                                                         | 釋放                                                |
| ------------ | ------------------------------------------------------------ | --------------------------------------------------- |
| session 層級 | `pg_advisory_lock(鍵)`、不等待的 `pg_try_advisory_lock(鍵)`  | 同一條連線呼叫 `pg_advisory_unlock(鍵)`，或連線關閉 |
| 交易層級     | `pg_advisory_xact_lock(鍵)`、`pg_try_advisory_xact_lock(鍵)` | 交易結束時自動釋放，沒有解鎖的函式                  |

應用程式經由 [Connection Pool](/backend/knowledge-cards/connection-pool/) 使用資料庫時，「同一條連線」這個條件不由程式控制：取鎖與解鎖是兩次呼叫，池可能交給它兩條不同的連線。應用程式和資料庫之間還有交易模式的連線池代理（PgBouncer；每個交易結束就把資料庫連線收回，下一個交易可能換一條）時，即使應用程式固定使用同一條連線，代理每個交易仍可能換一條資料庫連線，session 層級的鎖一樣落在不同的連線上（見 [PostgreSQL pgBouncer 配置 + 連線池治理](/backend/01-database/vendors/postgresql/pgbouncer-config/)）。MySQL 對應的 `GET_LOCK` 與 `RELEASE_LOCK` 也綁在連線上，而且沒有交易層級的版本。

## 可觀察訊號與例子

- **排程每一輪都跳過**：session 層級的鎖在一條連線上取得、在另一條連線上解鎖時，解鎖回傳 `false`，PostgreSQL 的伺服器日誌（server log）出現 `WARNING: you don't own a lock of type ExclusiveLock`，鎖仍然由還回池裡的那條連線持有；之後只有剛好拿到那條連線的輪次會執行，其餘都跳過，直到那條連線被關掉。實測與三種語言的寫法見 [1.18 高頻計數的寫入與彙總：熱點列的鎖、只新增的事件、可以重跑的彙總與重送的事件](/backend/01-database/high-frequency-counting/)〈同一時間只讓一個實例彙總：建議鎖與連線池〉。
- **鎖被取得了好幾次**：session 層級的鎖可以重複取得，同一條連線取兩次要解兩次。`pg_locks` 不論取得幾次都只有一列，看不出次數；解鎖一次之後 `locktype = 'advisory'` 的那一列仍在，代表同一條連線（看 `pid` 欄）取得過不只一次，要解到回傳 `false` 為止。
- **鍵撞在一起**：同一個資料庫裡所有功能共用同一個鍵空間，兩個無關的排程用了同一個整數，會互相擋住；migration 工具這類第三方套件也用建議鎖，自訂的鍵改用兩個 int 的形式（應用程式代號、功能代號），和套件常用的單一 bigint 鍵分開。
- **持有者卡住**：交易層級的鎖也會靜默失效。持有鎖的實例停在 `idle in transaction` 時，其他實例每一輪都取不到鎖而跳過；用 `idle_in_transaction_session_timeout` 讓資料庫切斷它，並監控「最後一次成功執行的時間」。

## 設計責任

用連線池的服務，排程互斥優先用交易層級的鎖，把取鎖與整份工作放在同一個交易裡；工作必須跨好幾個交易時，先從池裡借出一條連線固定使用（Go 的 `db.Conn`），取鎖、工作、解鎖都在那條連線上做完再還回去。鎖鍵集中定義在一份常數檔裡，每個功能各佔一個值；不要用 `hashtext()` 這類內部函式臨時算，它不保證不同大版本算出一樣的值。中間有交易模式的連線池代理時，只能用交易層級的鎖。交易層級的鎖讓交易在整份工作期間都開著，工作要切小，長交易會擋住舊列版本的清理。
