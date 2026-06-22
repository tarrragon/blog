---
title: "4.23 觀測查詢設計"
date: 2026-06-22
description: "把觀測資料的讀取路徑當系統設計問題處理：三種查詢模式、storage tiering、pre-aggregation 與資源治理"
weight: 23
tags: ["backend", "observability"]
---

## 大綱

- 觀測資料的讀寫不對稱：一種寫入路徑對應多種讀取路徑
- 三種查詢模式：即席診斷、聚合趨勢、鑑識回溯
- [Storage tiering](/backend/knowledge-cards/storage-tiering/) 與查詢路由：hot / warm / cold 不只是成本分層、是查詢能力分層
- Pre-aggregation 策略：[recording rule](/backend/knowledge-cards/recording-rule/)、[materialized view](/backend/knowledge-cards/materialized-view/)、[rollup](/backend/knowledge-cards/rollup/) 的使用情境與維護成本
- Query 資源治理：priority、queue 分離、timeout 差異化、cost estimation
- 觀測領域的讀寫分離：[CQRS](/backend/knowledge-cards/cqrs/) 的特化應用
- 反模式：把 raw log 當 OLAP 查、dashboard 查詢直打 raw storage 無 pre-aggregation、recording rule 跟 raw query 重複計算

## 概念定位

觀測查詢設計是把「產生訊號之後怎麼被讀取」當成獨立的系統設計問題。觀測資料的寫入路徑（agent → collector → ingest → storage）在 [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/) 處理；本章處理的是讀取路徑 — 從 storage 經 query engine 到 dashboard、alert 與即席查詢的資料流。

寫入路徑的設計目標是吞吐穩定、schema 一致、成本可控；讀取路徑的設計目標是在不同的時間壓力下，用對的精度取回對的切面。兩者的效能瓶頸不同、擴展方向不同、治理責任也不同。把讀取當寫入的附屬處理，會在流量成長後遇到「寫入正常但查詢崩潰」的局面。

## 觀測資料的讀寫不對稱

觀測資料有一個 application data 不常見的特性：同一份資料被多種完全不同的查詢形狀讀取，每種查詢的時間壓力、精度需求、結果形狀差距可以到三個數量級。

寫入面相對單純。不管是 log、metric 還是 trace，寫入都是 append-only、schema 由產生端定義、吞吐由流量決定。寫入路徑的設計問題集中在 cardinality 控制（[4.7](/backend/04-observability/cardinality-cost-governance/)）、pipeline 可靠性（[4.11](/backend/04-observability/telemetry-pipeline/)）與 sampling 策略。

讀取面則至少有三種模式，各自有獨立的 SLA、索引需求與資源消耗模型。把三種模式混在同一個未分化的 query engine 裡，會在任何一種模式的負載增長時拖累其他模式。

## 三種查詢模式

### 即席診斷

事故中的查詢，責任是在秒級內定位問題。

查詢形狀是精確 filter + 短時間範圍：拿一個 [request id](/backend/knowledge-cards/request-id/) 查關聯事件、拿一個 error code 加 time window 撈錯誤樣本、拿一個 [trace id](/backend/knowledge-cards/trace-id/) 展開完整 span tree。

對儲存的要求：需要 hot tier 的完整索引、完整精度、毫秒到秒級回應。即席查詢幾乎不命中 warm 或 cold tier — 事故通常發生在「現在」或「剛才」。

資源特性：低頻（事故時才有）、單次掃描量小、但延遲要求最嚴格。事故中的每一秒等待都在消耗 MTTR。

### 聚合趨勢

Dashboard 跟 alert rule 的查詢，責任是提供持續的服務健康視圖。

查詢形狀是 group by + aggregation + 中等時間範圍：過去 5 分鐘的 error rate by service、過去 1 小時的 latency p99 by endpoint、過去 24 小時的 log volume by level。Dashboard 每 30 秒到 1 分鐘刷新，alert rule 每 1 到 5 分鐘 evaluate。

對儲存的要求：可以讀 [recording rule](/backend/knowledge-cards/recording-rule/) 或 [rollup](/backend/knowledge-cards/rollup/) 的預聚合資料，不需要完整精度。延遲容忍比即席查詢寬（秒級到十秒級），但查詢頻率比即席查詢高兩到三個數量級。

資源特性：高頻、穩定、佔 query engine 的常態負載大頭。一個 Grafana dashboard 有 20 個 panel、每 30 秒刷新一次 = 每分鐘 40 個查詢；十個團隊各自有 dashboard = 每分鐘 400 個背景查詢。

### 鑑識回溯

事後分析、合規稽核與根因調查的查詢，責任是在大時間範圍內還原完整脈絡。

查詢形狀是寬時間範圍 + 條件掃描：過去 30 天某 tenant 的所有 authentication failure、過去 90 天某 API 的 error 分布演變、某次事故前後 48 小時的完整 log 流。

對儲存的要求：會命中 warm 甚至 cold tier。完整性比延遲重要 — 漏掉一筆 audit log 比多等 30 秒更嚴重。可能需要 rehydrate（把 cold tier 歸檔資料暫時載回可查詢狀態）。

資源特性：低頻但單次掃描量極大。一個 cold tier 的全量掃描可能佔用 query engine 數分鐘的計算資源。

### 三種模式的設計衝突

三種模式搶同一個 query engine 時，聚合趨勢的穩定高頻負載會佔滿常態資源、擠壓即席診斷的突發需求；鑑識回溯的大範圍掃描會吃掉臨時資源、拖慢同時進行的即席查詢。

事故中是衝突最嚴重的時刻：incident commander 在做即席診斷、dashboard 在高頻刷新聚合趨勢、事後調查團隊可能同時在做鑑識回溯。三種負載同時打在同一個 query engine 上，誰先退讓取決於 query 資源治理的設計。

## Storage tiering 與查詢路由

[Storage tiering](/backend/knowledge-cards/storage-tiering/) 在讀取路徑上的責任不只是降低儲存成本，而是為不同時間範圍的查詢提供對應的查詢能力。每一層的儲存介質、索引密度、資料精度共同決定該層能回答什麼問題。

### 每一層的查詢能力

| 層級 | 查詢延遲   | 可用索引                                 | 資料精度          | 適合的查詢模式 |
| ---- | ---------- | ---------------------------------------- | ----------------- | -------------- |
| Hot  | 毫秒到秒   | 完整結構化索引 + 全文索引                | 原始精度          | 即席診斷       |
| Warm | 秒到十秒   | 結構化索引（可能移除低價值欄位索引）     | 原始或輕度 rollup | 聚合趨勢       |
| Cold | 十秒到分鐘 | 最小索引（timestamp + service + tenant） | rollup 或歸檔     | 鑑識回溯       |

查詢跨越 tier 邊界時，回應時間由最慢的 tier 決定。Dashboard 時間範圍從「最近 1 小時」（全部 hot）拉到「最近 30 天」（hot + warm + cold），查詢延遲可能從毫秒跳到分鐘。這個延遲跳變需要在 dashboard UI 上提示使用者。

### 查詢路由的設計

查詢路由的責任是根據查詢的時間範圍跟精度需求，自動選擇最合適的 tier 跟資料精度。

- 時間範圍在 hot tier 內：直接查 raw data，完整精度。
- 時間範圍跨越 hot 跟 warm：hot 部分查 raw data、warm 部分查 rollup series，query engine 負責拼接。
- 時間範圍延伸到 cold tier：cold 部分需要 rehydrate 或走 object storage 查詢路徑，延遲大幅增加。

查詢路由的透明度影響使用者信任。使用者需要知道目前看到的資料是什麼精度、來自哪一層、是否有 freshness lag。Grafana 的 annotation 機制可以在 dashboard 上標示 tier 邊界跟精度切換點，避免使用者把精度變化誤讀成服務異常。

### Rehydrate 的操作成本

Cold tier 的資料通常儲存在 object storage（S3、GCS、Azure Blob），查詢前需要 rehydrate — 把資料從歸檔格式解壓、重建索引、載入到可查詢狀態。這個操作有時間成本（分鐘到小時）、儲存成本（臨時佔用 hot/warm 空間）跟計算成本（CPU 用在解壓跟索引重建）。

Rehydrate 是事故事後分析跟合規稽核的常見操作。設計 tiering 時要把 rehydrate 的 SLA（多久可以完成）、容量（同時可以 rehydrate 多少資料）跟觸發方式（手動 / API / 自動 policy）納入規劃。

## Pre-aggregation 策略

Pre-aggregation 是把讀取時的計算成本轉移到寫入時的策略。觀測領域有三種常見的 pre-aggregation 機制，適用場景跟維護成本不同。

### Recording rule

[Recording rule](/backend/knowledge-cards/recording-rule/) 在 TSDB 層定期執行 query expression，把聚合結果寫成新 series。適合 metrics 的高頻聚合查詢（SLO burn rate、error ratio、跨服務 latency summary）。

Recording rule 的維護成本集中在規則增長後的管理。數百條 recording rule 需要命名慣例、版本控制、執行時間監控（rule evaluation duration）與定期審計（是否有 rule 不再被 dashboard 或 alert 引用）。

### Log-to-metric 轉換

在 collector 端把高頻 log pattern 轉成 metric。適合「從 log 衍生的聚合查詢」— 例如把 `level=error` 的 log 計數轉成 error_log_total counter，把 specific exception 的出現率轉成 gauge。

Log-to-metric 的好處是讓 dashboard 讀 metric 而非重掃 log volume。維護成本在於 collector 配置要跟 log schema 保持同步 — log 的 field name 改了，轉換規則沒跟著改，metric 會靜默歸零。

### Rollup / downsampling

[Rollup](/backend/knowledge-cards/rollup/) 把高精度時間序列聚合成低精度版本。適合長時間範圍的趨勢查詢（90 天 error rate 趨勢、capacity planning 的年度成長曲線）。

Rollup 的設計關鍵是聚合函數必須按 metric type 選擇。Counter 用 sum、gauge 用 average（或 min/max 保留極端值）、histogram 需要保留 bucket boundary 而非做 average（否則 percentile 計算會失真）。混用聚合函數是 rollup 最常見的 silent data corruption。

### Pre-aggregation 的維護成本

Pre-aggregation 不是免費的。每一條 recording rule、每一個 log-to-metric 轉換、每一層 rollup 都需要：

- **儲存空間**：預聚合結果本身佔用 series 或 index 空間，增加 [cardinality](/backend/knowledge-cards/metric-cardinality/) 負擔。
- **計算資源**：定期執行聚合需要 CPU，rule evaluation lag 會讓 dashboard 看到過期資料。
- **配置維護**：規則需要跟 schema、label、service 保持同步，漂移會靜默產生錯誤資料。
- **除錯成本**：dashboard 讀的是 recording rule 輸出，事故時可能需要同時查 raw data 驗證 recording rule 是否正確。

設計時的判準是：預聚合的讀取節省是否大於維護成本。高頻讀取（dashboard auto-refresh、alert evaluation）的聚合計算值得 pre-aggregation；低頻讀取（月度報表、偶發 ad-hoc query）直接查 raw data 更簡單。

## Query 資源治理

觀測平台的 query engine 是共用資源，需要顯式的治理機制避免單一查詢類型或單一使用者耗盡資源。

### Query priority 與排程

Query engine 需要知道每個查詢的優先級，在資源不足時讓高優先查詢先執行。

| 查詢類型       | 建議優先級 | 理由                                            |
| -------------- | ---------- | ----------------------------------------------- |
| Alert evaluate | 最高       | 告警延遲直接影響 MTTD，不可因其他查詢排隊而漏發 |
| 即席診斷       | 高         | 事故中的查詢，每秒延遲消耗 MTTR                 |
| Dashboard 刷新 | 中         | 穩定背景負載，短暫延遲不影響決策品質            |
| 鑑識回溯       | 低         | 延遲容忍高，可排程到低負載時段執行              |
| Ad-hoc 探索    | 最低       | 非事故的探索性查詢，可被其他類型搶佔            |

### Query timeout 差異化

不同查詢類型設不同的 timeout：alert evaluation 設短 timeout（30 秒到 1 分鐘，跑不完說明 query 有問題）、即席診斷設中等 timeout（1 到 5 分鐘）、鑑識回溯允許較長 timeout（10 到 30 分鐘）。統一 timeout 會讓鑑識查詢被過早截斷、或讓 alert evaluation 等太久。

### Query cost estimation

在查詢執行前估算掃描量（掃描的 series 數、time range、shard 數），超過閾值的查詢被拒絕或降級。避免單一 heavy query（例：跨所有 service 的 90 天 full-resolution 聚合）拖垮 query engine。

Query cost estimation 對使用者的回饋要足夠清楚。拒絕查詢時要說明「這個查詢預計掃描 N 條 series × M 天，超過單次查詢上限；請縮小時間範圍或增加 filter 條件」，而不是只回 timeout 或 500 error。

### Query cache

聚合趨勢查詢的特徵是高頻重複 — 同一個 dashboard panel 每 30 秒查一次，查詢的時間範圍大部分重疊。Query cache 在 query-frontend 層快取最近的聯合結果，下一次刷新只需要增量計算新進的資料區間。

Thanos Query Frontend、Mimir Query Frontend、Grafana Cloud 的 query splitting + caching 都實作這個模式。Cache 的命中率直接影響 query engine 負載 — 高命中率讓 query engine 的常態負載下降、留更多資源給即席查詢。

## 觀測領域的讀寫分離：CQRS 的特化應用

觀測查詢設計的底層問題是讀寫不對稱 — 寫入跟讀取的形狀、頻率、SLA 都不同，單一模型無法同時服務。這個問題在 application data 層有成熟的設計框架：[CQRS](/backend/knowledge-cards/cqrs/)。觀測領域面對的是同一類不對稱，但不對稱的程度更極端，實作層級也不同。

### 觀測場景的不對稱比 application 更極端

[CQRS 知識卡](/backend/knowledge-cards/cqrs/)描述了讀寫不對稱的三個維度（形狀、頻率、SLA）。觀測場景在這三個維度上都比典型 application 更極端：

**形狀不對稱**：application 的 [read model](/backend/knowledge-cards/read-model/) 通常是一到兩種（列表頁、報表）。觀測的讀取面至少三種：即席診斷要精確 filter + 完整精度、聚合趨勢要 group by + pre-aggregated、鑑識回溯要寬範圍 + 完整性優先。三種形狀對索引、精度、儲存層的需求互斥。

**頻率不對稱**：application 的讀寫比通常在 10:1 到 100:1 之間。觀測的 dashboard 每 30 秒刷新一次、alert 每分鐘 evaluate、十個團隊各自有 dashboard — 讀取頻率可以到寫入的千倍以上，而且是持續穩定的背景負載而非突發。

**SLA 不對稱**：application CQRS 的讀寫 SLA 差距通常在同一個數量級（毫秒 vs 數百毫秒）。觀測的三種讀取模式 SLA 跨三個數量級 — 即席診斷要求毫秒到秒級、聚合趨勢容忍秒到十秒級、鑑識回溯容忍分鐘級。

### 觀測領域怎麼實作讀寫分離

CQRS 在 application 層透過 event handler、projector、read store 實作。觀測領域用自己的 first-class 機制做同樣的事：

| CQRS 概念      | 觀測領域的對應                                                                                                             | 設計責任                    |
| -------------- | -------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| Write model    | Raw series / log / span — append-only 寫入                                                                                 | Schema 穩定、吞吐           |
| Read model     | [Recording rule](/backend/knowledge-cards/recording-rule/)、[rollup](/backend/knowledge-cards/rollup/)、log-to-metric 轉換 | 讀取最佳化                  |
| Projection     | Collector 端的 aggregation / enrichment / routing                                                                          | 寫入到讀取模型的轉換        |
| Event 同步延遲 | Recording rule evaluation lag、rollup delay、buffer freshness lag                                                          | 最終一致性的延遲窗口        |
| 多 read store  | [Storage tiering](/backend/knowledge-cards/storage-tiering/)（hot / warm / cold 各自支援不同查詢模式）                     | 不同 SLA 的讀取走不同儲存層 |

### CQRS 的代價在觀測領域同樣存在

[CQRS 知識卡](/backend/knowledge-cards/cqrs/)列出的三項代價（最終一致性、同步可靠性、多模型維護）在觀測場景都找得到對應：

**最終一致性**：Recording rule 每 N 秒 evaluate 一次，dashboard 看到的聚合結果落後 raw data。Rollup 的延遲更長。事故中 incident commander 看 dashboard 做決策時，需要知道資料的 freshness — 這就是 CQRS 的 read model 延遲在觀測領域的具體表現。

**同步可靠性**：Recording rule evaluation 本身可能失敗（expression 太重跑不完、TSDB 暫時不可用）。Log-to-metric 轉換可能因 schema 漂移而靜默歸零。這些同步失敗跟 application CQRS 的 projector 失敗是同一類問題 — read model 看起來有資料但其實是過期的。

**多模型維護**：Metric schema 變更後，raw series、recording rule、rollup、dashboard query 都需要同步更新。Recording rule 引用的 label name 改了沒跟著改，aggregation 結果會靜默錯誤。這跟 application 的「schema migration 要同時更新 write model 跟所有 read model」是同一個維護負擔。

### 術語邊界

觀測領域的讀寫分離跟 CQRS 概念對應，但在業界溝通中直接說「log 的 CQRS」或「metrics 的 CQRS」會造成混淆。觀測領域有自己的 first-class 術語（recording rule、rollup、tiering、query routing），跟 application CQRS 的術語（command、query、projection、read model）平行但不互通。

理解 CQRS 的讀者可以把觀測查詢設計視為「infrastructure-level 的讀寫分離」，同樣的設計原則（分離的動機、最終一致性的代價、多模型維護的負擔）在不同層級重複出現。但設計決策時要用觀測領域的術語，把 recording rule 跟 rollup 當第一等公民，而非 CQRS 的衍生品。

## 核心判讀

判讀觀測查詢設計時，先看三種查詢模式是否有對應的資源與資料形狀，再看 pre-aggregation 跟 tiering 是否對齊實際查詢負載。

重點訊號包括：

- 即席查詢在事故中的延遲是否在秒級以內
- Dashboard 刷新是否佔用過多 query engine 資源
- 長時間範圍查詢是否有 rollup / recording rule 支撐
- Storage tiering 的查詢路由是否對使用者透明
- Alert evaluation 是否有最高 query priority
- Pre-aggregation 規則是否跟 schema 保持同步

## 判讀訊號

- Dashboard 載入時間持續退化、panel timeout 增加
- Alert rule evaluation duration 成長、偶發 missed evaluation
- 事故中即席查詢被 dashboard 背景負載擠壓
- 長時間範圍的查詢精度突變但使用者不知道
- Recording rule 輸出跟 raw query 結果不一致
- Rehydrate 需求頻繁但沒有預設流程
- Query engine CPU 被少數 heavy query 佔滿

## 反模式

| 反模式                           | 表面現象                                | 修正方向                                             |
| -------------------------------- | --------------------------------------- | ---------------------------------------------------- |
| Raw log 當 OLAP 查               | 聚合查詢掃 TB 級 log、timeout           | 用 log-to-metric 轉換把常用聚合推到 metric 層        |
| Dashboard 直打 raw storage       | Panel 載入慢、query engine 過載         | 用 recording rule / rollup 支撐高頻 panel            |
| Recording rule 跟 raw query 重複 | 同一個指標有兩條查詢路徑、數值不一致    | 統一入口：dashboard 讀 recording rule、ad-hoc 讀 raw |
| 所有查詢同一個 priority          | Alert 被 dashboard 查詢排隊延遲         | Query priority 分級、alert evaluation 最高           |
| Tier 邊界對使用者不透明          | 拉長時間範圍時數值突變但不知為何        | Dashboard 標示 tier 邊界跟精度切換                   |
| Rollup 聚合函數混用              | Histogram percentile 在長時間視圖被壓平 | 按 metric type 指定聚合函數、histogram 保留 bucket   |
| 所有訊號同一個 tier 邊界         | 高價值訊號過早退化、低價值訊號佔 hot    | 依訊號優先級設差異化 tier 邊界                       |

## 交接路由

- [4.1 log schema](/backend/04-observability/log-schema/)：log 的即席 / 聚合 / 鑑識三種查詢模式細節
- [4.2 metrics](/backend/04-observability/metrics-basics/)：metrics 的 recording rule 與 rollup 設計
- [4.7 cardinality / cost](/backend/04-observability/cardinality-cost-governance/)：storage tiering 對查詢能力的影響
- [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/)：讀取路徑作為 pipeline 的延伸
- [4.15 cost attribution](/backend/04-observability/cost-attribution/)：query 資源的成本歸屬
- [4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/)：pre-aggregation 與 raw data 的一致性驗證
- [4.18 operating model](/backend/04-observability/observability-operating-model/)：query 資源治理的 ownership
- [Monitoring 讀寫分離](/monitoring/04-collector/read-write-separation/)：Monitor 專案的讀寫分離具體應用
