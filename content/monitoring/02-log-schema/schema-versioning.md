---
title: "Schema 版本演進策略"
date: 2026-06-19
description: "Backward compatible 的增量變更 — 新增欄位不改版、改名或改型別才改版、collector 同時支援多版本"
weight: 3
tags: ["monitoring", "log-schema", "versioning", "backward-compatible"]
---

Schema 版本演進的目標是讓新版 SDK 和舊版 SDK 產生的事件能被同一個 collector 正確處理。核心策略是 backward compatible 的增量變更 — 儘量用「新增選填欄位」代替「修改現有欄位」。

## 不需要改版的變更

### 新增選填欄位

在 data 區域新增欄位。舊版 SDK 送來的事件不包含這個欄位，collector 和查詢工具用「欄位不存在則忽略」的邏輯處理。

例：v=1 的事件沒有 `data.duration_ms`，v=1 的 SDK 升級後開始送 `data.duration_ms`。Collector 不需要改 — 新欄位出現在 data 自由區域，不影響 schema 驗證。查詢時用 optional access。

### 新增事件名稱

新功能加入新的事件名稱（`enrollment.qr.scan`）。事件名稱不受 schema 版本控制 — schema 定義的是事件的結構，不是事件名稱的清單。

## 需要改版的變更

### 新增核心必填欄位

在核心區域（type、name、timestamp、source 同層）新增必填欄位。舊版 SDK 不會送這個欄位，collector 需要根據版本號決定是否要求這個欄位。

例：v=2 新增必填的 `environment` 欄位（production / staging / development）。v=1 的事件沒有這個欄位，collector 對 v=1 不要求 environment，對 v=2 要求 environment。

### 改變欄位型別

把 `duration` 從 string（`"320ms"`）改成 integer（`320`）。同一個欄位的兩種型別需要不同的解析邏輯，collector 用版本號區分。

### 刪除或重新命名欄位

刪除欄位或改名（`error_msg` → `error_message`）需要改版。Collector 對舊版本讀舊欄位名，對新版本讀新欄位名。

## Collector 的多版本支援

Collector 同時接收不同版本的事件。處理策略：

### 版本分派

收到事件後先讀 v 欄位，分派到對應版本的處理器。每個版本的處理器知道該版本的欄位結構和驗證規則。

### 正規化

不同版本的事件正規化成統一的內部格式後儲存。正規化層處理欄位名稱對應（`error_msg` → `error_message`）和型別轉換（string → integer）。查詢時只面對正規化後的格式。

### 版本淘汰

當所有 SDK 都升級到 v=2 後（從事件記錄中確認不再收到 v=1），可以移除 v=1 的處理器。淘汰前確認沒有離線 buffer 中的 v=1 事件尚未送達。

## 實務建議

**遲改版優於早改版**。每次改版增加 collector 的複雜度（多一個版本的處理器）。如果變更可以用「新增選填欄位」解決，優先選擇不改版。

**一次改版包含多個變更**。如果確定要改版，把多個計畫中的 breaking change 合併到同一次版本升級。v=1 → v=2 包含三個 breaking change，比 v=1 → v=2 → v=3 → v=4 各包含一個 breaking change 的維護成本低。

**Schema 文件和版本號同步**。每個版本的 schema 有對應的文件，記錄該版本和前一版本的差異。

## 下一步路由

- 完整欄位定義 → [event.schema.json 完整欄位解說](/monitoring/02-log-schema/event-schema-fields/)
- 欄位設計原則 → [欄位設計原則](/monitoring/02-log-schema/field-design-principles/)
- 和 OpenTelemetry 的比較 → [跟 OpenTelemetry 的 schema 差異對照](/monitoring/02-log-schema/otel-comparison/)
