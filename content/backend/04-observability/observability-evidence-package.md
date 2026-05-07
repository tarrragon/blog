---
title: "4.20 Observability Evidence Package"
date: 2026-05-02
description: "把 log、metric、trace、audit 與資料品質限制包成可交接證據"
weight: 20
---

## 大綱

- evidence package 的責任：把分散的 observability 資料包成可交給 reliability 與 incident response 的證據
- 資料來源：log、metric、trace、audit log、dashboard、query、client-side signal、deployment event
- 欄位：source、time range、owner、query link、data quality、confidence、known gap、retention
- 跟 4.17 的關係：telemetry data quality 提供資料限制，evidence package 提供交接格式
- 跟 6.23 的關係：可靠性驗證使用同一格式保存 experiment evidence
- 跟 8.18 / 8.19 的關係：事故 intake 與 decision log 使用同一組 evidence link
- 反模式：只貼 dashboard 截圖；query 沒有時間窗；evidence 沒標示 sampling / freshness 限制

Observability [evidence package](/backend/knowledge-cards/evidence-package/) 的核心是把可觀測資料從「查詢結果」升級成「可交接證據」。事故與驗證需要一組能說明來源、時間窗、可信度、限制與 owner 的 evidence。

## 概念定位

Observability evidence package 是可觀測性模組交給可靠性驗證與事故處理的證據包，責任是讓 log、metric、trace 與 audit log 能被重用、回放與復盤。

這一頁處理的是交接格式。4.17 [Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/) 說明資料是否可信；evidence package 說明如何把可信度、查詢入口與限制一起交給下游流程。

證據包的價值在於保存判讀上下文。只有截圖時，讀者看不到 query、時間窗、sampling、資料延遲與 owner；有 evidence package 時，後續 release gate、[incident decision log](/backend/knowledge-cards/incident-decision-log/) 與 post-incident review 才能回放同一組事實。

## Evidence 欄位

Evidence 欄位的責任是讓每個觀測證據都可查、可解釋、可追蹤。欄位不需要複雜，但要覆蓋事中判讀與事後復盤的最小需求。

| 欄位         | 責任                          | 判讀用途                          |
| ------------ | ----------------------------- | --------------------------------- |
| Source       | 標示資料來源                  | 區分 log、metric、trace、audit    |
| Time range   | 標示查詢時間窗                | 對齊 incident timeline            |
| Query link   | 保留可重跑查詢                | 支援 handoff 與復盤               |
| Owner        | 指定可解釋資料的人            | 避免 evidence 失去語意            |
| Data quality | 標示 completeness / freshness | 防止資料限制被誤讀                |
| Confidence   | 標示 confirmed / suspected    | 支援分級與決策                    |
| Known gap    | 標示 missing signal 或 drift  | 回寫 04 readiness 與 data quality |
| Retention    | 標示保存期限                  | 支援 audit、PIR 與長事故          |

Source 欄位讓讀者知道 evidence 的能力邊界。Metric 適合看趨勢，log 適合看事件細節，trace 適合看路徑，audit log 適合看責任鏈。

Time range 是 evidence package 的基本欄位。事故前後 30 分鐘、部署期間、DR drill 時窗、burn rate 短窗與長窗都需要明確，否則同一張圖可能被不同人解讀成不同結論。

Query link 比截圖更重要。截圖適合溝通當下狀態，query link 才能讓下一班 on-call、可靠性 owner 或 PIR reviewer 重跑同一個判讀。

Data quality 欄位讓 evidence 保留限制。sampling ratio、ingest delay、schema drift、log drop、cardinality truncation 與 timestamp skew 都應直接出現在證據包中。

## 資料來源

Evidence package 的資料來源要按判讀責任分層。每一層回答的問題不同，下游使用時也要保留這個差異。

| 資料來源           | 回答問題                     | 常見限制                         |
| ------------------ | ---------------------------- | -------------------------------- |
| Log                | 單一事件發生了什麼           | schema drift、drop、PII masking  |
| Metric             | 趨勢是否偏離穩態             | 聚合粒度、cardinality、延遲      |
| Trace              | 失效卡在哪個服務或依賴邊界   | sampling、async 斷鏈             |
| Audit log          | 高風險操作與責任鏈如何形成   | 權限限制、retention、法規要求    |
| Dashboard          | 操作視角如何快速判讀         | 面板版本、查詢成本、owner        |
| Client-side signal | 使用者感知是否和 server 一致 | browser / region / device bias   |
| Deployment event   | 近期變更是否與異常時間線重疊 | rollout 粒度、feature flag owner |

Log evidence 適合進入 incident intake。它要保留 request id、tenant、region、error class 與 trace id，讓事故候選能被查證。

Metric evidence 適合進入 SLO、release gate 與 [steady state](/backend/knowledge-cards/steady-state/) 判讀。它要保留時間窗、分母分子、聚合粒度與資料延遲，讓 burn rate 與容量判斷可回放。

Trace evidence 適合支援 dependency 與 async workflow 判讀。它要標示 sampling policy 與缺失 span，讓下游知道 trace 能支持到哪個邊界。

Audit log evidence 適合支援資安、資料修復與高風險操作。它要保留 access path、retention、masking 與 chain of custody 限制。

## 打包流程

Evidence package 的打包流程是從問題開始。先問下游要做什麼決策，再選擇足以支援該決策的資料與工具入口。

1. 定義 evidence 要支援的決策：readiness、release gate、incident intake、decision log 或 PIR。
2. 選擇最小資料集合：metric 看趨勢、log 看事件、trace 看路徑、audit 看責任。
3. 補上 time range、query link、owner 與 data quality。
4. 標示 confidence 與 known gap。
5. 把缺口回寫到 4.16 readiness、4.17 data quality 或 4.18 operating model。

Readiness 用的 evidence package 要回答「服務是否能被判讀」。它重視核心旅程、依賴、dashboard、alert、trace 與 owner。

Reliability 用的 evidence package 要回答「驗證是否有結果」。它重視 steady state、stop condition、experiment timeline、SLO burn 與回復訊號。

Incident 用的 evidence package 要回答「事故是否需要啟動、升級或回退」。它重視 source、impact scope、confidence、decision log 與 stakeholder update。

## 常見反模式

Evidence package 的反模式通常來自把資料貼出來就當作證據交接。證據需要上下文，否則只是一段輸出。

| 反模式              | 表面現象                       | 修正方向                      |
| ------------------- | ------------------------------ | ----------------------------- |
| 只貼 dashboard 截圖 | 事後缺少可重跑查詢             | 保留 query link 與 time range |
| Query 無時間窗      | 同一查詢不同時間跑出不同結論   | 標準化 time range             |
| 缺資料品質限制      | sampling / drop / delay 被忽略 | 引用 4.17 data quality 欄位   |
| Evidence 無 owner   | 下游無人能解釋欄位語意         | 指定 service / platform owner |
| Retention 未標示    | PIR 或 audit 時證據已過期      | 標示 retention 與保存責任     |

只貼 dashboard 截圖會讓 evidence 失去可回放性。截圖可以當摘要，query、時間窗與資料限制則提供復盤與交接能力。

缺資料品質限制會讓下游高估證據。若 trace sampling 只保留 10%、log pipeline 有 drop、metric 有 ingest delay，這些限制要跟證據一起交接。

## 交接路由

- 4.16 observability readiness：補 evidence package 所需的訊號入口
- 4.17 telemetry data quality：標示 completeness、freshness、drift 與 sampling 限制
- 4.18 operating model：指定 evidence owner、retention 與 review cadence
- 6.23 verification evidence handoff：把驗證結果包成同一格式
- 8.18 incident intake：把 evidence package 轉成事故候選
- 8.19 incident decision log：把 evidence package 連到事中決策
