---
title: "4.9 Continuous Profiling"
date: 2026-06-22
description: "把 CPU / memory / lock profile 從一次性除錯升級為持續訊號"
weight: 9
tags: ["backend", "observability"]
---

## 大綱

- Continuous profiling 的定位：metrics / logs / traces 之外的第四角
- Profile 維度：CPU、heap、allocations、lock contention、goroutine / async task
- Always-on vs on-demand：何時用哪種
- Flame graph 與版本差異比較
- Overhead 控制
- Vendor 定位
- 反模式

## 概念定位

Continuous profiling 是把 CPU、memory、allocation 與 lock contention 變成長期可比較的 production 訊號，責任是補上 metrics、logs、traces 看不到的 callstack 成本。

Metrics 會告訴你「CPU usage 上升了」，trace 會告訴你「這條 request 的 latency 從 200ms 變成 800ms」，profile 會告訴你「增加的 600ms 花在哪幾個 function call、哪幾行程式碼」。Profile 是唯一能精確到 callstack level 的觀測訊號。

「Continuous」的關鍵差異是：傳統 profiling 是事故時才手動開啟，continuous profiling 是 production 常駐的低開銷採樣。事故時不需要重現問題 — baseline profile 已經在那裡，直接跟事故期間的 profile 做 diff。

## Profile 維度

不同的 profile 維度回答不同的效能問題。服務的退化模式決定需要哪些維度。

### CPU profile

回答「CPU 時間花在哪些 function」。最常用的 profile 維度。適合診斷 latency 退化（某個 function 開始佔更多 CPU 時間）跟 CPU 利用率異常（某段程式碼意外進入 hot path）。

CPU profile 用 sampling 方式採集 — 定期（例如每秒 100 次）記錄當前的 callstack。統計意義上，出現在 sample 中的次數跟實際 CPU 消耗成正比。Sampling 頻率越高精度越好，但 overhead 也越高。

### Heap / memory profile

回答「memory 被哪些 function 持有」。適合診斷 memory leak（allocation 持續增長、GC 回收不了）跟 GC pressure（大量短命物件導致 GC 頻繁）。

Heap profile 記錄的是某個時間點的 live object 分布。Allocation profile 記錄的是一段時間內誰做了多少 allocation — 兩者互補。Memory leak 用 heap profile 的時間趨勢看；GC pressure 用 allocation profile 看。

### Lock contention profile

回答「哪些 lock 的等待時間最長」。適合診斷 mutex contention（多個 thread / goroutine 搶同一把 lock、等待時間累積成 latency）。

Lock profile 在高並發服務的診斷中特別有用。Metrics 只能看到整體 latency 上升；trace 能看到某個 span 變慢；lock profile 能精確定位是哪把 lock 在哪個 callstack 被等待。

### Goroutine / async task profile

Go 的 goroutine profile 回答「有多少 goroutine、它們在做什麼（running / waiting / blocked）」。Goroutine leak（goroutine 數量持續增長、都在等待某個 channel 或 lock）是 Go 服務常見的退化模式。

其他語言有對應的概念：Java 的 thread dump、Node.js 的 async resource tracking、Python 的 asyncio task inspection。

## Always-on vs On-demand

### Always-on（continuous）

Production 常駐的低開銷 profiling。CPU sampling 頻率降低（每秒 19 或 100 次，避免跟系統 timer 共振），heap sampling 用語言 runtime 內建機制（Go 的 `runtime/pprof`、Java 的 JFR）。

Always-on 的核心價值是 baseline — 平時就有 profile 資料，事故時可以跟 baseline 做 diff，看「哪些 function 的 CPU 消耗跟平時不同」。沒有 baseline 的 profiling 只能看「現在的 profile 長什麼樣」，無法判斷哪些是異常的。

### On-demand

事故中或效能調查時手動開啟的高精度 profiling。Sampling 頻率更高、涵蓋更多維度、但 overhead 也更高（可能影響 production 服務的 latency）。

On-demand profiling 適合在 always-on profile 定位到可疑 function 後，做更細粒度的 callstack 分析。兩者搭配使用 — always-on 做日常監控跟 baseline，on-demand 做事故深挖。

### Overhead 控制

Continuous profiling 的可行性取決於 overhead 是否夠低。目標是 CPU overhead < 1%、memory overhead < 10MB。

影響 overhead 的因素：

- **Sampling 頻率**：CPU profile 每秒 100 次 vs 1000 次，overhead 差一個數量級
- **採集機制**：eBPF-based profiler（Parca、Pyroscope eBPF）在 kernel 層採集，overhead 比 language-level profiler 低；language runtime 內建機制（Go pprof、Java JFR）overhead 居中；instrumentation-based profiler overhead 最高
- **資料傳輸**：profile 資料定期傳到 backend 的網路跟序列化成本

Production 部署前要用 benchmark 驗證 overhead。在 load test 環境開啟 profiling、比較開啟前後的 latency p99 跟 CPU usage — 差異超過 1% 要調整 sampling 頻率或換更輕量的 profiler。

## Flame Graph 與版本差異比較

### Flame graph

Flame graph 是 profile 資料的標準視覺化。X 軸是 callstack 的寬度（代表 sample 佔比 = 資源消耗佔比），Y 軸是 callstack 深度（底部是 root function、頂部是 leaf function）。寬的矩形代表消耗多、窄的代表消耗少。

讀 flame graph 的方式是「從寬的開始看」— 最寬的矩形是當前最大的資源消耗者。如果某個 function 佔整個 flame graph 的 40%，它就是最值得最佳化的候選。

### Diff flame graph

Diff flame graph 是兩個 profile 的差異視覺化。紅色代表新版本消耗增加、綠色代表減少。適合用在：

- **版本間比較**：v1.2.3 vs v1.2.4 的 CPU profile diff，看新版本哪些 function 變慢
- **Canary 對照**：canary instance vs baseline instance 的即時 diff
- **事故 vs baseline**：事故期間的 profile vs 平時的 profile

Diff flame graph 需要 profile 帶 version / deploy label。Profile 跟版本標記失聯時，跨版本比較只能靠手動對照時間範圍 — 精確度跟效率都會下降。

## Vendor 定位

| Vendor           | 採集機制            | 語言支援               | 定位                         |
| ---------------- | ------------------- | ---------------------- | ---------------------------- |
| Pyroscope        | SDK + eBPF          | Go, Java, Python, Ruby | 開源自架，Grafana 生態整合   |
| Parca            | eBPF                | 語言無關（kernel 級）  | 開源自架，零 instrumentation |
| Datadog Profiler | Agent + SDK         | Go, Java, Python, .NET | 託管，跟 APM trace 整合      |
| Polar Signals    | eBPF（Parca Cloud） | 語言無關               | 託管 Parca                   |

選擇要點：如果已有 Grafana 生態（Prometheus + Loki + Tempo），Pyroscope 整合最自然。如果不想改 application code（零 instrumentation），eBPF-based 的 Parca 是選項。如果已用 Datadog APM，Datadog Profiler 跟 trace 的整合（從 trace span 跳到對應的 profile）是獨有優勢。

## 核心判讀

Continuous profiling 的持續價值取決於兩件事：profile 能否按版本做 diff（沒有 baseline 就無法判斷哪些 callstack 是異常的），以及 overhead 能否低到 production 常駐（overhead 過高等於回到「事故時才開」的模式）。

重點訊號包括：

- Profile 是否帶有 service、version、environment 與 deploy label
- Flame graph diff 是否能對照 canary / baseline
- CPU、heap、lock、allocation 是否覆蓋主要退化模式
- Production sampling 是否足夠低成本且常駐穩定

## 判讀訊號

- 同一段熱點程式碼反覆出現在事故 RCA 中、無 baseline profile
- CPU / memory 異常時靠重現除錯、無 production profile 可對照
- 版本升級後 latency 退化、定位具體 callstack 需要重現環境
- Profile 跟 commit / version label 失聯、跨版本 diff 需要人工對照
- Profiling overhead 過高、production 環境常駐成本過高

## 反模式

| 反模式                       | 表面現象                                    | 修正方向                                        |
| ---------------------------- | ------------------------------------------- | ----------------------------------------------- |
| Profiling 只在事故時才開     | 事故時開 profiler 需要時間、問題可能已消失  | Always-on continuous profiling                  |
| Production sampling rate = 0 | Profile 只存在於 staging、production 沒資料 | 調低 sampling 頻率到 overhead < 1%              |
| Profile 跟 version 失聯      | Diff 只能靠時間範圍猜、無法精確比較         | Profile metadata 帶 version / commit hash label |
| 只看 CPU profile             | Memory leak 跟 lock contention 被忽略       | 按服務退化模式選擇 profile 維度                 |
| Profile 資料沒有保留策略     | 儲存持續成長、舊 profile 佔空間但沒被查     | 依版本保留（每版本保留 N 天）                   |

## 交接路由

- [4.2 metrics](/backend/04-observability/metrics-basics/)：metrics 是聚合訊號、profile 是 callstack 級別
- [4.3 tracing](/backend/04-observability/tracing-context/)：trace 是 request 維度、profile 是 process 維度
- [4.7 cardinality / cost](/backend/04-observability/cardinality-cost-governance/)：profile 儲存量與保留策略
- [4.21 rule-level CPU signal](/backend/04-observability/rule-level-cpu-signal-governance/)：規則執行成本的 CPU 訊號治理
- [8.5 post-incident review](/backend/knowledge-cards/post-incident-review/)：RCA 引用 profile flame graph
