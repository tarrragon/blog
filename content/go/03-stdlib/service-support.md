---
title: "3.10 標準庫如何支撐服務型 Go"
date: 2026-04-23
description: "把 context、net/http、log/slog、defer 與 time 連成服務底座"
weight: 10
---

這一章不是再教一次標準庫 API，而是把前面學過的工具串成一個事實：Go 之所以適合服務型應用，很大一部分原因是標準庫已經直接支撐了 HTTP、timeout、取消、日誌與資源管理。

## 本章目標

學完本章後，你將能夠：

1. 看出標準庫為什麼是 Go 服務的底座
2. 把 `context`、`net/http`、`log/slog`、`defer` 與 `time` 串成一個服務模型
3. 理解為什麼這些工具會讓服務更可維護
4. 把標準庫能力轉成實際服務邊界
5. 知道何時標準庫已足夠，何時才需要外部框架

---

## 【觀察】標準庫本身就能做服務

Go 的標準庫不是只能拿來寫練習題。`net/http` 可以直接建立服務，`context` 可以控制取消與 timeout，`log/slog` 可以支援結構化日誌，`defer` 可以整理資源釋放，`time` 可以處理期限與排程。

這些能力拼在一起，就是一個後端服務最基本的底盤。

## 【判讀】context 是服務生命週期的中心

在服務型 Go 裡，`context` 不是可有可無的參數，而是請求、取消與 deadline 的共同語言。當 handler、worker、DB、Redis 都接受 context 時，整個流程就能在同一個生命週期邊界內運作。

## 【判讀】net/http 讓入口保持簡單

`net/http` 的 handler 模型很薄，這是優點。它讓你能快速建立路由、驗證 request、回傳 response，而不需要先學一大套框架約定。對服務型 Go 來說，這種簡單性會直接降低協作成本。

## 【策略】log 與 defer 讓邊界更完整

`log/slog` 提供結構化日誌，讓高併發服務的診斷更容易；`defer` 則讓 close、unlock、cancel 等收尾操作更安全。這兩個工具都是 Go 在長時間運行服務中很重要的可靠性支撐。

## 小結

標準庫不是 Go 的附屬品，而是它能成為服務語言的核心原因之一。當你把 `context`、`net/http`、`log/slog`、`defer` 與 `time` 看成一組工具時，就更容易理解 Go 為什麼適合做後端服務。
