---
title: "9.3 壓測工具選型"
date: 2026-05-12
description: "k6 / JMeter / Gatling / Locust / Vegeta / Production Replay 的工程選型"
weight: 3
tags: ["backend", "performance", "capacity", "tooling"]
---

## 概念定位

壓測工具選型的核心不是「哪個工具最強」、是「哪個工具最貼合本團隊的 workload model 表達能力跟 CI 整合需求」。沒有絕對最好的工具、只有最匹配當前場景的工具。

跟 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 的關係：9.2 定義 workload 長什麼樣、9.3 找能複製這個樣子的工具。工具選對、壓測結果可信；工具選錯、壓測結果誤導。

本章不是工具教學、是 *選型維度* + 主流工具的 *適用情境*。讀者讀完後能回答「我現在這個 workload 該用哪個工具」、而不是「哪個工具最快」。

## 六個選型維度

選工具時要按六個維度評估、不能只看「能不能跑 HTTP GET」。

**腳本表達能力**：能不能寫複雜 user journey（登入 → 瀏覽 → 加購物車 → 結帳）、不只是單一 HTTP request。複雜系統的壓測通常是 user journey 級別、單一 endpoint 壓測只能找絕對極限、找不到 cross-endpoint contention。

**協議支援**：HTTP / WebSocket / gRPC / TCP / 自家二進位協議。WebSocket 跟 gRPC 是現代後端常見、傳統工具（JMeter、wrk）可能要 plugin 補。

**規模能力**：單機可以發多少 RPS、能不能分散式擴容。本機 wrk 可發 10K-50K RPS；分散式 Locust 可發 1M+ RPS。決定因素：CPU 效率、async I/O 模型、是否單機 bound。

**CI 整合**：能不能在 PR 上跑 lightweight perf check、結果能不能機器可讀（JSON / Prometheus exposition）、能不能跟 baseline diff。沒有 CI 整合的工具只能做「事件型壓測」、無法做 continuous perf governance。

**結果分析**：原生 dashboard（k6 Cloud、Gatling Enterprise）/ Prometheus + Grafana 整合 / 純文字輸出。要看結果分發、團隊成員能不能輕鬆查詢歷史。

**學習曲線**：腳本語言（JavaScript / Scala / Python / Go）、團隊熟悉度。工具好但團隊不會用、會變成 1-2 個工程師的孤島技能、流失時整套廢掉。

## 主流開源工具對照

| 工具     | 腳本    | 規模 | 學習曲線 | 適用情境                                    |
| -------- | ------- | ---- | -------- | ------------------------------------------- |
| k6       | JS      | 中   | 低-中    | 複雜 user journey + CI 整合、現代工具首選   |
| JMeter   | XML/GUI | 中   | 中-高    | 企業已有流程、protocol 廣、reluctant 改     |
| Gatling  | Scala   | 高   | 高       | 報表精美、Scala 學習門檻                    |
| Locust   | Python  | 高   | 中       | 複雜邏輯、Python 生態、單機 throughput 受限 |
| Vegeta   | CLI     | 中   | 低       | CLI driven、quick HTTP 壓測                 |
| wrk/wrk2 | C       | 高   | 低       | 單機極限 RPS、saturation discovery 用       |

**k6** 是過去 5 年崛起的綜合首選。JavaScript 腳本（前端工程師也能寫）、原生 dashboard、Prometheus exposition、CI 友善。Grafana 收購後生態加速。缺點：複雜 stateful 場景（DB connection pool 共享）需要繞 workaround。

**JMeter** 是企業常見的 incumbent。協議支援廣（含 LDAP、JDBC、JMS）、有 GUI 編輯器。缺點：腳本是 XML、版本控制困難；GUI 主要用來生成腳本、實際跑壓測還是要 headless。已經在用的團隊建議繼續、新團隊不必特意選它。

**Gatling** 高 throughput 純 async、性能優秀、報表精美。缺點：Scala / Kotlin DSL 學習曲線陡、新版本（11+）改了 DSL 不向後相容。

**Locust** 是 Python 生態的選擇、特別適合複雜業務邏輯（用 Python 寫 user journey 自然）。分散式部署原生支援。缺點：Python 單線程 throughput 受限、要靠分散式擴容。

**Vegeta** 跟 **wrk** 是「quick check」工具、用於單一 endpoint 的極限測試。不適合複雜場景、適合 saturation discovery 第一輪「找這個服務的天花板」。

## Production traffic replay 工具

當需要複製 *真實 production traffic* 的壓測場景時、需要另一類工具。

**GoReplay** 是最常用的開源 traffic replay 工具。在 production server 上 tcpdump-based 捕獲 HTTP traffic、可以 store 到 file 或 stream 到 staging 環境。優點：開源、無 vendor lock-in；缺點：HTTP only、加密流量要拿到 key 才能用。

**Service mesh shadow（Istio / Linkerd mirror）**：mesh 層 mirror traffic 到 staging service。優點：mesh 已部署的話 zero infra cost、加密 traffic 也能 mirror。缺點：需要 service mesh 已落地。

**AWS VPC Traffic Mirroring**：底層網路層 mirror、application 完全無感。優點：最低 invasion；缺點：AWS only、加密 traffic 要另外處理。

**Diffy（Twitter / X 開源、已 deprecated 但概念仍有效）**：dual-write 同時打到舊 / 新版本、比對結果。適合驗證「新版本是否邏輯正確」、不是純壓測。

對應案例：[Tixcraft 10K t2.micro 壓測](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 用分散式 EC2 跑 synthetic load 模擬 100K 同時搶票；[SeatGeek Virtual Waiting Room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) — token 配發邏輯通常用 dual-write 驗證新舊版本一致。

## 雲端 managed 壓測服務

當不想養 load test infrastructure、想 ad-hoc 跑大規模壓測時、用 managed service。

**AWS Distributed Load Testing**：CloudFormation 起 Fargate cluster 跑 JMeter 或 Taurus、報表寫到 S3。優點：一鍵部署、Fargate 計費；缺點：JMeter-based、不是現代 k6 風格。

**Grafana k6 Cloud**：託管 k6、跨地理 distributed 壓測（從多個 region 同時發流量）。優點：地理分散原生、跟 Grafana 整合無縫；缺點：vendor cost。

**Azure Load Testing**：Azure 原生、整合 Application Insights。優點：Azure 用戶無縫；缺點：相對較新、生態還在補。

**GCP 沒有 first-party managed load testing**：要靠 Marketplace 方案或自管 Locust on GKE。

## 工具選型決策樹

落地時的快速決策：

- 想快速驗證單一 API 極限 → wrk / Vegeta
- 想寫複雜 user journey + CI 整合 + JavaScript 團隊 → **k6**（新項目首選）
- 企業已有 JMeter 流程、不想換 → JMeter（接受 XML / GUI 複雜度）
- 大規模分散式 + Python 生態 → Locust
- 報表給管理層看、Scala 團隊 → Gatling
- 想複製真實 production traffic → GoReplay 或 service mesh shadow
- 想 ad-hoc 雲端大規模壓測 → 對應雲商的 managed load test

## 常見反模式

- **只測單一 API、不測 user journey**：找不到 cross-endpoint contention、找不到 session state 累積
- **壓測機跟被測機在同一網段**：網路延遲被低估、p99 比 production 樂觀
- **壓測時 throttle 自己的工具**：結果不是被測系統的極限、是工具自己的極限
- **結果報表只看平均**：[tail latency](/backend/knowledge-cards/tail-latency/) 看不到、p99 退化被掩蓋
- **壓測環境跟 production hardware 不一致**：CPU 型號、network、disk IOPS 差很大、結果不可外推
- **沒驗證 model**：跑了壓測但沒對比 production metrics、不知道 model 是否貼近 reality

## 案例對照

| 案例                                                                                          | 教學重點                                       |
| --------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) | 10,000 台 t2.micro 跑分散式壓測（$130 / 小時） |
| [9.C25 Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)       | ML p99 < 10ms 壓測必須帶 latency distribution  |

## 下一步路由

- 上游：[9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)
- 下游：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)（用工具找 knee）
- 下游：[9.9 Improvement Loop](/backend/09-performance-capacity/improvement-loop/)（CI 整合）
- 跨模組：[06.1 CI Pipeline](/backend/06-reliability/ci-pipeline/)（壓測在 CI 的位置）
- 跨模組：[運維 模組五：壓力測試工具與方法](/operations/05-capacity-planning/load-testing-tools/)（k6 實跑、怎麼讀延遲分布的動手層）

## 既建知識卡片

- [Load Test](/backend/knowledge-cards/load-test/)
- [Workload Model](/backend/knowledge-cards/workload-model/)
- [Shadow Traffic](/backend/knowledge-cards/shadow-traffic/)
- [Saturation Point](/backend/knowledge-cards/saturation-point/)
