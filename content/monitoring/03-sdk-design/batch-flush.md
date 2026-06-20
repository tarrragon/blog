---
title: "攢批送出策略"
date: 2026-06-19
description: "flush interval / buffer size / flush on close 三個控制點決定事件何時離開 SDK — 平衡即時性和網路效率"
weight: 3
tags: ["monitoring", "sdk", "batch", "flush", "buffer"]
---

攢批送出策略控制事件從 SDK 內部 buffer 送到 collector 的時機。事件產生後先進入記憶體 buffer，累積到一定數量或間隔一定時間後，一次性透過 HTTP POST 送出整批事件。攢批的目的是減少網路請求次數 — 100 筆事件合併成一個 HTTP 請求，比 100 個獨立請求的網路開銷低。

## 三個觸發條件

### 時間觸發（flush interval）

固定間隔自動 flush。SDK 在 init 時啟動計時器，每隔 N 毫秒檢查 buffer 是否有待發事件，有則送出。

合理的間隔範圍：10-60 秒。間隔太短（1 秒）接近逐筆送出，失去攢批的效益；間隔太長（5 分鐘）可能讓事件延遲到達 collector，影響即時監控和告警的反應速度。

自用工具場景下 30 秒是合理的預設 — 事件量低，30 秒的延遲對 debug 分析沒有實質影響。商業產品可以降到 10 秒以獲得更接近即時的 error 告警。

### 數量觸發（buffer size）

Buffer 內的事件數量達到上限時立即 flush。Buffer size 設定為一次 HTTP POST 的合理 payload 大小對應的事件數量。

合理的數量範圍：50-200 筆。數量太少（10 筆）頻繁觸發 flush；數量太多（1000 筆）單次 HTTP POST 的 payload 過大，增加傳輸失敗的風險（超時、記憶體）。

數量觸發和時間觸發互為備援。高頻事件場景（使用者快速操作）靠數量觸發避免 buffer 溢出；低頻事件場景（使用者長時間閒置）靠時間觸發確保事件在合理時間內送出。

### 關閉觸發（flush on close）

SDK close 時強制 flush buffer 中所有剩餘事件。這是最後一道保障 — app 關閉後 buffer 中未送出的事件就永久遺失了。

close flush 的挑戰是時間限制。iOS app 進入背景後約 5 秒會被系統 suspend，Android 的限制更嚴格。Close flush 必須在這個時間窗口內完成網路請求。如果 buffer 中事件太多導致 flush 超時，需要截斷 — 送出最近的 N 筆，放棄較舊的。

## Buffer 管理

### 記憶體 buffer

Buffer 在記憶體中維護一個事件陣列。新事件 append 到尾端，flush 時取出整個陣列送出並清空。

記憶體 buffer 的上限應該設定為 buffer size 的 2-3 倍（允許 1-2 次 flush 失敗後累積的事件）。超過上限時丟棄最舊的事件（FIFO），保留最新的 — 最新的事件對 debug 和即時分析的價值更高。

### 離線 buffer

網路不可用時，事件累積在記憶體 buffer 中。如果離線時間超過記憶體 buffer 容量，需要離線 persistence — 見 [離線 buffer 與重試](/monitoring/03-sdk-design/offline-buffer/)。

## Flush 失敗處理

HTTP POST 失敗時（網路中斷、server 回 5xx、超時），事件保留在 buffer 中等待下一次 flush 重試。不立即重試 — 連續失敗通常代表網路問題或 server 問題，立即重試只會增加負載。

重試次數有上限（3 次）。超過重試上限的事件被丟棄，記錄一筆 `sdk.flush.dropped` metric 事件（這筆 metric 本身也進 buffer，在下次成功 flush 時送出）。

## Heartbeat 和 flush 的整合

DevOps dashboard 需要 `sdk.heartbeat` 事件判斷 SDK 是否存活。Heartbeat 不需要獨立的 timer — 整合在 flush timer 中：

flush timer 觸發時，如果 buffer 為空且距上次 heartbeat 超過設定間隔（預設 5 分鐘），自動注入一筆 `sdk.heartbeat` lifecycle 事件後送出。App idle 時仍有心跳但不多一個 timer；app 活躍時 heartbeat 被正常事件的 flush 取代（buffer 不會為空）。

Heartbeat 間隔由 SDK init config 的 `heartbeatInterval` 設定。設為 0 停用 heartbeat。

## 下一步路由

- 離線場景的處理 → [離線 buffer 與重試](/monitoring/03-sdk-design/offline-buffer/)
- SDK 公開 API → [SDK 公開 API 設計](/monitoring/03-sdk-design/public-api/)
- Collector 端如何接收批次事件 → [模組四 Collector 架構](/monitoring/04-collector/)
