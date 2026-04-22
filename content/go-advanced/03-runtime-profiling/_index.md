---
title: "模組三：Runtime 與效能診斷"
date: 2026-04-22
description: "GC、memory limit、pprof、goroutine leak 與 allocation 壓力"
weight: 3
---

Runtime 診斷的核心目標是用資料判斷服務壓力來源。Go 服務長時間運行後，問題常出現在 heap 成長、GC 壓力、goroutine 數量、WebSocket buffer 堆積、JSON 配置與共享狀態保留；診斷流程應先看趨勢，再用 profile 定位來源。

本模組承接前面的並發、WebSocket 與測試可靠性：如果 goroutine lifecycle、send buffer、repository copy boundary 沒設計好，runtime 訊號會在 heap profile、goroutine profile、CPU profile 或 allocation profile 中反映出來。

## 章節列表

| 章節                    | 主題                       | 關鍵收穫                                                           |
| ----------------------- | -------------------------- | ------------------------------------------------------------------ |
| [3.1](gc-memory-limit/) | GC 與 memory limit         | 理解 heap、GOGC、memory limit 與 runtime metrics 的關係            |
| [3.2](pprof/)           | pprof 基礎診斷流程         | 用 heap、goroutine、CPU、trace profile 定位壓力來源                |
| [3.3](goroutine-leak/)  | goroutine leak 偵測        | 從 stack pattern 回到 context、close、deadline 與 ticker lifecycle |
| [3.4](allocation/)      | 資料結構與 allocation 壓力 | 區分必要 copy、安全邊界與可優化熱路徑配置                          |

## 本模組使用的範例主題

本模組使用虛構的即時通知服務作為範例。範例包含 WebSocket client lifecycle、background worker、repository list、JSON push payload 與 cache。

範例只用來展示 Go runtime 診斷方法，不假設讀者正在維護任何特定專案。

## 本模組的 Go 核心概念

- 用 `runtime.ReadMemStats` 或 `runtime/metrics` 觀察 heap、GC 與 goroutine 趨勢。
- 用 `debug.SetMemoryLimit` 給 runtime 軟性記憶體目標。
- 用 pprof 分析 heap、goroutine、CPU、block、mutex 與 trace。
- 用 goroutine profile 找出卡在 channel、network read、ticker、mutex 的路徑。
- 用 `alloc_space` 與 `inuse_space` 區分配置壓力與保留記憶體。
- 用資料結構設計降低不必要 allocation，但保留必要 copy boundary。

## 學習重點

學完本模組後，你應該能判斷：

1. 記憶體問題是 GC 壓力、長期保留，還是短暫尖峰
2. 什麼情境適合調整 memory limit，什麼情境應該找 leak
3. heap、goroutine、CPU、trace 各自回答什麼問題
4. goroutine leak 應回到哪個 lifecycle 邊界修
5. allocation 優化何時值得做，何時會破壞安全邊界

## 本模組不處理

本模組不討論分散式 tracing 平台、完整監控系統或雲端特定 profiler。這些工具可以接在本模組之後；本模組先建立 Go runtime 原生訊號與 pprof 的診斷思路。後續可接 [Observability pipeline、metrics 與 tracing](../07-distributed-operations/observability-pipeline/)。

## 學習時間

預計 3-4 小時
