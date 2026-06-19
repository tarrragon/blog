---
title: "規模演進"
date: 2026-06-19
description: "grep → SQLite → 時間序列 DB 的三階段演進路徑 — 每個階段的觸發條件、遷移成本和能力增量"
weight: 5
tags: ["monitoring", "collector", "scaling", "sqlite", "timeseries", "evolution"]
---

Collector 的儲存和查詢方案應該隨資料規模演進，每個階段用最簡單的方案滿足當前需求。過早引入複雜方案增加維護成本但不增加實際價值；過晚演進讓查詢變慢、開發者失去對監控資料的信任。演進的判斷依據是可觀察的效能指標，不是預測的成長曲線。

## 第一階段：JSONL + grep

JSONL 檔案 + grep/jq 查詢。Collector 的起始方案。

### 能力範圍

- 寫入：append-only，每秒數千筆
- 查詢：grep 全文搜尋 + jq 結構化過濾
- 聚合：`jq + sort + uniq -c` 手動組合
- 儲存：一天一檔，gzip 壓縮歷史檔

### 適用規模

單日事件量在萬筆以下、JSONL 單檔在 10MB 以下。grep 查詢在秒級完成。自用工具和小型團隊的開發期通常在這個範圍。

### 觸發演進的訊號

**查詢變慢**：grep 查詢單日檔案超過 5 秒。使用者開始避免查詢或只查最近幾小時的資料。

**聚合查詢太痛苦**：「過去 7 天每天的 error 數量」需要寫多行 shell 組合跨檔 jq，而這類查詢頻率從偶爾變成每天。

**跨欄位過濾需求增加**：grep 的字串匹配處理 `AND` 條件（`grep A | grep B`）尚可，但 `OR` 和 `NOT` 條件讓 grep pipeline 變得難以維護。

## 第二階段：SQLite

把 JSONL 匯入 SQLite 資料庫，用 SQL 查詢。Collector 可以同時寫 JSONL（原始記錄）和 SQLite（查詢索引）。

### 能力增量

- **索引查詢**：按 type、name、timestamp 建索引，查詢從全表掃描變成索引查找
- **SQL 聚合**：`SELECT name, COUNT(*) FROM events WHERE type='error' GROUP BY name` — 一行 SQL 替代多行 shell
- **跨欄位過濾**：`WHERE type='error' AND name LIKE 'terminal.%' AND ts > '2026-06-18'`
- **JOIN**：事件和 metadata 的關聯查詢

### 遷移成本

SQLite 是嵌入式資料庫，不需要額外的 server 程序。Go 用 `mattn/go-sqlite3` 或 `modernc.org/sqlite`（pure Go，無 CGO 依賴）。

遷移步驟：

1. 定義 events 表結構（id、type、name、ts、data JSON 欄位）
2. Collector 寫入時同時寫 JSONL 和 INSERT 到 SQLite
3. 查詢 API 從讀 JSONL 改為執行 SQL
4. 歷史 JSONL 用匯入腳本灌入 SQLite

JSONL 保留作為原始記錄和備份 — SQLite 資料庫損壞時可以從 JSONL 重建。

### 適用規模

單日事件量在十萬筆以下、SQLite 資料庫在 1GB 以下。索引查詢在毫秒級完成。

### 觸發演進的訊號

**寫入爭搶**：SQLite 是單寫者模型。高併發寫入（每秒數百筆以上持續發生）會出現 `database is locked` 錯誤。WAL mode 能緩解但不能根治。

**時間序列查詢效能不足**：「過去 30 天每小時的 error P95 回應時間」這類時間序列聚合在 SQLite 中需要全表掃描加排序，資料量大時變慢。

**資料量超過單機磁碟**：SQLite 資料庫超過 10GB 時，備份和恢復時間變長，查詢效能下降明顯。

## 第三階段：時間序列 DB

引入專門為時間序列資料設計的資料庫（InfluxDB、TimescaleDB、VictoriaMetrics）。

### 能力增量

- **時間序列原生操作**：downsampling、retention policy、continuous query 內建
- **高併發寫入**：設計上支援每秒數萬筆以上的 append 寫入
- **高效聚合**：時間分桶（per-minute、per-hour）的聚合在引擎層面優化
- **長期儲存**：壓縮和 tiered storage 讓 TB 級資料可查詢

### 遷移成本

時間序列 DB 是獨立的 server 程序，需要部署、設定、監控。從「一個 binary」變成「兩個 server」（collector + DB），運維複雜度顯著上升。

遷移需要考慮：

- DB server 的部署和維護
- 資料 schema 重新設計（時間序列 DB 的 measurement / tag / field 模型和 JSONL / SQL 不同）
- 查詢語言切換（InfluxQL / Flux / PromQL）
- 備份和恢復策略

### 判斷是否需要

多數自用工具和小型團隊不需要到第三階段。時間序列 DB 的核心價值是高併發寫入和長期時間序列分析 — 如果寫入量在 SQLite 的承受範圍內、且不需要自動 downsampling，留在第二階段成本更低。

## 演進原則

**按觀察到的瓶頸演進**。grep 查詢超過 5 秒是可觀察的訊號；「未來可能有百萬筆事件」是預測。按訊號行動，不按預測行動。

**保留原始 JSONL**。每一階段都保留 JSONL 作為原始記錄。SQLite 損壞時從 JSONL 重建；遷移到時間序列 DB 時從 JSONL 重新匯入。JSONL 是 source of truth。

**遷移是漸進的**。第一階段到第二階段可以並行運作（同時寫 JSONL 和 SQLite），確認 SQLite 查詢正常後再關閉 JSONL 的查詢入口。

## 下一步路由

- Collector 的起始架構 → [Collector 架構](/monitoring/04-collector/architecture/)
- JSONL 儲存的設計取捨 → [JSONL 儲存設計](/monitoring/04-collector/jsonl-storage/)
- 資料庫選型的通用指南 → [backend 01 資料庫](/backend/01-database/)
