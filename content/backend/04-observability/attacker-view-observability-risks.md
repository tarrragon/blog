---
title: "4.5 可觀測性威脅建模（Threat Modeling）"
date: 2026-06-22
description: "從觀測盲區、告警失真與資料暴露風險，盤點 observability 的主要弱點"
weight: 5
tags: ["backend", "observability"]
---

## 大綱

- 觀測系統為什麼需要威脅建模
- 三類弱點：觀測盲區、告警失真、資料暴露
- 每類弱點的判讀流程與修復方向
- 跟 [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/) 跟 [07 資安](/backend/07-security-data-protection/) 的分工

## 概念定位

可觀測性威脅建模的判讀目標是「觀測系統本身有哪些弱點會讓事故更難處理、更慢收斂、或擴大成資安事件」。觀測系統是事故處理的核心工具 — 工具失靈時，事故的 MTTD（偵測時間）跟 MTTR（修復時間）都會被拉長。

本章用三類弱點盤點觀測系統：觀測盲區（看不到問題）、告警失真（看到錯的東西）、資料暴露（觀測資料本身變成風險）。每類弱點有各自的判讀流程跟修復方向。

跟傳統資安威脅建模的差異：資安威脅建模聚焦「攻擊者怎麼入侵系統」；觀測威脅建模聚焦「觀測系統的設計缺陷怎麼讓事故更難處理」。兩者的交叉點在資料暴露 — 觀測資料含 secret 或 PII 時，觀測弱點直接成為資安弱點。

## 哪些服務要先做觀測弱點盤點

下列情境同時出現時，觀測弱點會快速放大：

- 服務數量增加，跨服務呼叫變深 — [trace](/backend/knowledge-cards/trace/) 斷鏈的影響面擴大
- 值班依賴告警，但告警常常失真或過量 — [alert fatigue](/backend/knowledge-cards/alert-fatigue/) 讓真正的問題被淹沒
- 調查事故高度依賴人工搜尋 log — 缺少結構化查詢入口
- 支援工具與觀測平台可接觸敏感資料 — 觀測資料的存取控制不足

## 弱點一：觀測盲區

觀測盲區是「問題存在但觀測系統看不到」的狀態。盲區的危險在於它讓團隊對系統狀態的判斷建立在不完整的資訊上 — 看起來一切正常，但其實有路徑沒被觀測到。

### 常見盲區

**Sampling 導致的盲區**：head sampling 按固定比例丟棄 trace，低流量服務的錯誤樣本可能全部被丟。事故時查 trace 查不到，因為 sampling 把剛好那些 request 的 trace 丟了。修復方向是 tail sampling 或 minimum sample floor（見 [4.7 sampling 策略](/backend/04-observability/cardinality-cost-governance/#sampling-策略)）。

**Uninstrumented 路徑**：新上線的服務沒加 instrumentation、async worker 沒有 [span](/backend/knowledge-cards/span/)、third-party SDK 的 HTTP call 沒被攔截。這些路徑在 [service graph](/backend/04-observability/service-topology/) 上不存在，事故時團隊甚至不知道有這條依賴。修復方向是把 instrumentation coverage 作為 [readiness review](/backend/04-observability/observability-readiness-review/) 的檢查項。

**Context 斷鏈形成的局部盲區**：[trace context](/backend/knowledge-cards/trace-context/) 在 queue、thread pool、background job 邊界斷掉後，下游的 span 成為孤兒。團隊可以看到下游服務有問題，但看不到跟上游 request 的因果關係。修復策略見 [4.3 tracing](/backend/04-observability/tracing-context/)。

**Log schema 漂移**：不同服務的 log 用不同欄位名稱記錄同一個概念（`request_id` vs `req_id` vs `requestId`）。查詢時用 `request_id` 搜尋會漏掉用其他名稱的服務。修復方向是 [log schema](/backend/04-observability/log-schema/) 的跨服務統一。

### 盲區的判讀方式

- 列出所有服務，標記哪些有 trace instrumentation、哪些沒有
- 檢查 service graph 跟已知 architecture diagram 的差異 — 差異就是盲區
- 用已知的跨服務 request 做 end-to-end trace 驗證，看有沒有斷點
- 檢查 sampling policy，確認低流量服務跟 error sample 的保留率

## 弱點二：告警失真

告警失真是「觀測系統看到了、但告訴你的是錯的或沒用的」。失真比盲區更危險 — 盲區至少讓團隊知道「這裡沒資料、要用其他方式查」；失真讓團隊基於錯誤訊號做判斷。

### 常見失真模式

**Threshold drift**：alert 的閾值在設定時是合理的（error rate > 1%），但服務改版後基線變了（正常 error rate 從 0.1% 變成 0.5%），閾值沒跟著調。結果是 alert 頻繁觸發但團隊知道是 false alarm — [alert fatigue](/backend/knowledge-cards/alert-fatigue/) 開始累積。

**Aggregation 掩蓋**：用 average latency 做 alert，tail latency 被掩蓋。Average 200ms 但 p99 是 5 秒 — 1% 的使用者體驗極差但 alert 沒觸發。修復方向是 [percentile](/backend/knowledge-cards/percentile/) 跟 [histogram](/backend/knowledge-cards/histogram/)。

**Alert storm**：單一根因觸發大量 alert（database 慢 → 所有依賴該 database 的服務都觸發 latency alert + error alert + timeout alert）。On-call 收到 20 則通知，分不清哪個是因、哪個是果。修復方向是 alert grouping 跟 inhibition（見 [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/)）。

**Stale dashboard**：Dashboard 的 panel 引用的 metric name 已改名、panel 的 query 因 label 變更而回空值。Dashboard 看起來正常（曲線是平的），但其實是 no data 被渲染成 zero。修復方向是 dashboard 的 no-data alert 跟定期審視。

### 失真的判讀方式

- 追蹤 alert noise rate（每月有多少 alert 是 actionable 的）
- 檢查 alert rule 的 threshold 跟當前 baseline 是否對齊
- 確認 SLI 用 percentile 而非 average
- 事故復盤時問「這次的事故，alert 有沒有在對的時間告訴我們對的事」

## 弱點三：資料暴露

觀測資料本身是風險資產。Log 可能含 secret（API key、token、password）、trace 可能含 PII（使用者 email、電話號碼在 span attribute 中）、dashboard 可能對所有人開放且顯示敏感業務指標。

### 常見暴露路徑

**Log 含 secret**：SDK 或框架在 error 發生時把完整 request body 寫進 log，body 中的 API key、token、password 跟著進入 log storage。Log storage 的存取控制通常比 secret manager 寬鬆 — 有 log 讀取權限的人都能看到 secret。

**Trace attribute 含 PII**：`http.url` attribute 帶完整 URL（含 query parameter 裡的 email 或 token）、`db.statement` attribute 帶完整 SQL（含 WHERE 子句的使用者 ID）。Trace storage 的保留期可能比業務資料庫長，PII 在 trace 裡存活的時間超過必要範圍。

**Dashboard 權限過寬**：所有工程師都能看所有服務的 dashboard，包含財務相關的 metric（營收、訂單金額分布）。Dashboard 的存取控制粒度通常是「整個 Grafana instance」而非「per-dashboard」。

**Collector / pipeline 有管理員權限**：OTel Collector 或 log aggregator 以 admin 權限部署，可以讀寫 secret、修改配置、存取所有資料。Collector 被入侵時，攻擊者可以把 redaction 規則關掉、讓後續的 log 全量暴露。

### 暴露的修復方向

- SDK 端做 redaction（在送出前掃描已知 secret pattern 並替換成 `[REDACTED]`）
- Collector 端做 attribute 過濾（在 pipeline 中移除敏感 attribute）
- Log / trace storage 做存取控制（RBAC、per-team 隔離）
- Dashboard 做權限分層（業務 dashboard 需要額外授權）
- 定期掃描 log storage 檢查是否有未 redact 的 secret pattern

詳見 [07 資安與資料保護](/backend/07-security-data-protection/) 跟 [4.12 audit log governance](/backend/04-observability/audit-log-governance/)。

## 設計取捨：訊號完整度與成本控制

觀測覆蓋越完整，盲區越少、事故定位越快。同時儲存、查詢與維護成本也會上升。穩定做法是先定義核心訊號與最低欄位（[log schema](/backend/04-observability/log-schema/) 的 correlation fields、[SLI](/backend/04-observability/sli-slo-signal/) 的 availability + latency），再按高風險路徑逐步加深觀測。

「全收」的成本問題見 [4.7 cardinality](/backend/04-observability/cardinality-cost-governance/)；「選擇性收」的品質問題見 [4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/)。

## 核心判讀

判讀觀測弱點時，按三類依序盤點：

1. **盲區**：哪些服務或路徑沒有被觀測到？Sampling 是否丟掉高價值樣本？
2. **失真**：Alert noise rate 有多高？Threshold 跟 baseline 是否對齊？SLI 用的是 average 還是 percentile？
3. **暴露**：Log / trace 是否含 secret 或 PII？Dashboard 權限是否過寬？Collector 的存取權限是否最小化？

## 判讀訊號

- 事故時查 trace 查不到（sampling 丟掉）
- Service graph 跟 architecture diagram 有明顯差異（uninstrumented 服務）
- Alert noise rate > 30%（threshold drift 或 aggregation 掩蓋）
- 同一事故觸發 10+ 個 alert（alert storm、缺 grouping / inhibition）
- Log grep 到 API key 或 token（redaction 缺失）
- Dashboard 對所有人開放且顯示營收指標（權限過寬）

## 交接路由

- [4.3 tracing](/backend/04-observability/tracing-context/)：context 斷鏈的修復策略
- [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/)：alert noise control、grouping、inhibition
- [4.7 cardinality](/backend/04-observability/cardinality-cost-governance/)：sampling 策略與保留決策
- [4.8 signal governance](/backend/04-observability/signal-governance-loop/)：alert / dashboard 的定期審視
- [4.12 audit log](/backend/04-observability/audit-log-governance/)：觀測資料的存取控制與稽核
- [4.16 readiness review](/backend/04-observability/observability-readiness-review/)：instrumentation coverage 的上線前檢查
- [4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/)：sampling bias 跟 schema drift 的品質問題
- [07 資安](/backend/07-security-data-protection/)：secret management、data masking、存取控制
