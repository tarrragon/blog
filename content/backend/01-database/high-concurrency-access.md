---
title: "1.1 高併發下的 SQL 讀寫邊界"
date: 2026-04-22
description: "說明高併發服務如何共用資料庫 client、控制 transaction 與避免資料庫成為瓶頸"
weight: 1
---

高併發服務處理 SQL 的核心原則是共用資料庫 client，並讓 [connection pool](/backend/knowledge-cards/connection-pool/) 管理連線生命週期。當並發升高時，真正要控制的是連線數、交易範圍、查詢時間與下游壓力；每個 request 各自建立連線會放大握手、排隊與資源回收成本。

## 本章目標

學完本章後，你將能夠：

1. 理解資料庫 client 為什麼應該共用
2. 分辨 query、exec、rows 與 [transaction](/backend/knowledge-cards/transaction/) 的不同邊界
3. 了解連線池參數對高併發的影響
4. 用 `context` 與 [timeout](/backend/knowledge-cards/timeout/) 控制慢查詢
5. 避免長 transaction、慢掃描與過量並發把資料庫壓爆

---

## 【觀察】資料庫 client 通常代表連線池入口

多數後端語言的資料庫 client 都會包住連線池或連線管理能力。一般情況下，服務會在啟動時建立可重用的 [database](/backend/knowledge-cards/database/) handle，讓 request handler、worker 或 service layer 共用它，並在需要時從池子裡取出可用連線。

這種模型的好處是：

- 呼叫端不用自己管理每個連線的生命週期
- 多個 request 或 worker 可以同時發出資料庫操作
- 連線回收與重用由 `sql.DB` 處理

## 【判讀】高併發需要有界連線

高併發時的核心風險是把 application concurrency 誤解成 database concurrency。語言端的 thread、task、coroutine 或 goroutine 可能很容易建立，但資料庫有自己的容量上限；連線池只是把壓力從應用端平滑地送到下游，無法消滅壓力。

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
- 熱讀資料可以在上層加 cache，同時保留資料庫作為正式狀態來源。

### 寫入

- transaction 只包住真正需要一致性的範圍。
- transaction 範圍只保留必要資料操作，外部 API 呼叫、使用者等待或長迴圈應放在交易外。
- 高衝突寫入要搭配重試、唯一鍵或明確去重策略。
- 需要高吞吐時，先評估批次化、分段處理與有界並發。

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

## 【策略】慢查詢要靠 timeout 與上層限流處理

在高併發服務裡，database timeout 應由 request timeout、client timeout 與資料庫 timeout 共同定義。語言端需要能把取消、[deadline](/backend/knowledge-cards/deadline/) 或 timeout 往資料庫 client 傳遞，讓慢查詢在合理時間內釋放資源。

如果下游開始變慢，通常要搭配：

- request-level timeout
- [worker pool](/backend/knowledge-cards/worker-pool/) 或 semaphore
- [queue](/backend/knowledge-cards/queue/) 長度限制
- 降級或拒絕策略

這樣做的目標是避免應用自己堆出大量等待中的工作，最後把問題放大成整個服務卡死。

## 【延伸】語言端的責任是邊界

這一章不討論 PostgreSQL、MySQL、SQLite 的語法差異，也不討論 [migration](/backend/knowledge-cards/migration/) 工具本身。語言端需要掌握的是：怎麼共用 database client、怎麼控制並發、怎麼縮小 transaction、怎麼把 timeout 和取消傳下去。

具體 schema、index、[isolation level](/backend/knowledge-cards/isolation-level/) 與 migration 寫法，會放在這個模組的其他資料庫教材中。

## 跨語言適配評估

資料庫高併發邊界會受語言 runtime 影響。Thread-based runtime 要管理 thread pool 與 connection pool 的比例；async runtime 要確認 database driver 是否真正非阻塞；輕量 task runtime 要限制同時查詢數量，避免把大量 task 轉成下游連線壓力。強型別語言可以用型別保護 row mapping 與錯誤分類；動態語言則需要用 migration、runtime validation、[contract](/backend/knowledge-cards/contract/) test 與 fixture 保護 schema 邊界。

## 小結

高併發下處理 SQL 的核心原則是：database client 共用、連線池可控、transaction 要短、rows 要關、timeout 要傳遞、下游壓力要限流。應用端並發可以很多，但資料庫連線必須受控，這兩者的邊界要分開管理。
