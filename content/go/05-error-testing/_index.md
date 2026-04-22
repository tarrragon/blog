---
title: "模組五：錯誤處理與測試"
date: 2026-04-22
description: "用明確錯誤路徑、testing、table-driven test 與時間注入驗證 Go 程式"
weight: 5
---

# 模組五：錯誤處理與測試

Go 的錯誤處理偏向顯式：錯誤是回傳值，呼叫者要直接面對。Go 的測試也偏向直接：建立輸入、執行函式、檢查輸出。本模組把錯誤處理、單元測試、table-driven test、HTTP 測試與並發測試串成一組可落地的驗證方法。

## 章節列表

| 章節 | 主題 | 關鍵收穫 |
|------|------|---------|
| [5.1](errors/) | 錯誤回傳與早期返回 | 寫出可追蹤的失敗路徑 |
| [5.2](testing-basics/) | testing 基礎 | 用 `testing` package 驗證函式行為 |
| [5.3](table-driven-test/) | table-driven test | 用表格整理多組輸入輸出 |
| [5.4](http-handler-test/) | HTTP handler 測試 | 用 `httptest` 驗證 request/response |
| [5.5](time-injection/) | 時間注入與 deterministic test | 避免測試依賴真實時間 |
| [5.6](concurrency-test/) | 並發行為測試 | 測試 channel、goroutine 與狀態更新 |

## 本模組使用的範例主題

- 函式單元測試
- table-driven test
- HTTP handler 測試
- 時間相關測試
- channel 與 goroutine 測試

## 學習時間

預計 2 小時
