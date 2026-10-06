---
title: "Transaction Propagation（交易傳遞）"
date: 2026-10-06
description: "多個 repository 的寫入要在同一個交易裡完成，或一段程式在交易失敗後仍留下部分寫入、交易裡的某個查詢卡住直到逾時時，查交易物件怎麼傳到每一個資料存取呼叫"
weight: 461
tags: ["backend", "database", "transaction", "knowledge-card"]
---

交易傳遞（transaction propagation）處理兩件事：一個在某處開始的 [Transaction](/backend/knowledge-cards/transaction/)，怎麼讓後續每一個資料存取呼叫都跑在它裡面；以及一個「自己需要交易」的函式在已經有交易的地方被呼叫時，要加入那個交易、另開一個，還是在裡面設一個儲存點（savepoint）。哪些寫入該放進同一個交易是 [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/) 決定的；交易傳遞是把那個邊界落實到程式碼的機制。Java 的 Spring 把巢狀呼叫時的這幾個選項取了名字（`REQUIRED` 加入既有交易、`REQUIRES_NEW` 另開一個、`NESTED` 用儲存點），英文資料多半沿用這組詞。

## 概念位置

交易屬於一條資料庫連線，所以「怎麼傳」取決於程式碼裡的資料存取呼叫怎麼拿到連線：

- **隱含傳遞**：一個請求或一個執行緒固定用同一條連線，連線物件自己記著「目前在交易裡」。Laravel（PHP-FPM 下每個請求一條連線）、Django（每個執行緒一條連線）都是這一種：`DB::transaction` 或 `transaction.atomic` 裡面呼叫的任何 model 方法，自然就在交易裡。巢狀呼叫時兩者都改用儲存點：內層失敗時先撤銷到儲存點，再把例外丟給外層，外層攔下例外才只撤銷內層的寫入，沒有攔下就整個交易撤銷。SQLAlchemy 的 `Session` 也持有交易，同一個 session 上的操作都在裡面，`begin_nested()` 設儲存點。Django 另有 `ATOMIC_REQUESTS` 設定，把整個請求包成一個交易，請求裡的每一個寫入自然都在同一個交易裡。
- **明確傳遞**：程式向連線池取連線，每一次呼叫可能拿到不同的連線。Go 屬於這一種：`*sql.Tx`、`pgx.Tx` 或 GORM 交易函式的參數 `tx` 要一路傳給每一個 repository，用了外面的 `db` 就從池裡另取一條連線、跑在交易之外。傳的方式有參數傳遞與放進 `context` 兩種，Repository Adapter 實作那一篇稱為 unit of work 的寫法（由服務層開交易、把交易物件當參數交給每個 repository）屬於參數傳遞（取捨見 [1.4 Repository Adapter 實作](/backend/01-database/repository-adapter/)〈Transaction 傳遞〉），常見的寫法是讓 repository 接受一個連線池與交易都符合的介面（sqlc 產生的 `DBTX`、GORM 的 `*gorm.DB`）。GORM 的交易函式裡再呼叫 `tx.Transaction` 時，實測送出的是 `SAVEPOINT` 與 `ROLLBACK TO SAVEPOINT`。

儲存點只能在同一條連線、同一個交易裡建立，跨資料庫或跨服務的寫入不在這個機制的範圍內，要改用 outbox 或補償流程（見 [Outbox Pattern](/backend/knowledge-cards/outbox-pattern/)）。

## 可觀察訊號與例子

- **交易失敗後留下部分寫入**：交易已經撤銷，其中一筆寫入卻還在。那一筆是在交易外的連線上執行的，自動提交了。
- **交易裡的某個查詢卡到逾時**（明確傳遞的語言才有）：交易先 `UPDATE` 了某一張訂單（拿到這一列的鎖），接著程式誤用連線池上的 `db` 再更新同一列。這個誤用的 `UPDATE` 在另一條連線上等那把鎖，而鎖要等交易結束才釋放，交易又在等這個 `UPDATE` 回來。資料庫看到的只是一條連線在等另一條閒置中的交易，不構成它能偵測的死結，所以不會報錯；實測要等到 context 的逾時（`timeout: context deadline exceeded`）才結束；在連線上設 PostgreSQL 的 `lock_timeout`，可以讓等鎖的語句提早失敗，錯誤訊息直接指出是在等鎖。連線池上限是 1 時，誤用的 `db` 連一條連線都借不到，同樣等到逾時。
- **同一個交易的語句出現在不同連線上**：PostgreSQL 的 `log_line_prefix` 加上 `%p`（後端程序 ID）之後，同一個交易該有的語句出現在兩個不同的 ID 底下。

## 設計責任

一個專案只用一種傳遞方式，並且寫進 repository 的簽章：參數傳遞就讓每個方法都收交易或連線的介面，放進 `context` 就讓每個 repository 都從同一個 key 取。隱含傳遞的框架要注意的是相反的情形：需要獨立提交的寫入（例如交易失敗也要留下的稽核紀錄）要明確用另一條連線或在交易外寫。巢狀呼叫時用儲存點還是加入外層交易，各框架的預設不同，跨框架移植程式時要重新確認。
