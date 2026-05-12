---
title: "9.C4 DraftKings：Aurora 撐 100 萬 ops/min 的體育博彩金融帳本"
date: 2026-05-12
description: "DraftKings 用 Aurora MySQL 跑體育博彩金融帳本、Super Bowl 流量 +50% 不影響延遲"
weight: 4
tags: ["backend", "performance", "capacity", "case-study", "db-oltp", "aws", "event-peak"]
---

這個案例的核心責任是說明「transactional 金融系統」如何在不可預期峰值下維持低延遲。跟 [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) 對比 — GR8 Tech 走「微服務 + AI 預測擴容」、DraftKings 走「Aurora 單一資料庫服務支撐多 DB cluster」、兩條路徑都解決同類業務問題。

## 觀察

DraftKings 帳本系統的關鍵數字（引自 [DraftKings case study](https://aws.amazon.com/solutions/case-studies/draftkings-aurora-case-study/)）：

| 指標            | 數字                                      |
| --------------- | ----------------------------------------- |
| 客戶數          | 310 萬 unique customers / month (Q2 2024) |
| 峰值操作        | 100 萬 ops / 分鐘                         |
| 讀延遲          | < 1 ms                                    |
| 寫延遲          | 6 ms                                      |
| Replication lag | 從 30 秒降到 10-30 ms                     |
| Database 數量   | 200 個 individual databases               |
| Super Bowl 流量 | 比賽季開幕高 +50%                         |

服務組合：Amazon Aurora MySQL-Compatible、Aurora Replicas（讀寫分流）、Aurora I/O-Optimized（2023-05 推出）、Aurora Database Cloning（測試環境）、跨三個 AZ 儲存複製。

關鍵負載形狀：「write workloads spike up significantly around payout events, but opening the app during the game also activates a lot of balance queries」— 比賽進行時是讀爆量、payout event 時是寫爆量、雙峰錯位。

## 判讀

DraftKings 的工程選擇揭露三個 OLTP 容量設計重點。

1. **200 個獨立資料庫 = sharding 預先做好**：不是一個巨型 cluster 撐全部、而是按業務切 200 個 cluster。對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 把「單機極限」改成「shard 極限」、每個 shard 的容量規劃變成獨立問題。
2. **Replication lag 30 秒 → 10-30 ms**：這個改善不只是「快」、而是讓 read-after-write 變得可預測。Aurora 的 storage layer 多 AZ 複製是這個 lag 改善的主因。對應 [01 資料庫模組](/backend/01-database/) 的 replication lag 影響 transaction boundary 設計。
3. **Super Bowl +50% 「no sweat」**：這句話的工程意義是 *提前做好容量規劃*、不是「Aurora 神奇」。寫 workload 預期可能 + 50%、整個 system headroom 預留至少 50%、加上 read replica 動態加減、才能讓 50% 增幅變成「不流汗」。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/) 的 headroom budget 與 event-driven scheduled scaling。

需要警惕：100 萬 ops / 分鐘 = ~17K ops / 秒、跨 200 個 databases 平均下來每個 DB 約 80 ops / 秒。這不是「單一 DB 撐 100 萬 ops」、而是「200 shard 加總 100 萬」。讀案例時要看「峰值是分散到多少 shard」、不只看總數。

## 策略

可重用的工程做法：

1. **按業務切 OLTP cluster、不要一個 DB 撐全部**：DraftKings 200 個 databases 顯示「業務切片」是 OLTP 擴容的前置。對應 [01 資料庫模組](/backend/01-database/) 的 schema design 與 partition 決策。
2. **讀寫分流是 OLTP 容量規劃的基線**：6ms 寫 vs <1ms 讀的差距、加上 read replica、是 OLTP 擴容最基本的兩個槓桿。
3. **事件型峰值預測寫進 baseline**：Super Bowl 是已知事件、+50% 是歷史經驗、所以可以提前 pre-scale。事件未知（突發新聞、KOL 推廣）的情況才需要 AI 預測（對照 [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)）。

跨平台等效：GCP Cloud SQL + read replica / Spanner、Azure Database for PostgreSQL + read replica、自建 PostgreSQL + Patroni + pgbouncer 都可以實作對等架構。Aurora 的差異是 storage layer 對 replica 的 lag 改善。

## 下一步路由

- 想規劃 OLTP 高峰容量 → [9.6 容量規劃模型](/backend/09-performance-capacity/) + [9.11 高峰事件準備](/backend/09-performance-capacity/) + [01 資料庫模組](/backend/01-database/)
- 想搞清楚事件型 vs 突發型峰值 → [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) 對照
- 想做 read replica 容量設計 → [01.6 高併發資料存取](/backend/01-database/high-concurrency-access/) + [9.5 瓶頸定位流程](/backend/09-performance-capacity/)
- 想理解 replication lag 對 transaction boundary 的影響 → [01.5 transaction boundary](/backend/01-database/transaction-boundary/)

## 引用源

- [DraftKings Scales Its Financial Ledger with Amazon Aurora](https://aws.amazon.com/solutions/case-studies/draftkings-aurora-case-study/)
- [Aurora I/O-Optimized announcement](https://aws.amazon.com/blogs/database/amazon-aurora-i-o-optimized-database-storage-configuration/)
