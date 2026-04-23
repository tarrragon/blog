---
title: "7.7 composition root 與依賴組裝"
date: 2026-04-22
description: "把具體 adapter、config 與 usecase wiring 留在應用入口層"
weight: 7
---

composition root 的核心責任是集中建立具體依賴。domain 與 application 應依賴 port；`main` 或啟動層負責讀取 config、建立 adapter、組裝 usecase、註冊 handler 與啟動 server。

## 本章目標

學完本章後，你將能夠：

1. 理解 composition root 為什麼要集中在啟動層
2. 分辨 port、adapter 與 usecase 的組裝責任
3. 用 typed config 讓 wiring 依賴可讀、可測、可替換
4. 看懂哪些依賴應在 `main` 組裝，哪些不該散在 handler 裡
5. 讓啟動層只負責「把系統接起來」，不負責業務規則

---

## 【觀察】composition root 是整個應用的接線板

composition root 的核心用途不是做更多抽象，而是把具體依賴集中在一個地方建立。這個地方通常是 `main()`、`cmd/.../main.go` 或啟動層 package。

當讀者打開入口程式時，應該能直接看到：

- config 從哪裡來
- repository 怎麼建立
- publisher / worker / server 怎麼串起來
- 哪些 dependency 是 mockable port
- 哪些是明確的外部 adapter

這種集中式 wiring 的好處是：

- 依賴方向清楚
- 測試替身好替換
- 啟動問題容易定位
- 不會把建構邏輯散落到各個 handler 或 usecase

## 【判讀】dependency injection 的重點是方向

Go 的依賴注入通常不需要框架。真正的重點是：高層只依賴 port，低層在入口被組裝進來。

例如：

```go
type App struct {
    jobs JobRepository
    log  EventLog
}

func NewApp(jobs JobRepository, log EventLog) *App {
    return &App{jobs: jobs, log: log}
}
```

`main()` 負責建立具體實作，再傳給 `NewApp`：

```go
func main() {
    cfg := LoadConfig()

    repo := NewSQLJobRepository(cfg.DatabaseDSN)
    eventLog := NewRedisEventLog(cfg.RedisAddr)
    app := NewApp(repo, eventLog)

    server := NewHTTPServer(app)
    log.Fatal(server.ListenAndServe())
}
```

這裡沒有框架，但依賴方向已經清楚：`App` 不知道 SQL 或 Redis 是怎麼接的。

## 【策略】typed config 先收斂設定，再進行組裝

composition root 會變亂，通常不是因為依賴太多，而是設定沒有先整理成型別清楚的 config。把環境變數、flag 與預設值先集中讀成結構體，wiring 會清楚很多。

```go
type Config struct {
    HTTPAddr   string
    DatabaseDSN string
    RedisAddr  string
}
```

load config 的責任是把外部輸入變成可預期的程式設定，而不是在每個 adapter 初始化時各自讀環境變數。

## 【執行】建立 adapter 後再注入 usecase

常見的組裝順序是：

1. 讀 config。
2. 建立 logger / [metrics](../../backend/knowledge-cards/metrics) / tracer。
3. 建立 [database](../../backend/knowledge-cards/database) / cache / [broker](../../backend/knowledge-cards/broker) client。
4. 建立 repository 與 service。
5. 建立 handler 或 server。
6. 啟動背景 worker 與 HTTP server。

這樣做可以讓初始化失敗在入口層就被看見，不會等到請求進來才爆。

## 【判讀】組裝邏輯應集中在入口層

如果 handler 自己 new repository、new client、new worker，就會出現這些問題：

- 測試無法替換依賴
- 生命週期很難控制
- 每個 request 都可能建立不必要的資源
- 啟動路徑與請求路徑混在一起

handler 應該只接收已組裝好的依賴，專心處理輸入和回應。

## 【延伸】Backend 教材負責具體外部服務語意

Go 章節只需要知道依賴怎麼接，真正的外部服務語意留給 Backend 教材：

- database client 建立、pool 與 [transaction](../../backend/knowledge-cards/transaction) 語意
- Redis client、pipeline 與 cache 邊界
- broker connection、[durable [queue](../../backend/knowledge-cards/queue)](../../backend/knowledge-cards/durable-queue) 與重試
- platform secret、runtime limit 與部署環境

Go 的 composition root 不需要重複教這些技術，只要把它們正確接上即可。

## 與 Backend 教材的分工

本章處理 Go 程式如何組裝依賴。資料庫連線池、Redis client、broker connection、container secret 與平台設定會放在 Backend 對應模組；Go 章節只保留「誰依賴誰」與「在哪裡組裝」的設計。
