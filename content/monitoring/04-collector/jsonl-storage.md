---
title: "JSONL 匯出與備份格式"
date: 2026-06-19
description: "JSONL 作為匯出和備份格式的設計 — 人類可讀、grep 友好、SQLite 損壞時的重建來源"
weight: 2
tags: ["monitoring", "collector", "storage", "jsonl", "export", "backup"]
---

Collector 的 day-one 主要儲存是 SQLite（見 [規模演進](/monitoring/04-collector/scaling-evolution/)）。JSONL（JSON Lines）保留作為匯出和備份格式 — 人類可讀、grep 友好、SQLite 資料庫損壞時可以從 JSONL 重建。Collector 提供 `monitor export --format=jsonl` 指令匯出事件，也可以設定同步寫入 JSONL 作為即時備份。

JSONL 的格式是每行一個 JSON 物件。作為匯出格式，核心優勢是工具鏈成熟 — `grep` 過濾、`jq` 結構化查詢、`tail -f` 即時監控，不需要 database client。

## 一天一檔

事件按日期分檔：`events-2026-06-19.jsonl`、`events-2026-06-20.jsonl`。每天零點（或 UTC 日期變更時）切換到新檔案。

一天一檔的好處：

**時間範圍查詢直接對應到檔案**。查「昨天的 error」只需要讀一個檔案，不需要掃描整個資料集。

**保留策略按檔案操作**。保留 30 天的資料 = 刪除 30 天前的檔案。不需要 database 的 TTL 機制或 partition pruning。

**備份和搬移按檔案操作**。rsync 一個目錄就完成備份；搬移特定日期的資料 = 搬移對應檔案。

一天一檔的風險是單日資料量過大時，單一檔案的 grep 查詢會變慢。自用工具場景下，單日事件量通常在數千到數萬筆，檔案大小在 MB 級，grep 查詢在秒級完成。當單日事件量超過百萬筆時，需要考慮演進到更適合的儲存方案（見 [規模演進](/monitoring/04-collector/scaling-evolution/)）。

## Append-only 寫入

JSONL 的寫入模式是 append-only — 新事件追加到檔案尾端，已寫入的事件不修改。

Append-only 的操作特性：

**寫入不需要鎖**。`os.OpenFile` 用 `O_APPEND` flag 開啟，OS 保證每次 write 是 atomic 的（在 write size 不超過 `PIPE_BUF` 的前提下，Linux 上是 4096 bytes）。單一事件的 JSON 通常在這個限制內。

**不會損壞既有資料**。寫入失敗（磁碟滿、程序崩潰）最多造成最後一行不完整，不影響前面的行。恢復時刪除最後一行的不完整片段即可。

**支援 tail -f 即時監控**。`tail -f events-2026-06-19.jsonl | jq .` 即時顯示新寫入的事件，不需要額外的 streaming 機制。

## Gzip 壓縮

歷史檔案（非當天的）用 gzip 壓縮。JSON 文字的壓縮率通常在 80-90%（10MB 壓縮到 1-2MB）。

壓縮策略：

**當天的檔案不壓縮**。保持 append-only 和 tail -f 的能力。

**日期切換時壓縮前一天的檔案**。用 cron job 或 collector 啟動時檢查，把 `events-2026-06-18.jsonl` 壓縮為 `events-2026-06-18.jsonl.gz`。

**查詢壓縮檔用 zgrep / zcat**。`zgrep "error" events-2026-06-18.jsonl.gz` 不需要先解壓。

## JSONL 備份的保留

JSONL 備份檔的保留策略和 SQLite 主要儲存的分層保留獨立 — JSONL 是最後的重建來源，保留期限可以比 SQLite 中的原始事件更長。

典型配置：JSONL 備份保留 30 天（即使 SQLite 中的原始事件只保留 7 天），提供 SQLite 損壞時的 30 天重建窗口。超過 30 天的 JSONL 壓縮檔用 cron job 清理：

```bash
find /var/lib/collector/events/ -name "events-*.jsonl.gz" -mtime +30 -delete
```

主要儲存的查詢驅動分層保留策略見 [規模演進](/monitoring/04-collector/scaling-evolution/)。

## 下一步路由

- Collector 的完整架構 → [Collector 架構](/monitoring/04-collector/architecture/)
- 查詢設計 → [查詢 API 設計](/monitoring/04-collector/query-api/)
- 儲存撐不住時的演進 → [規模演進](/monitoring/04-collector/scaling-evolution/)
