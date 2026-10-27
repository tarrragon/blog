---
title: "模組四：可觀測性平台"
date: 2026-04-22
description: "整理 log、metric、trace、dashboard 與 alert 的後端操作實務"
weight: 5
tags: ["backend", "observability", "operations"]
---

可觀測性模組的核心目標是說明服務如何把 [log schema](/backend/knowledge-cards/log-schema/)、[metrics](/backend/knowledge-cards/metrics/) 與 [trace context](/backend/knowledge-cards/trace-context/) 轉成可操作的診斷系統。語言教材會處理標準 logger、執行環境訊號、[Diagnostic Endpoint](/backend/knowledge-cards/diagnostic-endpoint/) 與 [trace context](/backend/knowledge-cards/trace-context/) 邊界；本模組負責平台、資料流與操作規則。

## Vendor / Platform 清單

實作時的常用選擇見 [vendors](/backend/04-observability/vendors/) — T1 收錄 OpenTelemetry / Prometheus / Grafana Stack / Datadog / Elastic Stack / Honeycomb / AWS CloudWatch / GCP Cloud Operations / Sentry，每個 vendor 有定位、適用場景、取捨與預計實作話題的骨架。Error tracking 是獨立子維度（Sentry），跟 metrics / logs / traces 三角互補。

進入 vendor 比較前，先回到 [觀測、可靠性與事故服務選型](/backend/00-service-selection/operations-control-service-selection/) 判斷目前缺的是訊號層、驗證層、響應層還是閉環層。可觀測性 vendor 選型只處理訊號層與部分告警入口；可靠性驗證與事故協作要交給可靠性與事故流程。

Deep article（vendor 自身的配置、故障、容量）跟 migration playbook（跨 vendor 遷移流程）的撰寫進度見 [vendors/](/backend/04-observability/vendors/) 的「內容覆蓋進度」段。

## 暫定分類

| 分類                                            | 內容方向                                                                                                                                                      |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Log](/backend/knowledge-cards/log) aggregation | [log schema](/backend/knowledge-cards/log-schema)、索引、查詢、保留策略                                                                                       |
| [Metrics](/backend/knowledge-cards/metrics)     | counter、gauge、[histogram](/backend/knowledge-cards/histogram)、[metric cardinality](/backend/knowledge-cards/metric-cardinality/)、Prometheus               |
| Tracing                                         | [span](/backend/knowledge-cards/span)、[trace id](/backend/knowledge-cards/trace-id)、[trace context](/backend/knowledge-cards/trace-context/)、OpenTelemetry |
| [Dashboard](/backend/knowledge-cards/dashboard) | SLI、[SLO](/backend/knowledge-cards/sli-slo)、容量趨勢、服務健康                                                                                              |
| [Alert](/backend/knowledge-cards/alert)         | alert rule、noise control、[runbook](/backend/knowledge-cards/runbook)、[on-call](/backend/knowledge-cards/on-call) workflow                                  |

## 選型入口

可觀測性選型的核心判斷是團隊缺少哪一種操作訊號。當工程師需要還原事件脈絡時先看 [log](/backend/knowledge-cards/log/)；需要趨勢與容量判斷時先看 [metrics](/backend/knowledge-cards/metrics/)；需要跨服務路徑時先看 [trace](/backend/knowledge-cards/trace/)；需要共同操作入口時先看 [dashboard](/backend/knowledge-cards/dashboard/)；需要主動通知時先看 [alert](/backend/knowledge-cards/alert/)。

Log aggregation 適合查單一事件與錯誤脈絡；metrics 適合觀察 error rate、latency、[throughput](/backend/knowledge-cards/throughput/) 與 [queue](/backend/knowledge-cards/queue/) lag；tracing 適合拆解跨服務 request path；dashboard 適合整合 [SLI/SLO](/backend/knowledge-cards/sli-slo/) 與容量趨勢；alert 適合把需要動作的異常送到負責者面前，並連到 [alert runbook](/backend/knowledge-cards/alert-runbook/)。

接近真實網路服務的例子包括 checkout 變慢、queue lag 上升、[WebSocket](/backend/knowledge-cards/websocket/) 斷線增加、Redis [timeout](/backend/knowledge-cards/timeout) 增加與下游 API 錯誤率上升。這些場景的共同問題是從症狀回到原因，因此本模組會先處理欄位、關聯、[metric cardinality](/backend/knowledge-cards/metric-cardinality/)、查詢、視覺化與告警規則。

## 訊號情境庫

本模組收的是可重複套用的訊號情境，不收服務級案例庫。服務的長期時間線與事故史，留給可靠性驗證與事故處理兩個模組；可觀測性平台只保留能反覆套用在不同服務上的觀測判讀樣式，讓讀者先知道「該看哪種訊號、如何辨識失真、下一步交給誰」。

| 情境                         | 先看訊號                                                                                                                                                                                                                       | 判讀重點                                                                                                                               | 下一步路由                                                                    |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| checkout 變慢                | latency [histogram](/backend/knowledge-cards/histogram/)、[trace](/backend/knowledge-cards/trace/)、downstream error rate                                                                                                      | 先分辨是 app latency、DB wait、cache miss 還是外部依賴慢                                                                               | 需要驗證回歸時回到 [可靠性驗證流程](/backend/06-reliability/)                 |
| queue lag 上升               | [queue depth](/backend/knowledge-cards/queue-depth/)、[consumer lag](/backend/knowledge-cards/consumer-lag/)、[retry policy](/backend/knowledge-cards/retry-policy/)、[DLQ](/backend/knowledge-cards/dead-letter-queue/) count | 先判斷是 [consumer](/backend/knowledge-cards/consumer/) 不足、downstream 變慢，還是 [redelivery](/backend/knowledge-cards/redelivery/) | 需要壓力驗證與回放時回到 [可靠性驗證流程](/backend/06-reliability/)           |
| metric cardinality 爆掉      | label explosion、cardinality growth、query latency                                                                                                                                                                             | 先看是否為維度設計失控、tenant label 過細，或聚合點過多                                                                                | 需要訊號治理與告警修正時回到 [事故處理與復盤](/backend/08-incident-response/) |
| trace 斷鏈                   | missing [span](/backend/knowledge-cards/span/)、[trace context](/backend/knowledge-cards/trace-context/) propagation error、sample gap                                                                                         | 先看 context 是否跨 thread / task / process 正確傳遞                                                                                   | 需要補 instrumentation 時回到 [可靠性驗證流程](/backend/06-reliability/)      |
| alert 太吵但真正事件沒被抓到 | alert volume、[burn rate](/backend/knowledge-cards/burn-rate/)、[symptom-based alert](/backend/knowledge-cards/symptom-based-alert/) mismatch                                                                                  | 先判斷是閾值太低、維度太窄，還是只盯症狀而沒盯服務健康指標                                                                             | 需要事故演練與回寫時回到 [事故處理與復盤](/backend/08-incident-response/)     |

這種情境庫的責任是定位訊號，服務史由可靠性驗證與事故處理承接。當讀者需要的是平台能力與判讀路由，可觀測性模組的範圍就夠了；當需要的是某個服務怎麼一路演進、怎麼歷次驗證與恢復，那是可靠性與事故模組的工作。

## 跟可靠性與事故模組的串接

可觀測性是「觀測 → 驗證 → 事故」閉環的起點，但閉環是雙向的：

- **觀測 → 事故**：訊號（log spike、SLO [burn rate](/backend/knowledge-cards/burn-rate/)、error rate）觸發告警、進入事故響應流程。判讀邊界由可觀測性定義、響應節奏由事故處理定義。
- **觀測 → 驗證**：SLO / SLI 量測由可觀測性提供、是 SLO 政策與 chaos hypothesis 的 baseline。沒有可信訊號就沒有可信驗證。
- **驗證 → 觀測**：驗證需求驅動訊號設計 — chaos experiment 需要新 metric、load test 需要新 dashboard、SLO 政策需要新 alert rule。
- **客服 → 觀測**：使用者比告警先發現的故障，由客服回報經工程查證之後寫回告警規則或合成監控（[8.24 客服回報的處理](/backend/08-incident-response/support-escalation-and-engineering-reply/)）；客服單量與排名在前的錯誤碼也是值班接班時與每週營運會議讀的訊號（[4.29 值班的例行檢查](/backend/04-observability/on-call-routine-checks/)）。
- **事故 → 觀測**：每次事故 [post-incident review](/backend/knowledge-cards/post-incident-review/) 揭露偵測缺口（symptom-based alert 缺、訊號太晚、cardinality 不足），回寫到訊號治理。
- **資安 → 觀測**：資安偵測、稽核證據與資料外洩風險會形成新的 log schema、audit log、alert 與 evidence chain 需求。尤其 [偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 會回寫到訊號治理閉環。
- **觀測 → 資安**：log、trace、audit log 與 service topology 提供資安 triage 的事實基礎，讓 [稽核追蹤與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/) 能把責任鏈落到可查證資料。
- **詳細閉環說明**：見 [Observability / Reliability / Incident Response 閉環](/backend/08-incident-response/observability-reliability-incident-loop/)。

## 跟 Monitoring 模組的串接

[Monitoring 模組](/devops/monitoring/) 聚焦非 server 端 runtime — mobile app、web 頁面、本機腳本的行為蒐集、錯誤回報與 SDK 設計。本模組聚焦 server-side observability。兩者的交叉點是 trace context propagation 和 event transport format。

- [4.10 Client-side / Synthetic / RUM](/backend/04-observability/client-side-monitoring/)：概念定位、RUM 與 synthetic 的 server-side 整合
- [4.24 Client-to-Server 觀測串接](/backend/04-observability/client-server-trace-integration/)：從 browser click 到 server span 的完整 trace 鏈路
- [監控資料的雙重用途](/devops/monitoring/telemetry-data-dual-use/)：同一份 event data 如何同時服務行為分析（monitoring/08）與訊號治理（04）
- [0.15 跨模組 Checkout Episode](/backend/00-service-selection/cross-module-checkout-episode/)：從 DB write 到 observability evidence 的四層端到端串聯

## 與語言教材的分工

語言教材處理如何產生穩定欄位與執行環境訊號。Backend observability 模組處理收集、儲存、查詢、視覺化、告警與跨服務關聯。

## 企業案例補充

可觀測性的案例補充重點是「訊號平台為什麼這樣設計」，不是工具比較表。閱讀時先抓資料規模、查詢延遲、保留策略與多租戶治理，再對照本模組章節。

| 企業案例                                                                                                      | 主要觀測選型問題                             | 優先回讀章節                                                                                                                                                                     |
| ------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [M3: Uber’s Open Source, Large-scale Metrics Platform for Prometheus](https://www.uber.com/en-GB/blog/m3/)    | 單機 Prometheus 不足時如何擴成平台層         | [4.2 metrics 與 SLI/SLO](/backend/04-observability/metrics-basics/)、[4.11 Telemetry Pipeline 架構](/backend/04-observability/telemetry-pipeline/)                               |
| [Building Cloudflare on Cloudflare](https://blog.cloudflare.com/building-cloudflare-on-cloudflare/)           | 大規模系統內部如何同時做 logs/metrics/traces | [4.1 log schema 與搜尋規劃](/backend/04-observability/log-schema/)、[4.3 tracing 與 context link](/backend/04-observability/tracing-context/)                                    |
| [Cloudflare Observability](https://blog.cloudflare.com/vision-for-observability/)                             | 監控、分析、鑑識三層能力如何組合             | [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)、[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)      |
| [How Discord Stores Trillions of Messages](https://discord.com/blog/how-discord-stores-trillions-of-messages) | 成長後如何從儲存問題回推觀測缺口             | [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)、[4.18 Observability Operating Model](/backend/04-observability/observability-operating-model/) |

若要擴充企業案例，先到 [0.14 企業選型案例圖譜](/backend/00-service-selection/enterprise-selection-case-atlas/) 依「企業型態 × 規模階段」挑樣本，再把觀測面教訓回寫到 4.16-4.21。這樣案例擴充會先補齊覆蓋度，再補單點技巧。

第一批缺口回填建議先做三條觀測題目：FinTech 補 audit log completeness 與 evidence traceability（回寫 4.12、4.20）；Gaming 補高峰時段 signal freshness 與 cardinality guardrail（回寫 4.7、4.17）；Healthcare 補資料主權相關的 access evidence 與留存邊界（回寫 4.12、4.18）。

| 產業案例類型 | 觀測回寫重點                                       | 章節路由                                                                                                                                                                            |
| ------------ | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FinTech      | 金流與帳務事件的 evidence chain、審計 log 完整性   | [4.12 Audit Log 邊界與 PII 治理](/backend/04-observability/audit-log-governance/)、[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) |
| Gaming       | 高峰流量下的訊號新鮮度、cardinality 膨脹與警示品質 | [4.7 Cardinality 治理與成本邊界](/backend/04-observability/cardinality-cost-governance/)、[4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)          |
| Healthcare   | 存取軌跡可追溯性、資料留存邊界與跨團隊 ownership   | [4.12 Audit Log 邊界與 PII 治理](/backend/04-observability/audit-log-governance/)、[4.18 Observability Operating Model](/backend/04-observability/observability-operating-model/)   |

第一批案例正文入口見 [可觀測性案例正文](/backend/04-observability/cases/)，可直接對應 `4.12 / 4.17 / 4.18 / 4.20` 的回寫欄位。

第二批觀測遷移案例已補： [4.C4 X-Ray 到 OTel 轉換](/backend/04-observability/cases/xray-to-opentelemetry-migration/) 與 [4.C5 Cloud Trace OTLP 導入](/backend/04-observability/cases/cloud-trace-otlp-adoption/)。兩者可直接回寫到 [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/)、[4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/) 與 [4.18 operating model](/backend/04-observability/observability-operating-model/)。

反例與規模對照入口： [4.C9 反例](/backend/04-observability/cases/failure-otel-migration-signal-drift/) / [4.C10 對照](/backend/04-observability/cases/contrast-observability-rollout-by-scale/)。

回退判讀寫法見 [0.C4 回退判讀寫法](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/#回退判讀寫法)，觀測案例要優先保留訊號語意、採樣策略、告警偏差與 SLO 判讀差異。

## 跨語言適配評估

可觀測性使用方式會受語言的 logger 生態、[trace context](/backend/knowledge-cards/trace-context/)、exception/error model、執行環境 metrics 與 instrumentation SDK 影響。同步 runtime 要保留 request context 與 thread-local 邊界；async runtime 要確認 [trace context](/backend/knowledge-cards/trace-context/) 能跨 task 傳遞；輕量並發 runtime 要觀察 task/goroutine 數量、queue lag 與下游等待。動態語言要特別管理 log schema 穩定性；強型別語言則要避免過度包裝導致 trace 與 error chain 斷裂。

## 章節列表

| 章節                                                                                                                                                                                                                  | 主題                                   | 關鍵收穫                                                                                                                                                                                                                             |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [4.0 服務端監控的分層](/backend/04-observability/monitoring-layers/)                                                                                                                                                  | 服務端監控的分層                       | 容器與程序的自檢、服務網路內的探測、元件指標、應用層訊號、告警規則與分送、告警鏈的監看與使用者路徑的合成監控，各層檢查的對象、看不到的範圍與接手的層；以這條鏈盤點一個服務時檢查範圍盲區、位置盲區、讀取缺口與訊號失真各自的補法     |
| [4.0.1 監控鏈事前偵測不到的異常](/backend/04-observability/monitoring-outside-the-chain/)                                                                                                                             | 監控鏈共同的檢查範圍盲區               | 業務結果、資料正確性、到期事件、排程與背景工作、備份、安全、第三方依賴與成本，各自要先定義的預期與檢查它的規則                                                                                                                       |
| [4.0.2 以監控鏈盤點單機短網址服務](/backend/04-observability/monitoring-inventory-single-host/)                                                                                                                       | 盤點案例：單機                         | 觀察者全在一台主機上時各層的缺口、補法，以及主機停機前沒有任何一層會通知的情形                                                                                                                                                       |
| [4.0.3 以監控鏈盤點 Kubernetes 上的電商 checkout](/backend/04-observability/monitoring-inventory-k8s-checkout/)                                                                                                       | 盤點案例：叢集、佇列與第三方           | 叢集、帳號與區域三種失效域的觀察者位置，readiness 納入金流業者的後果，消費端、金流回呼與對帳的盤點                                                                                                                                   |
| [4.0.4 以監控鏈盤點交易撮合系統](/backend/04-observability/monitoring-inventory-matching-engine/)                                                                                                                     | 盤點案例：低延遲、單一執行緒           | 觀察者從輸出日誌讀數字、以路徑心跳分辨市場安靜與路徑停住、分段量測延遲與時鐘偏差、依序日誌多數節點與同一可用區的失效域、序號斷號與部位對帳                                                                                           |
| [4.1 log schema 與搜尋規劃](/backend/04-observability/log-schema/)                                                                                                                                                    | log schema 與搜尋規劃                  | 設計欄位、索引與查詢方式                                                                                                                                                                                                             |
| [4.2 metrics 與 SLI/SLO](/backend/04-observability/metrics-basics/)                                                                                                                                                   | metrics 與 SLI/SLO                     | 用 counter、gauge、histogram 描述服務健康                                                                                                                                                                                            |
| [4.3 tracing 與 context link](/backend/04-observability/tracing-context/)                                                                                                                                             | tracing 與 context link                | 追蹤跨服務 request path                                                                                                                                                                                                              |
| [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)                                                                                                                                             | dashboard 與 alert 設計                | 讓告警能對應 runbook 與容量趨勢                                                                                                                                                                                                      |
| [4.5 可觀測性威脅建模（Threat Modeling）](/backend/04-observability/attacker-view-observability-risks/)                                                                                                               | 可觀測性威脅建模（Threat Modeling）    | 用盲區、告警失真與資料暴露風險盤點觀測系統                                                                                                                                                                                           |
| [4.6 SLI 量測與 SLO 訊號設計](/backend/04-observability/sli-slo-signal/)                                                                                                                                              | SLI 量測與 SLO 訊號設計                | 把可靠性目標轉成可量測訊號、餵給 6.6 SLO 政策                                                                                                                                                                                        |
| [4.7 Cardinality 治理與成本邊界](/backend/04-observability/cardinality-cost-governance/)                                                                                                                              | Cardinality 治理與成本邊界             | 把 cardinality 與保留階梯作為平台一級治理                                                                                                                                                                                            |
| [4.8 訊號治理閉環](/backend/04-observability/signal-governance-loop/)                                                                                                                                                 | 訊號治理閉環                           | 把 [post-incident review](/backend/knowledge-cards/post-incident-review/) 偵測缺口回寫成新訊號                                                                                                                                       |
| [4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/)                                                                                                                                           | Continuous Profiling                   | 把 CPU / heap / lock profile 升級為持續訊號                                                                                                                                                                                          |
| [4.10 Client-side / Synthetic / RUM](/backend/04-observability/client-side-monitoring/)                                                                                                                               | Client-side / Synthetic / RUM          | 補 server-side 看不到的 user perceived 訊號                                                                                                                                                                                          |
| [4.11 Telemetry Pipeline 架構](/backend/04-observability/telemetry-pipeline/)                                                                                                                                         | Telemetry Pipeline 架構                | 把採集到查詢分層治理、定位 pipeline 失敗                                                                                                                                                                                             |
| [4.12 Audit Log 邊界與 PII 治理](/backend/04-observability/audit-log-governance/)                                                                                                                                     | Audit Log 邊界與 PII 治理              | 把稽核訊號從 operational log 拆出、按法規治理                                                                                                                                                                                        |
| [4.13 Service Topology 與 Dependency Map](/backend/04-observability/service-topology/)                                                                                                                                | Service Topology 與 Dependency Map     | 把跨服務依賴變成自動發現的觀測訊號                                                                                                                                                                                                   |
| [4.14 Anomaly Detection](/backend/04-observability/anomaly-detection/)                                                                                                                                                | Anomaly Detection                      | ML / statistical baseline alert 跟 rule-based 整合                                                                                                                                                                                   |
| [4.15 Cost Attribution / Chargeback](/backend/04-observability/cost-attribution/)                                                                                                                                     | Cost Attribution / Chargeback          | 把 observability 成本拆到團隊 / 服務維度                                                                                                                                                                                             |
| [4.16 Observability Readiness Review](/backend/04-observability/observability-readiness-review/)                                                                                                                      | Observability Readiness Review         | 在服務上線、重大變更與演練前檢查 log / metric / trace / alert 是否可支援事故判讀                                                                                                                                                     |
| [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)                                                                                                                                      | Telemetry Data Quality                 | 把 missing signal、schema drift、sampling bias 與 timestamp skew 變成資料品質問題                                                                                                                                                    |
| [4.18 Observability Operating Model](/backend/04-observability/observability-operating-model/)                                                                                                                        | Observability Operating Model          | 定義 platform / service team / on-call 對訊號、dashboard、alert 與成本的 ownership                                                                                                                                                   |
| [4.19 Debuggability by Design](/backend/04-observability/debuggability-by-design/)                                                                                                                                    | Debuggability by Design                | 把可診斷性前移到 API、async workflow、dependency call 與錯誤模型設計                                                                                                                                                                 |
| [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)                                                                                                                      | Observability Evidence Package         | 把 log、metric、trace、audit 與資料品質限制包成可交接證據                                                                                                                                                                            |
| [4.21 Rule-level CPU Signal Governance](/backend/04-observability/rule-level-cpu-signal-governance/)                                                                                                                  | Rule-level CPU Signal Governance       | 把規則執行成本變成可觀測訊號，避免小變更在全域 rollout 後形成 CPU 熱點                                                                                                                                                               |
| [4.22 Checkout API Evidence Package 實作示範](/backend/04-observability/checkout-api-evidence-package/)                                                                                                               | Checkout API Evidence Package 實作示範 | 以 checkout 路徑示範 evidence package 如何交接到 gate 與 incident                                                                                                                                                                    |
| [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)                                                                                                                                            | 觀測查詢設計                           | 把讀取路徑當系統設計問題：三種查詢模式、storage tiering、pre-aggregation 與資源治理                                                                                                                                                  |
| [4.24 Client-to-Server 端到端觀測串接](/backend/04-observability/client-server-trace-integration/)                                                                                                                    | Client-to-Server 端到端觀測串接        | 用一個結帳場景走完 browser click → trace context → server span → 統一 waterfall 的完整實作鏈路                                                                                                                                       |
| [4.25 觀測共命運失效：工具退化時的訊號與人層設計](/backend/04-observability/observability-shared-fate/)                                                                                                               | 觀測共命運失效                         | 觀測跟系統一起退化時的 out-of-band 訊號、優雅降級、與 telemetry 不可信下的人層應對設計                                                                                                                                               |
| [4.26 單機容器服務的流量與資源監控：各層的訊號、Prometheus 與 exporter、監控所在層的盲區](/backend/04-observability/host-traffic-resource-monitoring/)                                                                | 單機容器服務的流量與資源監控           | 入口、應用程式、容器、主機與服務內部各層的訊號與 exporter，工具選項的取捨，單次取樣與時間窗，cAdvisor 在 OrbStack 上缺容器標籤的成因，監控裝在虛擬機裡看不到主機的 CPU 負載、磁碟要分清是哪一顆                                      |
| [4.27 主機過載時的監控告警：可用與變慢分開判斷、依原因抑制、監控自身的等待](/backend/04-observability/host-overload-alerting/)                                                                                        | 主機過載時的監控告警                   | 共用主機過載讓各服務的探測一起失敗時，可用性與延遲分開判斷、條件持續才告警、以主機飽和抑制服務變慢與它在虛擬機裡判斷不到的條件、抑制藏起受影響程度的差別、探測與 Prometheus 自身的等待                                               |
| [4.28 單台主機的監控盲區與失效域以外的觀察者：主機停機、使用者路徑中斷與告警鏈中斷，心跳監看與外部探測各自回答的問題與位置，以及與內部探測並排的判讀](/backend/04-observability/single-host-monitoring-outside-view/) | 單台主機的監控盲區與失效域以外的觀察者 | 服務與監控同一個失效域時看不到的主機停機、使用者路徑中斷與告警鏈中斷，心跳監看與外部探測各回答的問題與成立條件，觀察者放在第三方、另一個失效域的主機（含互相監看）或另一個業者的排程平台，心跳監看、外部探測與主機內部探測並排的判讀 |
| [4.29 值班的例行檢查：接班檢查與每週營運會議讀的訊號、交班紀錄的內容，以及例行檢查項目改寫成告警規則的條件](/backend/04-observability/on-call-routine-checks/)                                                        | 值班的例行檢查                         | 告警刻意不通知的訊號由值班定時讀：開班時的靜音、warning、error budget、排程與到期事件、容量走向、近期變更與客服單量；交班紀錄的內容；每週營運會議；檢查項目改寫成告警的條件                                                          |

> 註：4.0 是模組的入口篇，以每一層回答的問題把各章串成監控鏈，讀者路線從它開始。4.1-4.28 已完成概念層、實作示範與端到端串接正文，4.29 補告警以外由值班定時讀的訊號，案例庫可支援 06 與 08 的路由引用。後續工作重點為案例深挖與跨模組回寫密度提升，而非章節補齊。4.25（觀測共命運失效）是深化補的一章，處理「觀測系統自己在事故中失能」這個 4.1-4.24 假設可用、未正面展開的邊界。

## Backlog

格式見 [Backlog 段格式規範](/posts/backlog-format-spec/)。

| 項目                                                                                                                                                                                                                                                                                                                                                                         | 類型   | 前置條件                                                                                                      | 規模       |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------- | ---------- |
| OpenTelemetry deep article：Sampling 策略、Auto-instrumentation                                                                                                                                                                                                                                                                                                              | vendor | 無                                                                                                            | 2 篇（中） |
| 4.0.4 的反向連結回填：dead-mans-switch 卡〈概念位置〉補處理路徑內部的變體（路徑心跳）與它不滿足的位置條件；clock-skew、hybrid-logical-clock、quorum、consensus-protocol、consumer-lag、thundering-herd 卡，4.17〈時間對齊〉、4.25、9.C3 Coinbase 的〈下一步路由〉指回 4.0.4                                                                                                  | 跨模組 | 無                                                                                                            | 中         |
| 路徑心跳的業界名稱：候選有 heartbeat order、canary order、Flink 的 latency marker，先跑術語探針再決定是否改名或建卡                                                                                                                                                                                                                                                          | 知識卡 | 術語探針                                                                                                      | 小         |
| 4.0.4 只有兩個可用區時依序日誌的失效域：分不到三個以上的失效域時，第三個投票節點放在另一個區域或機房的做法與它對寫入延遲的代價（Round 4 個案實跑答不出來的那一步）                                                                                                                                                                                                           | 主章   | 需查 Raft 實作的 witness／learner 支援                                                                        | 小         |
| 4.0.2、4.0.3 的資料正確性段連到範例系統〈四個系統在請求性質上的差別〉的第三欄（backend _index 的交付條件），或把交付條件改成「適用時」                                                                                                                                                                                                                                       | 案例   | 無                                                                                                            | 小         |
| 案例反例補強（遷移失敗與訊號失真案例）                                                                                                                                                                                                                                                                                                                                       | 案例   | 需先採集公開案例                                                                                              | 中         |
| 觀測欄位對齊 release / incident 決策欄位                                                                                                                                                                                                                                                                                                                                     | 跨模組 | 需與 06、08 對齊                                                                                              | 中         |
| Meta-monitoring 卡：觀察者自己消失時的規則（`up == 0`、`absent()`）與心跳，站內九篇用到而沒有名字；4.0 的訊號失真引用它                                                                                                                                                                                                                                                      | 知識卡 | 名稱先跑術語探針                                                                                              | 1 張       |
| Real User Monitoring 卡：4.0 與 synthetic-monitoring 卡以行內定義，主場在 4.10                                                                                                                                                                                                                                                                                               | 知識卡 | 無                                                                                                            | 1 張       |
| 4.0 的回指：health-check-endpoint、small-service-host-layout、going-live/what-is-deploy、legacy-external-monitoring、operations-control-service-selection、service-failure-monitoring；synthetic-monitoring 卡在 4.25、external-heartbeat、legacy-external-monitoring 的入連                                                                                                 | 跨模組 | 無                                                                                                            | 小         |
| 4.6〈Multi-window multi-burn-rate〉的視窗數字核對：表寫「2hr + 3day」，SRE Workbook Table 5-8 的 ticket 列是「3 days 加 6 hours」；4.29 改為不引數字，核對後回填                                                                                                                                                                                                             | 主章   | 無                                                                                                            | 小         |
| 4.29 / alert-silence 的低優先回指：4.0〈告警鏈的監看〉補「心跳不證明沒有告警被靜音壓下」、4.27 與 kubernetes-monitoring-entry、visualization-tool-selection、external-heartbeat 的 silence 與暫停項目連卡、4.4〈Noise rate 量測〉與〈判讀訊號〉連 4.29；4.25 的「低摩擦 support-to-engineering 升級」連 8.24                                                                 | 跨模組 | 無                                                                                                            | 小         |
| 4.12 的 operational log 保留期前後不一（表寫 7-30 天、〈Retention 與保留策略漂移〉寫 30-90 天），11.16 兩處都引用                                                                                                                                                                                                                                                            | 主章   | 無                                                                                                            | 小         |
| Page 與 Ticket 卡（呼叫值班與只送通知）：8.24 與 4.29 各定義一次，4.4、observability-readiness-review、operations-control-service-selection 直接用 page 而不解釋                                                                                                                                                                                                             | 知識卡 | 先跑術語探針確認中文名                                                                                        | 小         |
| 停在失效（觸發消失、請求率回到平常之後仍不恢復）的偵測規則：入口請求率已回到平常範圍而成功完成的請求量仍偏低時送出的比對告警（PromQL 寫法、平常範圍的取法、持續時間），在 tinyurl-test 用重試造出一次再實測                                                                                                                                                                  | 主章   | 無（判斷標準已寫在 9.16 與 metastable-failure 卡；動筆時先定扣掉重試的請求率取法，並判斷 goodput 要不要建卡） | 小         |
| readiness 納入外部依賴的說法對齊：operations/04-service-health/liveness-vs-readiness〈Liveness〉段「外部 API 逾時屬於 readiness 或熔斷」與 05/platform-lifecycle-contract 同樣的「或」，和 4.0.3〈付款服務的 readiness 納入金流業者時的後果〉衝突，改成依依賴類別分流（必要依賴進 readiness、所有副本共用的可降級依賴進熔斷）                                                | 跨模組 | 無                                                                                                            | 小         |
| readiness 是否納入所有副本共用的必要依賴（資料庫）：站內 4.0.3、operations/liveness-vs-readiness、ci 的卡都主張納入（與 Kubernetes 文件一致），DoorDash 的 health check 文章與部分業界說法主張不讓共用依賴拉掉全部副本；兩種立場的後果（入口的 503 與服務自己的錯誤、恢復時反覆上下線、修復工具還能不能用）站內沒有一處並陳，先判斷是補進 liveness-vs-readiness 還是另開一篇 | 主章   | 無（Round 3 個案實跑登記，來源在 commit dc3af9ff 的訊息）                                                     | 中         |
| 4.C13 Discord 案例檔查證：「aggregated latency metric（p50、p95）看起來正常」「由使用者回報才發現」「ScyllaDB tail latency 比 Cassandra 高」三處在它引的兩篇 Discord blog 裡找不到（原文是 p95 告警門檻 80ms、on-call 被 page、dual-read 只寫 looked great），回原文改寫或刪除                                                                                               | 案例   | 無                                                                                                            | 小         |

「個案前拓展空間」列的四個前置控制面（4.16-4.19）已全數完成，保留該段作為回寫路由的判斷標準參考。

### 個案前拓展空間

個案前拓展的責任是補足讀案例時需要的判讀框架。04 適合補「訊號是否足以支援判讀」這類跨服務能力，不適合展開單一服務的事故史。

| 拓展方向                       | 補充理由                                       | 先放位置 |
| ------------------------------ | ---------------------------------------------- | -------- |
| Observability Readiness Review | 服務上線前需要先知道訊號是否支援事故分級與驗證 | 4.16     |
| Telemetry Data Quality         | 觀測資料本身也會缺漏、漂移、偏誤與時間錯位     | 4.17     |
| Observability Operating Model  | dashboard、alert、成本與淘汰需要明確 owner     | 4.18     |
| Debuggability by Design        | 診斷能力需要進入 API / async / dependency 設計 | 4.19     |

本輪先完成這四個前置控制面，讓後續 06 與 08 文章有穩定的訊號前提可引用。若服務案例暴露的是訊號分類問題，回寫 4.16；若暴露的是資料品質問題，回寫 4.17；若暴露的是 owner 與治理問題，回寫 4.18；若暴露的是架構本身難以診斷，回寫 4.19。

### 後續深化方向

04 後續深化以「案例反例補強、跨模組回寫、證據欄位對齊」為主。可觀測性是 06 與 08 的輸入層，重點在提高 evidence package、data quality 與 incident write-back 的銜接精度。

| 深化方向     | 主要責任                                        | 回寫路由                                                                                                                                                                           |
| ------------ | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 案例反例補強 | 補齊遷移失敗與訊號失真案例                      | [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)、[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) |
| 跨模組對位   | 把觀測欄位對齊 release/incident 決策欄位        | [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/)、[8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)   |
| 成本與治理   | 把採樣、cardinality、chargeback 連到 owner 決策 | [4.7 Cardinality 治理與成本邊界](/backend/04-observability/cardinality-cost-governance/)、[4.15 Cost Attribution / Chargeback](/backend/04-observability/cost-attribution/)        |

## 實作探討入口

進入實作層時，04 建議先從一條最小切片開始：同一個 user journey 建立 `SLI + dashboard + alert + evidence query` 四件組，再把欄位直接接到 [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/) 與 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

首篇示範已完成： [4.22 Checkout API Evidence Package 實作示範](/backend/04-observability/checkout-api-evidence-package/)。

完成條件是每篇都能回答四件事：判讀訊號、風險代價、控制面邊界與下一步路由。這樣 06 的 SLO / readiness / experiment safety 與 08 的 intake / decision log / impact assessment 才能引用 04，而不需要在各自章節重寫觀測前提。

## 跟 Infra 可觀測性的分界

[Infra 模組六：可觀測性與 log](/devops/infra/06-observability-logging/) 處理基礎設施層的訊號 — log group、CloudWatch metric、alarm 跟資源同生命週期的 IaC 管理。本模組處理應用層的訊號 — 服務的延遲、錯誤率、trace、業務指標；自架環境的主機與容器資源監控（4.26 到 4.28）也放在本模組，因為它與應用層的訊號放在同一套 Prometheus 與同一份儀表板裡對照。分界的判讀是：這個訊號是「資源建立時就該存在」還是「功能開發時才埋」——前者進 infra 的 IaC，後者進本模組的應用程式碼。事故排查時兩層合流：infra alarm 告訴你哪個資源異常，本模組的 trace 告訴你哪個請求路徑受影響。
