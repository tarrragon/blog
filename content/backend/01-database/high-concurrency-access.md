---
title: "1.1 高併發下的 SQL 讀寫邊界"
date: 2026-04-22
description: "說明 Go 服務在高併發下如何共用 sql.DB、控制 transaction 與避免資料庫成為瓶頸"
weight: 1
---

Go 服務在高併發下處理 SQL 的核心，不是把每個 request 都當成獨立連線去打資料庫，而是把 `sql.DB` 當成可共用的資料庫把手，讓 connection pool 負責管理連線生命週期。當並發升高時，真正要控制的是連線數、交易範圍、查詢時間與下游壓力，而不是單純把 goroutine 開多。

## 本章目標

學完本章後，你將能夠：

1. 理解 `sql.DB` 為什麼應該共用
2. 分辨 query、exec、rows 與 transaction 的不同邊界
3. 了解連線池參數對高併發的影響
4. 用 `context` 與 timeout 控制慢查詢
5. 避免長 transaction、慢掃描與過量並發把資料庫壓爆

---

## 【觀察】`sql.DB` 是連線池，不是單一連線

Go 的 `database/sql` 不是要求你手動開一條連線、用完再關掉。一般情況下，你會建立一個 `*sql.DB`，它代表的是連線池與操作入口。這個把手可以被多個 goroutine 安全共用，並在需要時從池子裡取出可用連線。

這種模型的好處是：

- 呼叫端不用自己管理每個連線的生命週期
- 多個 goroutine 可以同時發出資料庫操作
- 連線回收與重用由 `sql.DB` 處理

## 【判讀】高併發不是無限開連線

高併發時最常見的錯誤，是把 goroutine 的便宜誤解成資料庫連線也可以無限開。事實上，資料庫有自己的容量上限，連線池只是把壓力從應用端平滑地送到下游，不會消滅壓力。

連線池調校的核心觀念是：

- `SetMaxOpenConns` 太低，request 會在應用端排隊。
- `SetMaxOpenConns` 太高，可能把 DB 直接打滿。
- `SetMaxIdleConns` 影響高峰與尖峰之間的重用效率。
- `SetConnMaxLifetime` / `SetConnMaxIdleTime` 影響長連線與資源回收節奏。

## 【策略】讀取與寫入要分開看

讀取的核心風險通常是慢查詢、掃描過大、N+1、熱點資料與連線被占住太久。寫入的核心風險則常常是 transaction 太大、衝突太高、鎖時間太長、重試邏輯不清楚。

### 讀取

- 用索引支援常見查詢條件。
- 避免一次載入過多資料。
- 需要分頁時，先考慮游標或穩定排序。
- 熱讀資料可以在上層加 cache，但不要把 cache 當成唯一保證。

### 寫入

- transaction 只包住真正需要一致性的範圍。
- 不要把外部 API 呼叫、使用者等待或長迴圈放進 transaction。
- 高衝突寫入要搭配重試、唯一鍵或明確去重策略。
- 需要高吞吐時，先想能否批次化，而不是單筆無限並發。

## 【執行】查詢與 rows 的生命週期要收乾淨

查詢回傳 rows 後，呼叫端要負責把它關掉，並檢查迭代錯誤。這不只是記憶體管理問題，也會影響連線何時能回到池子裡。

典型模式是：

```go
rows, err := db.QueryContext(ctx, "SELECT id, name FROM users WHERE status = ?", status)
if err != nil {
    return err
}
defer rows.Close()

for rows.Next() {
    var id int64
    var name string
    if err := rows.Scan(&id, &name); err != nil {
        return err
    }
}
if err := rows.Err(); err != nil {
    return err
}
```

## 【策略】慢查詢要靠 context 與上層限流處理

在高併發服務裡，database timeout 不應該只靠資料庫自己等。Go 端應該把 `context` 傳進去，讓請求取消、deadline 與上層 timeout 能往下傳播。

如果下游開始變慢，通常要搭配：

- request-level timeout
- worker pool 或 semaphore
- queue 長度限制
- 降級或拒絕策略

這樣做的目的，是避免應用自己堆出大量等待中的 goroutine，最後把問題放大成整個服務卡死。

## 【延伸】Go 端的責任是邊界，不是資料庫選型

這一章不討論 PostgreSQL、MySQL、SQLite 的語法差異，也不討論 migration 工具本身。Go 端需要掌握的是：怎麼共用 `sql.DB`、怎麼控制並發、怎麼縮小 transaction、怎麼把 timeout 和取消傳下去。

具體 schema、index、isolation level 與 migration 寫法，會放在這個模組的其他資料庫教材中。

## 和 Go 教材的關係

這一章是資料庫實作層；如果你要先理解 Go 端為什麼會這樣設計，可以先回去看：

- [Go 並發模型總覽](../../go/04-concurrency/concurrency-model/)：先理解 goroutine 與下游邊界的關係。
- [bounded worker pool](../../go-advanced/01-concurrency-patterns/worker-pool/)：先看 Go 怎麼把並發限制成有界容量。
- [Go：建立 repository port](../../go/06-practical/repository-port/)：先看語言教材怎麼隔離資料庫依賴。

## 小結

Go 在高併發下處理 SQL 的核心原則是：`sql.DB` 共用、連線池可控、transaction 要短、rows 要關、timeout 要傳遞、下游壓力要限流。goroutine 可以很多，但資料庫連線不行，這兩者的邊界不能混在一起。
