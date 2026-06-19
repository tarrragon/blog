---
title: "JSONL 儲存設計"
date: 2026-06-19
description: "一天一檔、append-only、gzip 壓縮、保留策略 — JSONL 作為監控資料儲存格式的設計取捨"
weight: 2
tags: ["monitoring", "collector", "storage", "jsonl", "compression"]
---

JSONL（JSON Lines）是每行一個 JSON 物件的文字格式。作為監控資料的儲存格式，JSONL 的核心優勢是簡單 — 寫入是 append 一行文字，讀取是逐行 parse，查詢用 grep。不需要 database server、不需要 schema migration、不需要連線管理。

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

## 保留策略

保留策略決定資料保留多久。自用工具場景下，保留天數的判斷依據是「最遠需要回溯多久的資料」。

**Debug 用途**：保留 7-14 天。問題通常在發生後幾天內被發現和調查。

**趨勢分析用途**：保留 30-90 天。觀察月度趨勢需要至少兩個月的資料。

**合規用途**：依法規要求。某些法規要求 access log 保留一年以上。

保留策略的執行是 cron job 刪除超過保留天數的檔案：

```bash
find /var/lib/collector/events/ -name "events-*.jsonl.gz" -mtime +30 -delete
```

## 下一步路由

- Collector 的完整架構 → [Collector 架構](/monitoring/04-collector/architecture/)
- 查詢設計 → [查詢 API 設計](/monitoring/04-collector/query-api/)
- 儲存撐不住時的演進 → [規模演進](/monitoring/04-collector/scaling-evolution/)
