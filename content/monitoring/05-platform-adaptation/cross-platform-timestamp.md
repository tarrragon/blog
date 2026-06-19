---
title: "跨平台 timestamp 一致性"
date: 2026-06-19
description: "時區、精度、clock drift — 不同平台產生的 timestamp 在 collector 端需要能正確比對和排序"
weight: 5
tags: ["monitoring", "platform", "timestamp", "timezone", "clock-drift"]
---

跨平台的監控系統收到來自不同平台（JS / Flutter / Python / Go）的事件，每個平台的 timestamp 格式、精度和時鐘來源不同。Collector 需要對這些 timestamp 做排序、分組和時間範圍查詢，一致性問題會導致事件順序錯亂和分析結果偏差。

## 統一格式：ISO 8601 + 時區偏移

所有平台的 SDK 統一使用 ISO 8601 格式，包含毫秒精度和時區偏移：

```text
2026-06-19T14:30:00.123+08:00
```

避免使用 Unix timestamp（秒或毫秒）作為唯一的時間表示 — Unix timestamp 沒有時區資訊，如果 SDK 端和 collector 端在不同時區，需要額外的 metadata 才能正確轉換。

避免使用「本地時間不帶時區」的格式（`2026-06-19T14:30:00`）— 無法區分 UTC+8 的 14:30 和 UTC+0 的 14:30。

## 各平台的 timestamp 來源

### JavaScript

`Date.now()` 回傳毫秒精度的 Unix timestamp。`new Date().toISOString()` 回傳 UTC 時間的 ISO 8601 字串。

SDK 應該用 `Intl.DateTimeFormat` 或手動計算時區偏移，產生帶本地時區的 ISO 8601 字串 — collector 端需要知道事件的本地時間，以便做使用者時區的分析。

`performance.now()` 提供微秒精度的高解析度時間，但起點是頁面載入時間，無法用來產生絕對 timestamp。用於計算 duration（兩個時間點的差值），不用於記錄事件時間。

### Flutter / Dart

`DateTime.now()` 回傳本地時間的 DateTime 物件。`DateTime.now().toUtc()` 轉成 UTC。`DateTime.now().toIso8601String()` 產生 ISO 8601 字串，但不包含時區偏移（Dart 的 ISO 8601 格式不包含 offset）。

SDK 需要手動附加時區偏移：`DateTime.now().timeZoneOffset` 取得偏移量，手動格式化為 `+08:00` 格式附加到 ISO 8601 字串後面。

### Python

`datetime.now(timezone.utc)` 取得 UTC 時間。`datetime.now().astimezone()` 取得本地時間帶時區。`.isoformat()` 產生帶時區偏移的 ISO 8601 字串。

Python 3.2+ 的 `datetime` 原生支援 timezone-aware 的 ISO 8601 輸出，是各平台中最完整的。

### Go

`time.Now()` 回傳帶時區的 Time 值。`time.Now().Format(time.RFC3339Milli)` 產生帶毫秒和時區偏移的字串。

Go 的 `time.RFC3339Nano` 提供奈秒精度，但監控事件不需要這個精度 — 毫秒足夠。

## Clock drift

不同裝置的系統時鐘可能有偏差（clock drift）。使用者手機的時鐘比 collector server 快 5 分鐘，SDK 產生的 timestamp 會比 collector 收到時間早 5 分鐘。

Clock drift 的影響：

- **排序錯亂**：裝置 A（時鐘快）和裝置 B（時鐘慢）的事件混合排序時，時間順序可能和真實發生順序不一致
- **告警延遲計算錯誤**：collector 用「事件 timestamp 到收到時間的差值」計算延遲，clock drift 讓延遲值不準確

處理策略：

**Collector 記錄 receive_timestamp**：每筆事件除了 SDK 端的 timestamp，collector 在收到時附加 `receive_timestamp`。兩者的差值用於估算 clock drift 和網路延遲。

**容忍而非修正**：在數秒到數分鐘級的 drift 範圍內，容忍 drift 帶來的排序不精確。跨裝置的事件排序本身就不需要毫秒精度 — 分析的粒度通常是秒或分鐘。

**異常值偵測**：timestamp 比 receive_timestamp 早超過 1 小時，或晚超過 5 分鐘，標記為可疑的 clock drift — 可能是使用者手動調整了系統時鐘。

## 下一步路由

- JS 平台適配 → [JS/TS 平台適配](/monitoring/05-platform-adaptation/js-ts-platform/)
- Flutter 平台適配 → [Flutter 平台適配](/monitoring/05-platform-adaptation/flutter-platform/)
- Log schema 中的 timestamp 欄位 → [模組二 event.schema.json 欄位解說](/monitoring/02-log-schema/event-schema-fields/)
