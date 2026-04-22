---
title: "模組四：並發模型"
date: 2026-04-22
description: "從 goroutine、channel、select 與 RWMutex 理解 Go 並發模型"
weight: 4
---

Go 的並發不是只會寫 `go func()`。Go 的並發模型包含工作如何啟動、資料如何傳遞、取消如何傳播、共享狀態如何保護。本模組從語言機制出發，再延伸到 worker、事件處理與網路服務情境。

## 章節列表

| 章節              | 主題                       | 關鍵收穫                             |
| ----------------- | -------------------------- | ------------------------------------ |
| [4.1](goroutine/) | goroutine：輕量並發工作    | 啟動並發工作並設計退出條件           |
| [4.2](channel/)   | channel：資料傳遞與背壓    | 用 channel 在 goroutine 之間傳遞資料 |
| [4.3](select/)    | select：同時等待多種事件   | 實作 event loop                      |
| [4.4](rwmutex/)   | sync.RWMutex：保護共享狀態 | 安全讀寫共享資料                     |

## 本模組使用的範例主題

- worker pool 與背景工作
- producer / consumer 資料流
- ticker 與取消訊號
- 共享狀態的讀寫鎖
- 非阻塞送出與背壓

## 學習時間

預計 90-120 分鐘
