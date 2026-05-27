---
title: "1.14 Production Slow Log Closed Loop"
date: 2026-05-27
description: "把 production slow log 從『偶爾看一下』變成『定期審視 + PR review 整合 + regression 偵測』的閉環、補 1.13 反模式清單後的操作層"
weight: 14
tags: ["backend", "database", "slow-log", "observability", "ops-loop"]
---

[1.13 應用層查詢反模式](/backend/01-database/query-anti-patterns/) 列出了 query 反模式清單跟每請求預算、但沒覆蓋一件事：**production slow log 怎麼從「事故時才看」變成「定期審視能 catch 反模式」**。本章把 slow log 包成 closed loop — 採集、分析、PR review 整合、regression 偵測四個動作串起來、讓反模式在進 production 之前就被攔下。

## Slow log 的兩種讀法

多數團隊把 slow log 當「事故診斷工具」— 服務變慢時去翻一下、找出當下的罪魁禍首。這條讀法在事故時有效、但有 systemic 缺陷：所有 catch 到的反模式都已經影響使用者一段時間。

另一條讀法是把 slow log 當「定期審視訊號」— 每週 / 每 release cycle 抓 slow log top-N、看哪些 query 模式持續存在、哪些是新出現的。這條讀法的關鍵在於「對比基線」、不是「找絕對閾值」。

兩種讀法的對比決定了 closed loop 的設計方向：

| 維度     | 事故診斷工具                    | 定期審視訊號                             |
| -------- | ------------------------------- | ---------------------------------------- |
| 觸發時機 | 服務變慢時被動翻                | 排程定期掃                               |
| 比較對象 | 跟絕對閾值比（query &gt; 1 秒） | 跟上週 / 上次 release 的 slow log 分布比 |
| 處理路徑 | 找出 root cause → 立即修        | 收進 PR backlog → 排序 → 規律修          |
| 介入點   | 事故發生後                      | 反模式被引入後、影響使用者前             |
| 對應角色 | On-call / SRE                   | 整個團隊（每週輪流 review）              |

定期審視這條讀法是本章的核心、後續四個動作都環繞它建立。

## Loop 第一步：採集

Slow log 採集的設計關鍵是「採集標準要穩定、retention 要夠長」。常見的採集配置選擇：

- **Threshold 設定**：MySQL `long_query_time`、PostgreSQL `log_min_duration_statement` 設多久才記？常見 default 1 秒太寬鬆、會漏掉「200ms-1s」這層慢但累積成大量壓力的 query。建議 100ms 或更低（依 application 需求）。
- **採集對象**：純 SELECT 慢？還是含 INSERT/UPDATE/DELETE？寫路徑慢通常代表 lock contention 或 transaction 範圍問題、跟讀路徑反模式不同、要分開分析。
- **Retention**：log 保留多久？至少 30 天（覆蓋一個 sprint）、有資源的話 90 天（覆蓋季度 regression 對比）。雲端 managed DB（RDS / Aurora）的 slow log 通常自動匯出到 CloudWatch / S3、設定 retention policy 而不是依賴 DB instance 本身的 log。
- **Sample rate**：高流量服務全採會把 disk I/O 拖垮。Production 環境用 sampling（如 10% 取樣）平衡採集完整度跟系統壓力。

採集出來的 raw log 不適合直接讀、要先 normalize。

## Loop 第二步：Normalize 與聚合

Raw slow log 每筆都帶具體參數（`WHERE user_id = 12345`、`WHERE user_id = 67890`），直接看會看到上千筆「不同 query」。實際上多數是同一個 query template 的不同參數實例。

Normalize 動作把參數抽掉、留 query shape：

- `WHERE user_id = 12345` → `WHERE user_id = ?`
- `IN (1, 2, 3, 4, 5)` → `IN (?)`
- 字串常數同樣抽掉

工具上：MySQL 用 `pt-query-digest`（Percona Toolkit）；PostgreSQL 用 `pg_stat_statements` extension（已內建 normalize）；雲端用 vendor 工具（AWS Performance Insights、GCP Query Insights、Azure SQL Insights）。Normalize 後可以按 query shape 聚合、看哪些 shape 累計時間最長、出現次數最多、平均延遲最高。

聚合後產出三條訊號：

1. **Top-N by total time**：累計時間最長的 query — 改一條就能省最多 DB 壓力
2. **Top-N by count**：出現次數最多的 query — 改一條就能降最多 connection 占用
3. **Top-N by avg latency**：平均延遲最高的 query — 個別 request 體驗最差的

三條訊號可能指向不同 query、各自值得 attention。

## Loop 第三步：PR review 整合

把 slow log 的 top-N 帶回 PR review 是 closed loop 的關鍵。常見三種整合機制：

- **每週 slow log review 會議**：固定時段（每週 30 分鐘）、團隊輪流 owner、把 top-10 過一輪、決定每筆是修 / 留 / 標 acceptable。產出進 backlog、不是當場修。
- **PR-level query budget check**：CI 加 middleware 統計每個 endpoint 的 query 數（per [1.13 query 預算](/backend/01-database/query-anti-patterns/#每請求的-query-預算)）、超過閾值的 PR 在 review 時觸發討論。這層比 slow log 早、catch 的是「新引入」反模式。
- **Production regression alert**：當某個 query shape 的 P99 latency 比上週 baseline 偏高 50%+、自動發 alert 給該服務 owner。這層 catch 的是「漸進惡化」反模式（如資料量增加、index 失效）。

三層機制按介入點分層：PR check 是「進 production 前」、weekly review 是「進 production 後的固定盤點」、regression alert 是「漸進惡化的訊號偵測」。三層覆蓋率最高、單跑任一層都會漏。

## Loop 第四步：Regression 偵測

Slow log 的對比基線需要主動維護。沒有基線、定期審視會退化成「每次都看到同樣的 top-10、習以為常」。建立基線的常見做法：

- **每 release 凍結 baseline**：上線新版本前抓一份 slow log snapshot、release 後跟它比。新增的 query shape 跟惡化的 query shape 都會浮出來。
- **資料量分位點 marker**：在 schema 加註「這張表預期 1M / 10M / 100M 行的 query 計畫」、實際成長到對應規模時驗證 plan 是否還對。Index 失效常常是「資料量過某個門檻、optimizer 改用 full scan」造成的。
- **跨 release 趨勢圖**：把 slow log top-10 的累計時間做時序圖、看一年的趨勢。穩定升高代表反模式 / 資料成長壓力、突然升高代表新引入問題。

Regression 偵測的 false-positive 風險是「業務本身在變、流量本身在長」、不是反模式造成的。用「query shape 佔比」而非「絕對延遲」當訊號可以降低 false positive — 某個 query shape 從佔 5% 變成佔 30%，不論絕對延遲是否升高、都值得審視。

## 判讀訊號

| 訊號                                            | 判讀重點                                      | 對應動作                                                      |
| ----------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------- |
| Slow log top-10 一直是同一批 query              | Closed loop 沒形成、review 退化成擺設         | 啟動 PR-level query budget check 或 weekly review             |
| 某個 query shape 突然從 top-100 升到 top-10     | 新版本引入反模式 / 流量結構變化               | 對照最近 release diff、找出引入時點                           |
| Top-N 累計時間穩定升高、但 query shape 沒變     | 資料量增加、index 退化或 query 計畫漂移       | EXPLAIN 對比、檢查是否該加 covering index 或 partition        |
| Slow log 異常稀少（< 預期）                     | Threshold 設太寬、或採集 sample rate 太低     | 降 threshold、提高 sample rate                                |
| 同一個 endpoint 在 PR check 過、production 卻爆 | PR 環境資料量太小、CI 無法 catch 大資料量退化 | 加 production-like load test、或在 CI 用 anonymized prod data |

## 常見誤區

把 slow log 當「事故工具」、不做定期審視。事故時的 slow log 是 lagging indicator — 反模式已經影響使用者一段時間才被看見。定期審視是把它變成 leading indicator 的關鍵。

把 threshold 設太鬆（1 秒、5 秒）。多數反模式落在 100ms-1s 區間、設 1 秒會漏掉。Threshold 應該對齊「user-perceived 慢」門檻、通常 100-500ms。

把 top-10 當「不能動」。一些 top-10 是業務本質慢（複雜 report、bulk write）、改起來代價遠超效益。Review 時要明示標記「acceptable」、避免下週又被當未解決問題討論。

## 定位邊界

本章專注「production slow log 怎麼變成 closed loop」。當問題進入具體反模式分析（這條 query 是哪種反模式？怎麼改？）、回到 [1.13 應用層查詢反模式](/backend/01-database/query-anti-patterns/)；進入 EXPLAIN 解讀細節、回到 [1.2 schema design](/backend/01-database/schema-design/)；進入 application-side query 數量控制機制（ORM middleware、query log 觀察），跨到 [04 observability](/backend/04-observability/) 模組。

## 案例回寫

09 案例庫中、slow log closed loop 直接示範的案例稀少（多數案例談規模 / vendor、不談 ops loop 設計）。可用以下案例反向追問：

- [9.C39 DoorDash：Aurora Postgres 寫入瓶頸](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/) — 寫入飽和被識別為 vendor 層問題、但若 production slow log loop 早期就 catch 到 transaction 範圍跟熱 row 競爭、可能延後遷移時點。對照本章可問：DoorDash 在啟動遷移前、是否有定期 slow log review 機制？
- [9.C14 Standard Chartered：合規驅動容量規劃](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 容量規劃以合規為驅動、但 query 預算假設若無 production 驗證、規劃出的 TPS 上限會偏低。對照本章「Regression 偵測」段：合規 cluster 是否有 query shape 趨勢圖？

反向追問框架（per [#146](/report/case-misalignment-reverse-inquiry/)）：案例本身不直接示範 closed loop、但用「啟動 vendor 升級前、closed loop 能不能延後撞牆」這條追問、能看出 slow log loop 的事前價值。

## 跨模組路由

1. 與 [1.13 query 反模式](/backend/01-database/query-anti-patterns/) 的交接：1.13 給反模式清單、本章給「定期 catch 它們」的機制。
2. 與 [04 observability](/backend/04-observability/) 的交接：slow log 採集跟聚合是 observability 的子問題、跨服務的 query trace 需要 04 的 telemetry pipeline。
3. 與 [9.5 瓶頸定位](/backend/09-performance-capacity/bottleneck-localization/) 的交接：9.5 用 USE / RED method 定位、本章用 slow log 在 DB 層做更精細的 query-level 定位。
4. 與 [06 reliability ci-pipeline](/backend/06-reliability/ci-pipeline/) 的交接：PR-level query budget check 是 CI 環節、屬 06 模組的 release gate 設計。

## 下一步路由

要看具體反模式怎麼修、回 [1.13 應用層查詢反模式](/backend/01-database/query-anti-patterns/)。要把 query 觀測接進完整 telemetry pipeline、進 [04 observability](/backend/04-observability/)。要看 PR-level check 怎麼接 release gate、進 [6.8 release gate](/backend/06-reliability/release-gate/)。
