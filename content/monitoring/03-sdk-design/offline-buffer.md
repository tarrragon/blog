---
title: "離線 buffer 與重試"
date: 2026-06-19
description: "網路不可用時的事件保存策略 — FIFO 丟棄、本地 persistence、恢復後補發的取捨"
weight: 4
tags: ["monitoring", "sdk", "offline", "buffer", "retry", "persistence"]
---

離線 buffer 處理的是「事件產生時網路不可用」的場景。記憶體 buffer 有容量上限，離線時間超過 buffer 容量時需要決策：丟棄舊事件、持久化到本地儲存、或兩者混合。每種策略有不同的複雜度和資料保留量的取捨。

## 三種策略

### FIFO 丟棄（最簡單）

Buffer 滿時丟棄最舊的事件，保留最新的。整個 buffer 在記憶體中，不做本地 persistence。

優點：實作最簡單（array + 容量檢查），不需要檔案系統存取，不增加磁碟 I/O。

代價：離線超過 buffer 容量時，較舊的事件永久遺失。如果離線 30 分鐘、buffer 容量 200 筆、事件產生速率每分鐘 10 筆，前 100 筆（前 10 分鐘）的事件被丟棄。

適合場景：自用工具（離線場景少、遺失部分事件影響低）、SDK 初期版本（先用最簡單的策略上線）。

### 本地 persistence（最完整）

Buffer 滿時把事件寫入本地檔案（SQLite、JSONL 檔案、SharedPreferences / UserDefaults）。網路恢復後從本地檔案讀取並補發。

優點：離線期間的事件不會遺失（在本地儲存容量內）。

代價：實作複雜度高 — 需要處理檔案讀寫、並發存取（多執行緒安全）、本地儲存容量管理（磁碟空間上限）、補發時的去重（同一筆事件可能已在記憶體 buffer 中被 flush 過）。

適合場景：商業產品（使用者在地鐵、電梯、飛航模式下使用）、離線時間長且事件不可遺失的需求。

### 混合策略

記憶體 buffer 處理正常情況和短暫離線。離線超過記憶體 buffer 容量時，溢出的事件寫入本地檔案。網路恢復後先 flush 記憶體 buffer（最新事件），再補發本地檔案中的事件（較舊事件）。

混合策略的實作複雜度介於兩者之間。本地檔案只在溢出時使用，正常情況下不產生磁碟 I/O。

## 恢復後補發

網路恢復後補發離線期間累積的事件，需要處理三個問題：

### 補發順序

離線事件按 timestamp 順序補發，保持事件的時間順序。Collector 端收到的事件 timestamp 可能比當前時間早數小時 — 這是正常的離線補發，collector 應該根據事件的 timestamp 處理，不依賴收到時間。

### 補發速率

一次送出大量離線事件可能讓 collector 過載。分批補發（每批 50-100 筆，間隔 1-2 秒），讓 collector 有時間處理。

### 去重

同一筆事件可能同時存在於記憶體 buffer 和本地檔案中（寫入本地檔案時 buffer 中也有一份）。Collector 端用事件的唯一識別（timestamp + session_id + name 的組合，或 SDK 產生的 event_id UUID）做去重。

## 本地儲存容量管理

本地 persistence 需要設定磁碟使用上限。上限取決於事件大小和保留時間。

以平均每筆事件 500 bytes 估算：

| 上限  | 可儲存事件數 | 備註                      |
| ----- | ------------ | ------------------------- |
| 1 MB  | ~2,000       | 約 3 小時（每分鐘 10 筆） |
| 10 MB | ~20,000      | 約 33 小時                |
| 50 MB | ~100,000     | 約 7 天                   |

自用工具 1 MB 足夠（離線場景少）。行動 app 10-50 MB 合理（使用者可能整天離線）。超過上限時用 FIFO 丟棄最舊的本地檔案。

## 下一步路由

- 攢批送出策略 → [攢批送出策略](/monitoring/03-sdk-design/batch-flush/)
- SDK 端的資料脫敏 → [SDK redaction helper](/monitoring/03-sdk-design/redaction-helper/)
- Collector 端如何處理補發事件 → [模組四 Collector 設計](/monitoring/04-collector/)
