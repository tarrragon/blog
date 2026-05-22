---
title: "MySQL Cross-buffer Memory Contention"
date: 2026-05-22
description: "MySQL InnoDB buffer pool、sort / join buffer、tmp table、thread memory、OS page cache 與 memory pressure 判讀"
tags: ["backend", "database", "mysql", "memory", "performance"]
---

MySQL cross-buffer memory contention 的核心責任是把 MySQL memory tuning 從單一 buffer pool 參數擴展到整體記憶體競爭。InnoDB buffer pool、redo log buffer、sort buffer、join buffer、tmp table、thread stack、connection memory、OS page cache 與 container limit 會共同決定 latency 與 OOM 風險。

本文的判讀錨點是：MySQL memory 問題常來自[「每連線 / 每操作」記憶體](/backend/knowledge-cards/per-connection-memory/)乘上 concurrency，而非只來自全域 buffer pool。調大單一 buffer 前，要先看 workload 與同時執行的 query。

## Memory Surfaces

Memory surfaces 的核心責任是列出會互相競爭的記憶體來源。

| Surface             | 類型                    | 風險                                |
| ------------------- | ----------------------- | ----------------------------------- |
| InnoDB buffer pool  | global                  | 太小造成 read I/O，太大壓縮 OS 空間 |
| Redo log buffer     | global                  | 大交易 / burst write 需要審查       |
| Sort buffer         | per session / operation | concurrent sort 放大 memory         |
| Join buffer         | per session / join      | missing index 時放大                |
| Temp table          | memory / disk           | group / sort / derived table        |
| Connection overhead | per connection          | connection storm / thread memory    |
| OS page cache       | system                  | file、backup、binlog、tmp           |

Per-session buffer 是最容易誤調的項目。把 sort / join buffer 全域調大，會在高 concurrency 下造成 memory spike。

## Contention Signals

Contention signals 的核心責任是把 memory pressure 從 symptom 轉成可排查訊號。

| Signal                       | 意義                                |
| ---------------------------- | ----------------------------------- |
| OOM / container restart      | total memory 超出限制               |
| swap activity                | memory pressure 已影響 latency      |
| Created_tmp_disk_tables 增加 | memory temp table 不足或 query 太大 |
| Sort_merge_passes 增加       | sort memory / query shape 問題      |
| Buffer pool hit rate 下降    | working set / query pattern 問題    |
| Threads_connected 高         | per-connection memory 放大          |

Signal 要和 query workload 對照。Temp table 與 sort 問題通常需要 query rewrite、index 或報表隔離，而非只調 memory。

## Tuning Order

Tuning order 的核心責任是建立安全調整順序。

1. 先確認 host / container memory limit。
2. 設定 InnoDB buffer pool baseline。
3. 控制 max connections 與 application pool。
4. 用 top query 找 sort / join / temp table 來源。
5. 對特定 session / workload 調 buffer，而非全域放大。
6. 將 analytics / reporting 移到 replica 或 OLAP。

這個順序讓全域 memory 先穩定，再處理 query 層問題。若反過來先調大 per-session buffer，壓力會在尖峰流量時爆發。

## Query Patterns

Query patterns 的核心責任是找出 memory heavy 查詢。

| Pattern            | Memory 風險              | 修正方向                            |
| ------------------ | ------------------------ | ----------------------------------- |
| Large sort         | sort buffer / temp table | index order、limit、pagination      |
| Missing join index | join buffer 放大         | 補 index、改 join order             |
| Big GROUP BY       | tmp table / disk spill   | pre-aggregate、OLAP、covering index |
| Large transaction  | undo / lock / memory     | batch、縮短 transaction             |
| Many idle sessions | connection memory        | pooler、timeout、max connection     |

Memory tuning 要服務 query design。若 query 本身無界，memory 只會把問題延後到更大資料量。

## Runbook

Runbook 的核心責任是把 memory incident 分流。

| Step               | 操作                                     |
| ------------------ | ---------------------------------------- |
| Confirm pressure   | OS memory、swap、OOM、MySQL status       |
| Identify workload  | processlist、performance schema、top SQL |
| Reduce concurrency | 限流、停報表、降 background job          |
| Protect OLTP       | kill heavy query、切 read replica        |
| Tune safely        | session-level buffer、index、query       |
| Retrospective      | pool size、query guard、dashboard        |

OOM 後要保存 evidence：memory limit、MySQL variables、Threads_connected、top queries、tmp table counters、container restart time。

## 下一步路由

Cross-buffer memory contention 完成後，InnoDB 基礎讀 [InnoDB Tuning](../innodb-tuning/)；query 層讀 [Query Optimization](../query-optimization/)；lock 與 transaction 壓力讀 [Lock Contention](../lock-contention/)。
