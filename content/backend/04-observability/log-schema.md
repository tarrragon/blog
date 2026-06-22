---
title: "4.1 log schema 與搜尋規劃"
date: 2026-04-23
description: "整理 log 欄位、索引與搜尋策略"
weight: 1
tags: ["backend", "observability"]
---

## 大綱

- structured [log schema](/backend/knowledge-cards/log-schema/)
- [correlation id](/backend/knowledge-cards/correlation-id/) / [request id](/backend/knowledge-cards/request-id/) fields
- index 與 [retention](/backend/knowledge-cards/retention/)
- query pattern

## 概念定位

[log schema](/backend/knowledge-cards/log-schema/) 是把事件紀錄從文字輸出變成可查詢資料的契約，責任是讓不同服務在事故時能用同一組欄位還原脈絡。

這一頁處理的是欄位與搜尋路徑。log 的價值不在於寫得多，而在於事故時能用穩定欄位找到同一個 request、同一個 tenant、同一個 dependency call 與同一段錯誤鏈。

## 核心判讀

判讀 log schema 時，先看 correlation fields 是否穩定，再看 [search index](/backend/knowledge-cards/search-index/) 與 [retention](/backend/knowledge-cards/retention/) 是否對齊查詢需求。

重點訊號包括：

- [request id](/backend/knowledge-cards/request-id/)、[trace id](/backend/knowledge-cards/trace-id/)、[tenant boundary](/backend/knowledge-cards/tenant-boundary/) 與 service name 是否跨服務一致
- high-cardinality 欄位是否被放進可控索引，並受查詢價值與成本預算約束
- [retention](/backend/knowledge-cards/retention/) 是否依 operational debug、[audit](/backend/04-observability/audit-log-governance/)、compliance 分層
- query pattern 是否能支援 [incident timeline](/backend/knowledge-cards/incident-timeline/) 還原

## 判讀訊號

- log 欄位 schema 漂移、跨服務 correlation id 對不上
- 事故時靠 grep 拼湊事件、無結構化查詢入口
- log 索引爆量、查詢退化但無清理流程
- log 含大量 free-form text、無一致關鍵欄位
- retention 策略全平、舊事件查不到 / 不該留的還在留

## 查詢模式設計

Log 的寫入格式跟讀取需求是兩個不同的設計問題。寫入追求 schema 穩定與吞吐效率；讀取要在不同時間壓力下，用不同的查詢形狀取回不同精度的資料。同一份 structured log 至少被三種查詢模式讀取，每種模式對索引、延遲與結果形狀的要求不同。

### 即席診斷查詢

事故中的查詢要在秒級內定位問題。典型操作是拿到一個 [request id](/backend/knowledge-cards/request-id/) 或 error code，加上 time window，撈出相關事件鏈。

即席查詢的索引策略是把高頻過濾欄位放進結構化索引：service name、log level、error code、[request id](/backend/knowledge-cards/request-id/)、[trace id](/backend/knowledge-cards/trace-id/)、[tenant boundary](/backend/knowledge-cards/tenant-boundary/)。這些欄位的共同特徵是有界或半有界（error code 有限、request id 雖然無界但查詢時一定帶精確值），查詢時用等值匹配或短範圍掃描。

即席查詢的反模式是對 free-text 欄位做全文搜尋當作主要診斷入口。全文搜尋適合探索性調查（「最近有沒有出現某個未預期的 exception message」），但事故中的時間壓力下，結構化欄位的精確查詢比全文搜尋快一到兩個數量級。

### 聚合趨勢查詢

Dashboard 跟告警的查詢是定期的聚合計算：過去 5 分鐘的 error count by service、過去 1 小時的 log volume by level、某個 tenant 的 warning 趨勢。這類查詢不需要看單筆 log 的內容，而是需要 count / rate / group by 的聚合結果。

聚合查詢的負載特性跟即席查詢不同。即席查詢讀少量資料、要求低延遲；聚合查詢掃大量資料、容忍較高延遲但執行頻率高（dashboard 每 30 秒刷新一次 = 每分鐘 2 次相同的重聚合）。當 log volume 成長，重複計算聚合的成本會推高 query engine 負擔。

應對策略有兩種。一是在 log pipeline 把常用聚合轉成 [metrics](/backend/knowledge-cards/metrics/) — collector 端做 log-to-metric 轉換（例：把 `level=error` 的 log 計數轉成 error_log_total counter），dashboard 讀 metric 而非重掃 log。二是在查詢層設定 [materialized view](/backend/knowledge-cards/materialized-view/) 或快取，讓重複查詢直接取用預計算結果。

### 鑑識回溯查詢

事後分析與合規稽核的查詢範圍大（跨天、跨週甚至跨月）、對完整性要求高、但延遲容忍也高（分鐘級回應可接受）。鑑識查詢常見的形狀是「某個 tenant 在過去 30 天內所有 authentication failure」或「某個 API 的 error 分布演變」。

鑑識查詢的儲存設計跟 [storage tiering](/backend/knowledge-cards/storage-tiering/) 直接相關。Hot tier 保留最近數天的 full-index log，warm tier 保留數週的部分索引或壓縮 log，cold tier 保留數月到數年的歸檔 log。鑑識查詢命中 cold tier 時，系統可能需要 rehydrate（把歸檔資料暫時載回可查詢狀態），這個操作本身需要時間和臨時儲存空間。

鑑識場景的關鍵設計決策是「哪些欄位在 cold tier 仍可查詢」。全部欄位都保留索引成本太高；只保留 timestamp + service name + tenant 的最小索引，能支援基本的範圍掃描，細節再用 rehydrate 後的全文搜尋補。

### 三種模式的資源隔離

三種查詢模式搶同一個 query engine 時，聚合查詢的持續負載會擠壓即席查詢的回應速度。事故中團隊最需要即席查詢的低延遲，但此時 dashboard 也在高頻刷新聚合查詢，兩者競爭 query 資源。

可操作的隔離方式是讓即席查詢跟聚合查詢走不同的 query priority 或 query queue。Elasticsearch 的 search thread pool、Loki 的 query-frontend queue、Datadog 的 query quota 都提供某種程度的查詢隔離。設計時要把即席查詢的延遲 SLA 當作硬性約束，聚合查詢的延遲可以被彈性排程。

## 交接路由

- 04.7 [metric cardinality](/backend/knowledge-cards/metric-cardinality/) / cost：label 預算與保留階梯
- 04.8 訊號治理閉環：log-based alert 的生命週期
- 04.12 [audit log](/backend/knowledge-cards/audit-log/)：稽核訊號跟 operational log 的邊界
- 04.23 [觀測查詢設計](/backend/04-observability/observability-query-design/)：跨訊號類型的讀取路徑系統設計
