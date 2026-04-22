---
title: "3.8 defer 與資源清理"
date: 2026-04-22
description: "用 defer 管理 close、unlock、cleanup 與 panic 邊界"
weight: 8
---

`defer` 的核心用途是把資源清理放在取得資源的附近。檔案、鎖、response body、temporary resource 與測試 cleanup 都適合用 `defer` 表達「離開這個 scope 前要完成的事」。

## 預計補充內容

1. `defer` 的執行時機與 LIFO 順序。
2. file close、mutex unlock、HTTP response body close。
3. loop 中使用 `defer` 的成本與 scope 問題。
4. `panic`、`recover` 與 application error 的邊界。
5. test cleanup 與 `t.Cleanup` 的比較。

## 與 Go 進階的關係

本章建立基本資源清理語感。長時間 worker、WebSocket pump 與 graceful shutdown 會在 [Go 進階：select loop 的生命週期設計](../../go-advanced/01-concurrency-patterns/select-loop/) 與 [graceful shutdown 與 signal handling](../../go-advanced/06-production-operations/graceful-shutdown/) 中延伸。
