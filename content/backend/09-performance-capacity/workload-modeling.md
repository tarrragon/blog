---
title: "9.2 Workload Modeling"
date: 2026-05-12
description: "把 production traffic shape 翻成可重播的壓測模型"
weight: 2
tags: ["backend", "performance", "capacity", "workload"]
---

## 概念定位

Workload modeling 的角色是讓壓測結果有意義。如果壓測模型跟 production traffic shape 不一致、壓測通過不代表 production 撐得住。這一層的工作不是「製造大量請求」、而是「製造跟 production 一樣形狀的請求」。

跟 [9.1 壓測理論](/backend/09-performance-capacity/performance-theory/) 的關係：9.1 提供推導工具、9.2 把工具的輸入（流量參數）量化。沒有 workload model、Little's Law 的 λ 跟 W 都是猜。

本章的核心問題：production traffic 不是「N RPS」這麼簡單。它有時間分布、地理分布、操作分布、cohort 分布、burst pattern。每個維度都會影響系統行為。一個只測「總 RPS」的壓測通過了、production 還是可能因為某個 cohort 集中或某個 burst pattern 出事。

## Traffic shape 的五個維度

Production traffic shape 至少要量五個維度才算 model 完整。

**平均吞吐 vs 峰值**：peak/avg ratio 是工程意義最大的單一指標。1.5x 的 peak/avg 代表流量相對平緩、容量規劃可以接近 average peak；3-5x 的 peak/avg 代表 bursty 流量、必須按 peak 規劃、平日大幅 over-provision。對應案例：[ASOS Black Friday 24h 1.67 億 / 峰值 3500 RPS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) 峰均比約 1.81x 屬於相對溫和；[Tixcraft 5 分鐘賣完](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 是另一極端。

**時間分布**：日內（早晚通勤）、週內（週末活躍）、月內（月初發薪）、季內（節慶）、年內（活動）。不同尺度的週期都要記錄、用於 forecast 跟 pre-scaling 決策。

**用戶分布**：geographic（哪個 region 多）、device（mobile vs desktop）、tier（free / paid / VIP）。同樣 RPS、不同分布可能造成完全不同系統行為 — VIP 用戶可能跑更複雜 query、mobile 用戶可能更多 retry、跨 region 用戶可能更多 cross-zone latency。

**操作分布**：read vs write 比、不同 endpoint 的 mix。一個系統 90% read 跟 50% read 的容量設計完全不同 — read-heavy 可以 cache、write-heavy 必須關注 storage IOPS。

**Cohort 與 burst pattern**：同一秒的請求不一定均勻 — bursty arrival 比 Poisson arrival 對系統更殘酷。突發 burst 來源：promo 推播、KOL 推廣、新片發布、新聞事件。

對應案例：[GR8 Tech 賽事高潮 burst](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) — 賽事「進球瞬間」 burst 比平均流量高 10-50 倍；[Disney+ 新片發布](/backend/09-performance-capacity/cases/disney-plus-content-metadata/) — 同片瞬間集中、cohort 高度集中。

## 從 production log 抽 workload model

實務上 workload model 不能憑空寫、要從 production data 抽。流程通常分四步：

**第一步：data 蒐集**。從 access log、APM trace、metric 系統取得 production traffic 樣本。要 sampling（不是全量）、避免影響 production；要包含 *至少一個完整 weekly cycle*（含週末、含峰谷）；要按 endpoint / per-tenant 分組。

**第二步：分組統計**。對每組（per endpoint、per tier、per region）計算 percentile（p50 / p95 / p99）、arrival pattern（Poisson、bursty、scheduled）、payload size 分布。輸出是「workload profile」 — 比單一數字更接近 reality。

**第三步：序列重播**。複製一段 production traffic 的時間序列、保留 inter-arrival timing（不只是 RPS 平均、是 *每秒幾個*）。這層讓 burst 在壓測重現、不只是「平均壓力均勻分布」。

**第四步：脫敏處理**。PII（user_id、phone、address）必須匿名化或替換 — 否則壓測環境變成 PII 洩漏點。常見做法：hash + salt + 確保結果 cardinality 跟 production 一致。

production log 通常缺寫入 payload（log 只記 metadata、不記 request body）、要從 application metric 或 schema sample 補。schema sample 用「distinct value 抽樣」、不是「random」 — 確保壓測涵蓋常見 value pattern。

## Synthetic load vs production replay

兩種主要壓測方式各有取捨。

**Synthetic load**：手寫腳本、明確控制每個請求的 shape。優點是好複現、可以針對特定情境設計（例如「測登入失敗 retry」）；缺點是容易脫離 production reality、寫腳本的人會無意識套用自己的偏見。

**Production traffic replay**：用 GoReplay、Istio mirror、AWS VPC Traffic Mirroring 等工具把 production traffic 複製到測試環境。優點是 *最貼近真實*、自動帶上 burst 跟 cohort；缺點是消耗 production 下游資源（要算進容量規劃）、PII / 合規處理複雜、replay 環境的下游 mock 不容易做。

**混合模式**：常態壓測用 synthetic（cheap、可控）、release candidate 驗證用 production replay（真實）、debug 特定 incident 用 *特定時段* 的 replay。三種工具在不同階段用、不是二選一。

對應案例：[FanDuel 雙峰需要兩個 workload model 並行](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) — 直播 model（CDN heavy、長 session）跟投注 model（低延遲、burst at goal）必須分開壓測、不能合成一個。

詳見 [Workload Model 卡片](/backend/knowledge-cards/workload-model/) 跟 [Shadow Traffic 卡片](/backend/knowledge-cards/shadow-traffic/)。

## 模型驗證：怎麼知道模型像 production

寫了 workload model 之後、怎麼驗證它真的「像 production」？方法是 *跑壓測 同時 對比 production metrics*。

驗證指標包含：throughput pattern（總 RPS、各 endpoint mix）、latency 分布（p50 / p95 / p99 對比）、resource utilization（CPU / memory / network 行為）、error rate 與 retry pattern。

兩個可能的偏差結果：

- **模型撐不住但 production 撐得住** → 模型太苛刻、可能高估了流量或操作複雜度。usually fine、調整模型參數即可。
- **模型撐得住但 production 撐不住** → 模型不足、漏了某個維度。dangerous、需要回到 data 蒐集階段找漏掉的 pattern。

對應案例：[Zoom 30x COVID surge](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) — 之前的 workload model 完全不能用、必須 reset baseline 重新從 post-COVID 流量抽 model；[Tixcraft 10K t2.micro 壓測](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 用實際售票場景重播驗證、不是 synthetic 數字。

## 模型維護：定期 review

Workload model 不是一次抽完就永久有效。業務變化會讓模型過時、過時的模型導出的容量規劃會失準。

需要 re-抽 model 的訊號：

- 新功能上線改變 user journey（例如新增 video upload、user 行為變寫多）
- 新市場進入改變 cohort 分布（例如進入印度市場、mobile share 大幅增加）
- 行銷活動改變 burst pattern（例如新增 push notification、burst 集中度上升）
- 用戶習慣轉變（例如 work-from-home 讓週末跟平日流量比變化）

維護節奏建議每季 review 一次、重大產品改動立即 re-抽。每次 re-抽要 *跟前一版對比*、量化變化幅度、決定哪些容量計畫要重新評估。

## 案例對照

| 案例                                                                                           | 教學重點                                     |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------- |
| [9.C21 ASOS Black Friday](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) | 持續高峰型 workload（峰均比 1.81x）          |
| [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)  | flash-sale 形狀（5 分鐘賣完）                |
| [9.C7 Lyft](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/)            | 100+ 微服務各自 workload model（不能用單一） |
| [9.C26 PayPay](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/)        | 3 億 / 天的峰均比預估                        |
| [9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/)   | 雙峰必須兩個 model 並行                      |

## 下一步路由

- 上游：[9.1 壓測理論](/backend/09-performance-capacity/performance-theory/)
- 下游：[9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)（用什麼工具實作 model）
- 下游：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)（用 model 跑 ramp-up）
- 跨模組：[04 可觀測性模組](/backend/04-observability/)（production log 來源）
- 跨模組：[運維 模組五：流量模型建立](/operations/05-capacity-planning/traffic-model/)（峰均比、到達型態、從 log 抽模型的容量規劃入口）

## 既建知識卡片

- [Workload Model](/backend/knowledge-cards/workload-model/)
- [Shadow Traffic](/backend/knowledge-cards/shadow-traffic/)
- [Growth Curve](/backend/knowledge-cards/growth-curve/)
- [Peak Forecast](/backend/knowledge-cards/peak-forecast/)
