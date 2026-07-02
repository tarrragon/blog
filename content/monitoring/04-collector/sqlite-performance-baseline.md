---
title: "SQLite Backend 效能基準"
date: 2026-06-20
description: "寫入吞吐 / 查詢延遲 / 資源消耗的量化預期 — 不同硬體環境下 SQLite 能撐多少、邊界在哪、怎麼實測"
weight: 12
tags: ["monitoring", "collector", "sqlite", "performance", "benchmark", "baseline"]
---

SQLite Backend 的效能受三個因素影響：儲存裝置（SSD vs HDD vs SD card）、Go driver 選擇（modernc.org/sqlite pure Go vs mattn/go-sqlite3 CGO）、並發模型（WAL mode + single-writer）。本章根據 SQLite 的技術特性和業界基準推導預期效能範圍，並提供實測方法讓使用者在自己的環境驗證。所有數字是預期範圍而非實測值 — 實際效能依硬體和 workload 而定。

## 寫入吞吐

寫入吞吐決定 collector 每秒能消化多少事件。SQLite 的寫入效能主要受 fsync 頻率和 WAL checkpoint 影響。

### 單筆 INSERT

每筆 INSERT 獨立一個 transaction 時，每次 commit 都會 fsync。WAL mode 的 fsync 成本比 journal mode 低（append-only），但仍是寫入的主要瓶頸。

| 儲存裝置 | 單筆 INSERT 延遲 | 理論上限                   |
| -------- | ---------------- | -------------------------- |
| NVMe SSD | 10-30 μs         | 30,000-100,000 inserts/sec |
| SATA SSD | 30-50 μs         | 20,000-30,000 inserts/sec  |
| HDD      | 50-200 μs        | 5,000-20,000 inserts/sec   |
| SD card  | 500-2000 μs      | 500-2,000 inserts/sec      |

modernc.org/sqlite（pure Go）的效能約為 CGO driver（mattn/go-sqlite3）的 60-80%。上表數字基於 CGO driver，pure Go 需打八折。Go HTTP handler 的開銷（JSON 解碼、schema 驗證、goroutine 調度）再扣 10-20%。

### 批次 INSERT

一個 transaction 包裹多筆 INSERT，只做一次 fsync。Collector 接收 SDK 的 flush batch（一個 HTTP request 帶一批事件）天然適合批次寫入。

吞吐提升幅度和批次大小的關係：

| 批次大小   | 相對單筆的吞吐提升 |
| ---------- | ------------------ |
| 10 筆/tx   | 3-5x               |
| 100 筆/tx  | 5-10x              |
| 1000 筆/tx | 8-15x              |

提升來自 fsync 次數從「每筆一次」降到「每批一次」。超過 100 筆/tx 後邊際收益遞減。

### 實際預期

結合 pure Go driver、HTTP handler 開銷和批次寫入，不同環境下的預期吞吐：

| 環境                     | 單筆       | 批次（100/tx） | 適合場景 |
| ------------------------ | ---------- | -------------- | -------- |
| Mac M1/M2 NVMe + pure Go | ~5,000/sec | ~30,000/sec    | 開發機   |
| Linux VPS SATA SSD       | ~3,000/sec | ~20,000/sec    | 小型部署 |
| Raspberry Pi 4 SD card   | ~200/sec   | ~1,000/sec     | 邊緣設備 |

**實測校準（monitor collector benchmark，Apple Silicon NVMe + modernc.org/sqlite）**：單筆 10,750 events/sec（p50 74µs）、批次 100/tx 93,671 events/sec（p50 9.2µs）——分別為推導預期的 2.1 倍與 3.1 倍。推導鏈的「pure Go 打八折 + handler 再扣 10-20%」疊加折扣偏保守，且未含 Apple Silicon NVMe 的低 fsync 成本；上表數字可視為安全下限。批次/單筆提升倍率實測 8.7x，落在推導的 5-10x 區間內。完整比對見 monitor repo `docs/challenges/005-benchmark-baseline-deviation.md`。

### 和事件產生速率的對照

| 場景                     | 預估 events/sec | SQLite 批次能撐嗎              |
| ------------------------ | --------------- | ------------------------------ |
| 自用 1 個 app            | < 10            | 遠超需求                       |
| 小團隊 5 人各跑 1 個 app | < 50            | 綽綽有餘                       |
| 10 SDK 同時 flush        | 100-1000 burst  | 批次 INSERT 撐得住             |
| 100+ 使用者持續活躍      | 500+ 持續       | 邊界 — 觀察 database is locked |

burst 和持續的差異在於：burst 是短暫的高峰（flush batch 到達後數秒內消化完），持續是長時間的穩定高流量。SQLite 的 WAL mode 對 burst 容忍度高（write lock 等待時間短），對持續高流量容忍度有限（write lock 等待累積）。

## 查詢延遲

查詢延遲決定 dashboard 的刷新體驗。SQLite 的查詢效能取決於索引覆蓋和掃描行數。

### 有索引的查詢

建議的索引（見 [規模演進](/monitoring/04-collector/scaling-evolution/) 的建議索引段）覆蓋 dashboard 的核心查詢模式。有索引時的預期延遲：

| 查詢模式                             | 10 萬筆  | 50 萬筆   | 100 萬筆  |
| ------------------------------------ | -------- | --------- | --------- |
| 等值查詢（WHERE session_id = ?）     | < 1ms    | < 1ms     | < 1ms     |
| 範圍查詢（WHERE ts BETWEEN ? AND ?） | < 10ms   | 10-50ms   | 50-100ms  |
| GROUP BY name                        | 10-50ms  | 50-200ms  | 200-500ms |
| COUNT DISTINCT session_id            | 50-100ms | 200-500ms | 500ms-1s  |
| JOIN + window function               | 100ms-1s | 1-3s      | 3-10s     |

### 無索引的查詢

無索引時 SQLite 做全表掃描。掃描速度約 50-100 MB/sec（SSD）、10-30 MB/sec（HDD）。

| 資料量   | 預估大小 | SSD 全掃延遲 | HDD 全掃延遲 |
| -------- | -------- | ------------ | ------------ |
| 10 萬筆  | ~40 MB   | 200-500ms    | 1-3s         |
| 100 萬筆 | ~400 MB  | 2-5s         | 10-30s       |
| 300 萬筆 | ~1.2 GB  | 5-15s        | 30-90s       |

預估大小與事件 payload 尺寸強相關：上表以較大 payload 估算；monitor collector benchmark 的 seed 資料（小 payload）實測 10 萬筆僅 18 MB。實務估算建議用「每筆 180B-400B 依 payload 而定」的區間，而非單一數字。

超過 100 萬筆無索引查詢會超出 dashboard 可接受的刷新延遲 — 這是 day-one 就建索引的理由。

### Dashboard 刷新頻率 vs 查詢延遲

Dashboard 的每個視圖有不同的刷新間隔和可接受延遲。查詢延遲超過可接受值時，dashboard 體驗變差（等待轉圈、資料過時）。

| Dashboard 視圖         | 刷新間隔 | 可接受延遲 | 10 萬筆有索引 | 100 萬筆有索引 |
| ---------------------- | -------- | ---------- | ------------- | -------------- |
| 即時狀態卡             | 1-5 秒   | < 100ms    | 滿足          | 滿足           |
| Error 列表             | 5-10 秒  | < 500ms    | 滿足          | 滿足           |
| 趨勢圖（最近 24h）     | 30 秒    | < 1s       | 滿足          | 邊界           |
| 長期聚合（最近 30 天） | 5 分鐘   | < 3s       | 滿足          | 需要預聚合     |

「需要預聚合」代表原始事件的聚合查詢超過可接受延遲，應該依賴分層保留策略中的 hourly_summary / daily_summary 表（見 [規模演進](/monitoring/04-collector/scaling-evolution/) 的分層保留段）。

## 資源消耗

### 記憶體

| 元件                   | 佔用           | 備註                          |
| ---------------------- | -------------- | ----------------------------- |
| Go HTTP server         | 20-50 MB       | 基礎開銷                      |
| SQLite page cache      | 2 MB（預設）   | `PRAGMA cache_size` 可調      |
| 寫入 buffer（channel） | 1-10 MB        | 取決於 channel 容量和事件大小 |
| 查詢結果暫存           | 和結果集成正比 | GROUP BY 10 萬筆 ~10 MB       |
| **Collector 整體**     | **50-100 MB**  | 自用場景                      |

Raspberry Pi（1 GB RAM）上建議把 page cache 調小（`PRAGMA cache_size = -512` = 512 KB），避免大結果集查詢（加 LIMIT），dashboard 刷新頻率降低。

### CPU

| 操作                 | CPU 使用        | 備註                    |
| -------------------- | --------------- | ----------------------- |
| INSERT（寫入）       | 可忽略          | I/O bound，CPU 不是瓶頸 |
| SELECT（查詢）       | 和掃描行數正比  | 有索引時可忽略          |
| Downsample（每小時） | 短暫 spike < 1s | 處理最近一小時的事件    |
| Purge（每天）        | 短暫 spike 1-3s | 分批 DELETE             |
| **整體**             | **< 5%**        | 自用場景                |

### 磁碟

| 日事件量          | 原始資料/天 | 原始資料/月 | 含索引/月  |
| ----------------- | ----------- | ----------- | ---------- |
| 1,000（極低）     | 0.3-0.5 MB  | 9-15 MB     | 11-18 MB   |
| 10,000（自用）    | 3-5 MB      | 90-150 MB   | 110-180 MB |
| 100,000（小團隊） | 30-50 MB    | 0.9-1.5 GB  | 1.1-1.8 GB |

WAL 檔案通常 < 10 MB（auto-checkpoint 在 WAL 達到 1000 pages 時觸發）。分層保留策略下，原始事件只保留 7 天，長期佔用由聚合摘要表決定（遠小於原始事件）。

## 邊緣設備場景

Raspberry Pi、低配 VPS（1 核 / 1 GB RAM）、甚至 NAS 上跑 collector 時的特殊考量：

**SD card 的隨機寫入**：SD card 的隨機寫入 IOPS 極低（100-500 IOPS），WAL mode 的 checkpoint（把 WAL 內容合併回主資料庫檔案）可能卡住 1-5 秒。期間新的寫入等待 checkpoint 完成。建議調高 `wal_autocheckpoint` 的閾值（如 5000 pages），讓 checkpoint 頻率降低但每次時間更長 — 在非活躍時段（凌晨）手動觸發 `PRAGMA wal_checkpoint(TRUNCATE)`。

**1 GB RAM**：cache_size 調小（512 KB）、避免 `SELECT *` 不帶 LIMIT、GROUP BY 的結果集用 HAVING 條件過濾減少暫存。Dashboard 的長期聚合直接查 hourly_summary 表而非原始事件。

**ARM CPU**：pure Go SQLite driver（modernc.org/sqlite）在 ARM 上的效能差距可能比 x86 更大（pure Go 的 C-to-Go 翻譯在 ARM 的指令最佳化較少）。實測確認。

**建議配置**：邊緣設備上 collector 的 dashboard 刷新頻率從預設值降低（即時狀態卡 5 秒 → 30 秒，趨勢圖 30 秒 → 5 分鐘），降採樣 job 頻率從每小時改為每 6 小時。

## 實測方法指引

教學的預期數字是推導值，實際效能取決於使用者的硬體和 workload。Collector 提供內建的 benchmark 命令讓使用者在自己的環境實測。

### 寫入 benchmark

```bash
# 單筆寫入：10000 筆，每筆獨立 transaction
./collector benchmark write --events=10000 --batch=1 --storage=sqlite

# 批次寫入：10000 筆，每 100 筆一個 transaction
./collector benchmark write --events=10000 --batch=100 --storage=sqlite
```

輸出：total duration、events/sec、p50/p95/p99 latency per event。

### 查詢 benchmark

```bash
# 先灌入測試資料
./collector benchmark seed --events=100000 --storage=sqlite

# 跑查詢 benchmark
./collector benchmark query --type=error --group-by=name --storage=sqlite
./collector benchmark query --session-id=random --storage=sqlite
```

輸出：query duration、rows scanned、rows returned。

### Production 觀察指標

部署後用 DevOps dashboard（見 [DevOps Dashboard 設計](/monitoring/04-collector/dashboard-devops/)）觀察 collector 自身的效能 metric：

- `collector.storage.write_duration_ms`：每次寫入的延遲。P95 超過 100ms 是瓶頸訊號。
- `collector.storage.query_duration_ms`：每次查詢的延遲。P95 超過 dashboard 刷新間隔是瓶頸訊號。
- `collector.storage.db_size_bytes`：資料庫大小。接近磁碟可用空間的 80% 時觸發 purge 或擴容。
- `collector.storage.wal_size_bytes`：WAL 檔案大小。持續 > 50 MB 代表 checkpoint 跟不上寫入速度。

## 下一步路由

- 切換到 PostgreSQL 的觸發條件 → [規模演進](/monitoring/04-collector/scaling-evolution/)
- SQLite 和 PostgreSQL 的功能分層 → [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)
- Ingestion 端的擴展設計 → [Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/)
