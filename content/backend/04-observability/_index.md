---
title: "模組四：可觀測性平台"
date: 2026-04-22
description: "整理 log、metric、trace、dashboard 與 alert 的後端操作實務"
weight: 4
---

可觀測性模組的核心目標是說明服務如何把 [log schema](/backend/knowledge-cards/log-schema/)、[metrics](/backend/knowledge-cards/metrics/) 與 [trace context](/backend/knowledge-cards/trace-context/) 轉成可操作的診斷系統。語言教材會處理標準 logger、執行環境訊號、[Diagnostic Endpoint](/backend/knowledge-cards/diagnostic-endpoint/) 與 [trace context](/backend/knowledge-cards/trace-context/) 邊界；本模組負責平台、資料流與操作規則。

## Vendor / Platform 清單

實作時的常用選擇見 [vendors](/backend/04-observability/vendors/) — T1 收錄 OpenTelemetry / Prometheus / Grafana Stack / Datadog / Elastic Stack / Honeycomb / AWS CloudWatch / GCP Cloud Operations / Sentry，每個 vendor 有定位、適用場景、取捨與預計實作話題的骨架。Error tracking 是獨立子維度（Sentry），跟 metrics / logs / traces 三角互補。

進入 vendor 比較前，先回到 [觀測、可靠性與事故服務選型](/backend/00-service-selection/operations-control-service-selection/) 判斷目前缺的是訊號層、驗證層、響應層還是閉環層。可觀測性 vendor 選型只處理訊號層與部分告警入口；可靠性驗證與事故協作要交給可靠性與事故流程。

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
- **事故 → 觀測**：每次事故 [post-incident review](/backend/knowledge-cards/post-incident-review/) 揭露偵測缺口（symptom-based alert 缺、訊號太晚、cardinality 不足），回寫到訊號治理。
- **資安 → 觀測**：資安偵測、稽核證據與資料外洩風險會形成新的 log schema、audit log、alert 與 evidence chain 需求。尤其 [偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/) 會回寫到訊號治理閉環。
- **觀測 → 資安**：log、trace、audit log 與 service topology 提供資安 triage 的事實基礎，讓 [稽核追蹤與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/) 能把責任鏈落到可查證資料。
- **詳細閉環說明**：見 [Observability / Reliability / Incident Response 閉環](/backend/08-incident-response/observability-reliability-incident-loop/)。

## 與語言教材的分工

語言教材處理如何產生穩定欄位與執行環境訊號。Backend observability 模組處理收集、儲存、查詢、視覺化、告警與跨服務關聯。

## 跨語言適配評估

可觀測性使用方式會受語言的 logger 生態、[trace context](/backend/knowledge-cards/trace-context/)、exception/error model、執行環境 metrics 與 instrumentation SDK 影響。同步 runtime 要保留 request context 與 thread-local 邊界；async runtime 要確認 [trace context](/backend/knowledge-cards/trace-context/) 能跨 task 傳遞；輕量並發 runtime 要觀察 task/goroutine 數量、queue lag 與下游等待。動態語言要特別管理 log schema 穩定性；強型別語言則要避免過度包裝導致 trace 與 error chain 斷裂。

## 章節列表

| 章節                                                                | 主題                                 | 關鍵收穫                                                                                       |
| ------------------------------------------------------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------- |
| [4.1](/backend/04-observability/log-schema/)                        | log schema 與搜尋規劃                | 設計欄位、索引與查詢方式                                                                       |
| [4.2](/backend/04-observability/metrics-basics/)                    | metrics 與 SLI/SLO                   | 用 counter、gauge、histogram 描述服務健康                                                      |
| [4.3](/backend/04-observability/tracing-context/)                   | tracing 與 context link              | 追蹤跨服務 request path                                                                        |
| [4.4](/backend/04-observability/dashboard-alert/)                   | dashboard 與 alert 設計              | 讓告警能對應 runbook 與容量趨勢                                                                |
| [4.5](/backend/04-observability/attacker-view-observability-risks/) | 攻擊者視角（紅隊）：可觀測性弱點判讀 | 用盲區、告警失真與資料暴露風險檢查觀測系統                                                     |
| [4.6](/backend/04-observability/sli-slo-signal/)                    | SLI 量測與 SLO 訊號設計              | 把可靠性目標轉成可量測訊號、餵給 6.6 SLO 政策                                                  |
| [4.7](/backend/04-observability/cardinality-cost-governance/)       | Cardinality 治理與成本邊界           | 把 cardinality 與保留階梯作為平台一級治理                                                      |
| [4.8](/backend/04-observability/signal-governance-loop/)            | 訊號治理閉環                         | 把 [post-incident review](/backend/knowledge-cards/post-incident-review/) 偵測缺口回寫成新訊號 |
| [4.9](/backend/04-observability/continuous-profiling/)              | Continuous Profiling                 | 把 CPU / heap / lock profile 升級為持續訊號                                                    |
| [4.10](/backend/04-observability/client-side-monitoring/)           | Client-side / Synthetic / RUM        | 補 server-side 看不到的 user perceived 訊號                                                    |
| [4.11](/backend/04-observability/telemetry-pipeline/)               | Telemetry Pipeline 架構              | 把採集到查詢分層治理、定位 pipeline 失敗                                                       |
| [4.12](/backend/04-observability/audit-log-governance/)             | Audit Log 邊界與 PII 治理            | 把稽核訊號從 operational log 拆出、按法規治理                                                  |
| [4.13](/backend/04-observability/service-topology/)                 | Service Topology 與 Dependency Map   | 把跨服務依賴變成自動發現的觀測訊號                                                             |
| [4.14](/backend/04-observability/anomaly-detection/)                | Anomaly Detection                    | ML / statistical baseline alert 跟 rule-based 整合                                             |
| [4.15](/backend/04-observability/cost-attribution/)                 | Cost Attribution / Chargeback        | 把 observability 成本拆到團隊 / 服務維度                                                       |
| [4.16](/backend/04-observability/observability-readiness-review/)   | Observability Readiness Review       | 在服務上線、重大變更與演練前檢查 log / metric / trace / alert 是否可支援事故判讀               |
| [4.17](/backend/04-observability/telemetry-data-quality/)           | Telemetry Data Quality               | 把 missing signal、schema drift、sampling bias 與 timestamp skew 變成資料品質問題              |
| [4.18](/backend/04-observability/observability-operating-model/)    | Observability Operating Model        | 定義 platform / service team / on-call 對訊號、dashboard、alert 與成本的 ownership             |
| [4.19](/backend/04-observability/debuggability-by-design/)          | Debuggability by Design              | 把可診斷性前移到 API、async workflow、dependency call 與錯誤模型設計                           |
| [4.20](/backend/04-observability/observability-evidence-package/)   | Observability Evidence Package       | 把 log、metric、trace、audit 與資料品質限制包成可交接證據                                      |

> 註：4.6-4.15 目前為訊號治理與平台能力骨架、案例引用待後續迭代補上；4.16-4.19 是本輪優先完成的個案前控制面，負責支援 06 可靠性驗證與 08 事故處理後續章節。

## 個案前拓展空間

個案前拓展的責任是補足讀案例時需要的判讀框架。04 適合補「訊號是否足以支援判讀」這類跨服務能力，不適合展開單一服務的事故史。

| 拓展方向                       | 補充理由                                       | 先放位置 |
| ------------------------------ | ---------------------------------------------- | -------- |
| Observability Readiness Review | 服務上線前需要先知道訊號是否支援事故分級與驗證 | 4.16     |
| Telemetry Data Quality         | 觀測資料本身也會缺漏、漂移、偏誤與時間錯位     | 4.17     |
| Observability Operating Model  | dashboard、alert、成本與淘汰需要明確 owner     | 4.18     |
| Debuggability by Design        | 診斷能力需要進入 API / async / dependency 設計 | 4.19     |

本輪先完成這四個前置控制面，讓後續 06 與 08 文章有穩定的訊號前提可引用。若服務案例暴露的是訊號分類問題，回寫 4.16；若暴露的是資料品質問題，回寫 4.17；若暴露的是 owner 與治理問題，回寫 4.18；若暴露的是架構本身難以診斷，回寫 4.19。

## 下一輪撰寫順序

04 後續撰寫順序以「先補前提、再補驗證、最後補事故入口」為主。可觀測性是 06 與 08 的輸入層，因此本模組先把 readiness、data quality、operating model 與 debuggability 寫成可引用章節，再讓可靠性與事故模組承接。

| 順序 | 章節                                                                                             | 交付責任                                              | 下游路由                                             |
| ---- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------- | ---------------------------------------------------- |
| 1    | [4.16 Observability Readiness Review](/backend/04-observability/observability-readiness-review/) | 定義上線、變更與演練前的訊號準備度                    | 06.19 reliability readiness、08.18 intake            |
| 2    | [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)                 | 定義 completeness、freshness、drift 與 sampling 限制  | 06.6 SLO、08.19 decision log                         |
| 3    | [4.18 Observability Operating Model](/backend/04-observability/observability-operating-model/)   | 定義 dashboard、alert、schema、成本與 owner           | 08.2 command roles、08.16 runbook lifecycle          |
| 4    | [4.19 Debuggability by Design](/backend/04-observability/debuggability-by-design/)               | 定義 API、async、dependency 與 error model 的診斷欄位 | 06.10 contract testing、08.18 evidence triage        |
| 5    | [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) | 把可觀測資料包成可交給 06 / 08 的證據包               | 6.23 verification evidence、8.22 evidence write-back |

完成條件是每篇都能回答四件事：判讀訊號、風險代價、控制面邊界與下一步路由。這樣 06 的 SLO / readiness / experiment safety 與 08 的 intake / decision log / impact assessment 才能引用 04，而不需要在各自章節重寫觀測前提。
