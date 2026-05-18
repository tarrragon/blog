---
title: "Vegeta"
date: 2026-05-15
description: "用簡潔 CLI 與固定 rate HTTP attack 快速探測 latency、throughput 與 saturation 的效能工程工具"
weight: 5
tags: ["backend", "performance", "capacity", "vendor", "vegeta", "load-test"]
---

Vegeta 的核心責任是用簡潔 CLI 對 HTTP endpoint 產生固定 rate 負載，快速探測 latency、throughput、error rate 與 saturation。它適合單一 endpoint、少量 header / body 變化、快速 baseline、incident 後驗證與工程師本機或 CI 中的輕量壓測。

## 服務定位

Vegeta 是 Go 寫的 HTTP load testing CLI，核心模型是 *constant rate attack*：指定「每秒 N 個 request」就持續打 N rps、不會因 server 變慢就降速，跟「fire-and-wait」型工具（hey / wrk 預設 closed-loop）行為差異很大。constant rate 是 *open-loop* 模型 — 模擬真實流量「不會因服務慢而減少」的行為、所以 saturation 點才會明確浮現。

Vegeta 是 Unix philosophy CLI：targets 從 stdin 讀（可以 pipe 進複雜 generator）、binary report 從 stdout 出（可以 pipe 進 `vegeta report` / `vegeta plot` / `vegeta encode`）。這個設計讓 Vegeta 容易跟 shell pipeline / CI script 接合、但同時也決定它不適合表達多步驟 session。

跟 [k6](/backend/09-performance-capacity/vendors/k6/) 比、Vegeta 走 *CLI-first + open-loop constant rate*、k6 走 *JS scenario + threshold + CI artifact*。Vegeta 適合「我要對這個 URL 打 200 rps 60 秒」的一次性壓測、k6 適合「我有 3 種 user journey、各占 40/30/30%、跑 ramp-up profile」的可維護 scenario。跟 hey 比、Vegeta 的 constant rate 是真的 open-loop、hey 的 `-q` 是 per-worker rate（worker 變慢整體就降速）— 探測 saturation 時 Vegeta 比較誠實。跟 wrk / wrk2 比、Vegeta 沒有 LuaJIT 那麼極致的單機壓測效能、但 binary report + `vegeta plot` + targets pipe 對日常工程師工作流更友善。

## 本章目標

讀完本頁、讀者能判斷：

1. 何時用 Vegeta、何時走 k6 / hey / wrk / Gatling / Locust 的取捨
2. constant rate attack 的設計意涵（open-loop vs closed-loop、為什麼這對 saturation discovery 重要）
3. target file / rate / duration / report 四件套的 baseline workflow 跟 evidence package 對應
4. 排錯時的常見陷阱：runner 端 TCP socket exhaust、open file limit、constant rate 跟 target server 限速 disconnect

## 定位

Vegeta 適合快速回答「這個 endpoint 在某個 rate 下表現如何」。當團隊需要先找出大概 knee point、驗證一個修補是否降低 latency、或在 CI 裡跑小型 performance smoke test，Vegeta 的 CLI workflow 很直接。

這個定位讓 Vegeta 接到 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 與 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)。它提供的是快速壓力探針，後續若要表達複雜 workload model，通常要轉向 k6、Gatling、Locust 或 JMeter。

## 最短判讀路徑

判斷一次 Vegeta 壓測是否有效、最少看四件事：

- **Target 描述完整性**：targets file 是否包含 method / URL / headers / body、是否反映真實 request shape（含 auth header、content-type、representative payload size），缺一就會讓壓測結果偏離正式環境
- **Rate model 設計**：選的是 constant rate（`-rate=200/s`）還是 ramp（用多段 attack pipe），constant rate 適合 saturation probe、ramp-up 要 wrap script 自己 stage、Vegeta 沒有原生 ramp profile
- **Report 解讀**：`vegeta report` 給 mean / p50 / p95 / p99 / max latency + success rate + throughput，重點看 *p99 跟 max 的距離* 與 *requested rate vs actual throughput* 是否 disconnect — disconnect 表示 server / runner 端有人在限速
- **Duration vs warm-up**：短 duration（< 30s）容易吃到 JIT / cache / connection pool warm-up 噪音，baseline 壓測 duration 至少 60s、且第一段 result 要 discard，否則 p99 會被前 5s 拉高

## 適用場景

單 endpoint saturation probe 是 Vegeta 的主要入口。工程師可以對 login、search、read API、feature flag endpoint 或 internal health-like endpoint 施加固定 rate，觀察 p95 / p99 與 error rate 何時開始上升。

Regression smoke test 適合用 Vegeta。CI 或 pre-release 可以用短時間固定 rate 測試，確認 hot path 沒有明顯退化，再把更完整的 scenario 交給 k6、Gatling 或 Locust。

Incident 後修補驗證適合用 Vegeta。當事故根因是某個 endpoint 的 query、cache miss、lock contention 或 timeout，修補後可以用相同 request set 重跑，快速比較 latency distribution。

## 選型判準

| 判準       | Vegeta 的價值                   | 需要補的能力                        |
| ---------- | ------------------------------- | ----------------------------------- |
| CLI 簡潔   | 本機、CI、shell workflow 容易接 | 長期報表與 artifact 標準化          |
| 固定 rate  | 探測 rate / latency 關係清楚    | 複雜使用者行為與 arrival pattern    |
| HTTP 導向  | API hot path 快速驗證           | 非 HTTP protocol 與 multi-step flow |
| 快速 probe | 適合 smoke test 與修補驗證      | 完整 workload model 與資料治理      |

CLI 簡潔價值來自低摩擦。當問題還在定位階段，工程師可以很快產生可重跑 command 與 target file，先取得 baseline，再決定是否需要完整壓測平台。

固定 rate 價值來自可比較。用相同 request set、rate、duration 與 target environment 重跑，可以讓修補前後的 latency distribution 有清楚對照。

## 跟其他工具的取捨

Vegeta 和 k6 的主要差異是 scenario 深度。Vegeta 適合固定 rate HTTP probe；k6 適合多步驟 scenario、threshold、CI artifact 與 browser-style flow。

Vegeta 和 JMeter 的主要差異是工具重量。Vegeta 適合快速 CLI；JMeter 適合 GUI、多 protocol、plugin 與企業測試資產。

Vegeta 和 Gatling 的主要差異是長期維護模式。Vegeta 用 command / target file 保持簡單；Gatling 用 simulation 維護複雜 flow 與 injection profile。

Vegeta 和 Locust 的主要差異是自訂能力。Locust 適合 Python user behavior 與 custom client；Vegeta 適合 HTTP endpoint 的直接壓力測量。

## 操作成本

Vegeta 的主要成本是 workload coverage 有限。它能快速測 endpoint，但多步驟 session、資料依賴、payment mock、queue side effect 與 realistic user journey 需要額外工具或腳本補上。

Artifact 成本來自命令可追溯性。每次測試要保存 rate、duration、targets、headers、body、環境、版本與結果檔；否則快速 probe 很容易變成不可比較的一次性觀察。

Runner 成本通常較低，但仍要檢查本機瓶頸。高 rate 測試時，產生負載的機器也可能先被 CPU、network、file descriptor 或 connection limit 卡住。

## Evidence Package

Vegeta 結果應回寫到 evidence package。最小欄位包括 command、target file hash、rate、duration、workers、target environment、p95 / p99、max latency、error rate、throughput、target saturation metric、known gap 與 owner。

| 欄位         | Vegeta 證據來源                                 |
| ------------ | ----------------------------------------------- |
| Source       | command、targets file、binary result、report    |
| Time range   | test start / end                                |
| Query link   | APM / metrics / logs 查詢連結                   |
| Data quality | target set freshness、header / body correctness |
| Confidence   | runner capacity、endpoint representativeness    |
| Known gap    | 未覆蓋多步驟 flow、資料偏差、runner limit       |

Evidence package 的核心用途是讓快速測試可以比較。Vegeta 的結果通常很短，反而更需要保存 command 與 target set，讓下一次修補驗證能跑同一組條件。

## 核心取捨表

| 取捨維度      | Vegeta                                         | k6                                                | hey                                 | wrk / wrk2                           |
| ------------- | ---------------------------------------------- | ------------------------------------------------- | ----------------------------------- | ------------------------------------ |
| 負載模型      | Open-loop constant rate（rps 不隨 latency 降） | Open-loop（k6 default）/ closed-loop（VU mode）   | Per-worker rate（closed-loop 傾向） | wrk closed-loop / wrk2 open-loop     |
| Scenario 深度 | 單 endpoint pipe target、多 endpoint 需 script | JS script、多步驟、staging / threshold / SLO 內建 | 單一 URL CLI flag                   | Lua script 可寫複雜邏輯但 idiom 較陡 |
| 輸出形式      | Binary stream + `vegeta report/plot/encode`    | stdout summary + JSON + 內建 dashboard            | stdout 文字 summary                 | stdout 文字 summary、HdrHistogram    |
| CI 整合       | 用 shell 包、自寫 threshold gate               | 內建 threshold / exit code、CI artifact 標準化    | 簡單 smoke、無 threshold            | 需自寫 wrapper                       |
| 學習成本      | 低 — 幾個 flag 就上手                          | 中 — 要寫 JS scenario                             | 極低 — 一行 CLI                     | 中 — Lua 加 HdrHistogram 概念        |
| 適合場景      | 修補驗證、CI smoke、saturation probe           | 完整壓測平台、SLO gate、多 scenario               | 一次性 ad-hoc 探測                  | 極致單機壓測效能、低 overhead 量測   |

選 Vegeta 的核心訴求：*工程師本機 / CI smoke / 修補驗證 / saturation probe* 都要快速可重跑、且結果要可以保存比較；不需要完整 scenario 模型也不需要 GUI 報表。若團隊需要完整 user journey、threshold / SLO gate、長期 trend dashboard，直接走 [k6](/backend/09-performance-capacity/vendors/k6/) 或 [Gatling](/backend/09-performance-capacity/vendors/gatling/)。

## 進階主題

**Reporting 多輸出 format**：`vegeta report` 預設 text summary、加 `-type=hist[0,10ms,50ms,100ms,500ms]` 給 latency bucket histogram、`-type=json` 給機器可讀 result、`vegeta plot` 出 HTML latency chart、`vegeta encode -to=csv` 轉成可進 spreadsheet / dashboard 的 CSV。binary result 檔可重複 decode 成不同 format，不用重跑壓測。修補驗證的標準作法是保留 `results.bin`、之後可隨時 re-render report。

**Pipe attack workflow**：Vegeta 的 stdin/stdout 都是 stream — 可以用 shell pipe 串接 `jq` 動態產 targets（`jq -r '.urls[] | "GET " + .'`）、用 `vegeta attack | tee results.bin | vegeta report` 同時寫檔跟即時看 summary、用 `cat results-old.bin results-new.bin | vegeta report` 比較兩次結果。這個設計讓 Vegeta 跟 incident drill / chaos test script 容易接合 — 修補 deploy 完跑一次 attack、result 直接 commit 進 git 當 evidence。

**CI integration pattern**：CI 裡 Vegeta 沒有 k6 那種內建 threshold，要自寫 gate — `vegeta report -type=json results.bin | jq '.latencies.p99'` 出 p99、bash 比較 budget、超標 exit 非零。把 `targets.txt` + `attack.sh` + `expected-budget.json` commit 進 repo、CI artifact 上傳 `results.bin` + `plot.html`，下次 regression 時可以 diff。

## 排錯與失敗快速判讀

- **Requested rate 跟 actual throughput disconnect（要 200rps 實際只跑 80rps）**：runner 端先飽和、不是 server 飽和 — 看 `vegeta attack` stderr 是否報 `socket: too many open files`、檢查 `ulimit -n`（生產壓測 runner 至少設 65535）；或 server 端有限速 / rate limit / connection cap 把 request reject 在 TCP 層、Vegeta 看不到完整 response 就被卡
- **TCP socket exhaust（runner 端）**：constant rate 模型下、若 server 回應慢、connection 會堆積、`TIME_WAIT` socket 爆 ephemeral port range — 用 `-keepalive=true`（預設）並調 `net.ipv4.tcp_tw_reuse=1`、或加 `-connections=N` 限制 connection pool 上限避免無限堆 socket
- **p99 / max latency 異常高、但 server-side metrics 看不到**：runner 端 GC pause / CPU steal / network jitter 把 latency 量測污染 — 把 runner 移到跟 target 同 placement group / same AZ、確認 runner CPU 沒被其他 process 搶、duration 拉長到 5min 讓 outlier 變稀釋
- **Success rate 100% 但 server 已經爆**：targets 沒帶 auth header / 打到 LB 而非 backend、所有 request 在前面就 200 / cache hit、server 根本沒收到壓力 — 檢查 target server access log 的 request count 跟 Vegeta requested rate 是否對得上
- **短時間壓測結果不穩定（同 command 跑兩次差很多）**：duration 太短（< 30s）、warm-up 噪音占比太高 — 至少 60s、第一段 5-10s discard、若 endpoint 有 lazy initialization（cache / connection pool / JIT compile）先跑一段 warm-up attack 再正式量

## 案例回寫

Vegeta 適合回寫單 endpoint hot path 與修補驗證案例。它可接 [9.C3 Coinbase ultra-low latency](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) 的 sub-millisecond latency distribution 判讀、[9.C25 Tubi feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) 的 p99 < 10ms lookup 驗證、[9.C29 Lemino connection limit](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 的 RDB bottleneck 探測、[9.C6 Tinder ElastiCache](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/) 的次毫秒 cache lookup 驗證，以及 [9.C5 Amazon Ads DynamoDB](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) 的 hot partition 探測。

這些案例的重點是快速定位與比較。Vegeta 頁引用案例時，要把 case 轉成 endpoint、rate、duration、latency budget、target saturation metric 與 runner limit — 例如 Coinbase 的 sub-ms 目標要求 Vegeta runner 必須跟 target 同 placement group、否則 runner 自身的網路 jitter 會吃掉觀測精度。

## 下一步路由

- 上游：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)
- 上游：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 平行：[k6](/backend/09-performance-capacity/vendors/k6/)、[Gatling](/backend/09-performance-capacity/vendors/gatling/)、[Locust](/backend/09-performance-capacity/vendors/locust/)
- 跨模組：[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)
- 官方：[Vegeta documentation](https://github.com/tsenart/vegeta)
