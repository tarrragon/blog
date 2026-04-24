---
title: "3.8 defer 與資源清理"
date: 2026-04-22
description: "用 defer 管理 close、unlock、cleanup 與 panic 邊界"
weight: 8
---

`defer` 的核心用途是把資源清理放在取得資源的附近。檔案、鎖、response body、temporary resource 與測試 cleanup 都適合用 `defer` 表達「離開這個 scope 前要完成的事」。

## 預計補充內容

這些資源清理邊界會在下列章節展開：

- [Go 進階：select loop 的生命週期設計](/go-advanced/01-concurrency-patterns/select-loop/)：長生命週期的 goroutine 會怎麼收尾，和 `defer` 的 scope 觀念直接相關。
- [Go 進階：graceful shutdown 與 signal handling](/backend/knowledge-cards/graceful-shutdown/)：當 process 要停下來時，`defer` 常常是 cleanup 的最後一道保險。
- [Go 入門：testing 基礎](/go/05-error-testing/testing-basics/)：測試裡的資源回收與 `t.Cleanup`，會比單純 close 更能說清楚責任。

## 與 Go 進階的關係

本章建立基本資源清理語感。長時間 worker、[WebSocket](/backend/knowledge-cards/websocket/) pump 與 [graceful shutdown](/backend/knowledge-cards/graceful-shutdown/) 會在 [Go 進階：select loop 的生命週期設計](/go-advanced/01-concurrency-patterns/select-loop/) 與 [graceful shutdown 與 signal handling](/backend/knowledge-cards/graceful-shutdown/) 中延伸。

## 和 Go 教材的關係

這一章承接的是資源生命週期、goroutine 停止與 shutdown；如果你要先回看語言教材，可以讀：

- [Go：goroutine：輕量並發工作](/go/04-concurrency/goroutine/)
- [Go：select：同時等待多種事件](/go/04-concurrency/select/)
- [Go 進階：goroutine leak 偵測](/go-advanced/03-runtime-profiling/goroutine-leak/)
- [Go 進階：graceful shutdown 與 signal handling](/backend/knowledge-cards/graceful-shutdown/)
