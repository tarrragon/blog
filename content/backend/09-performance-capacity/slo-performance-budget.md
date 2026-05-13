---
title: "9.12 SLO 與 Performance Budget"
date: 2026-05-12
description: "performance budget 跟 SLO / error budget 的對接"
weight: 12
tags: ["backend", "performance", "capacity", "slo"]
---

## 概念定位

SLO 與 performance budget 的責任是讓容量決策有「可衡量的目標 + 可審查的代價」。沒有 SLO 時、容量規劃容易變「越大越好」、沒邊界；有 SLO + budget 之後、所有決策都能回答「是否在 budget 內」、「超出 budget 該怎麼辦」。

跟 [06.6 SLO 與 Error Budget](/backend/06-reliability/slo-error-budget/) 的關係：06.6 處理「可靠性 SLO」（用 error budget 凍結 release）、9.12 處理「效能 SLO」（用 performance budget 約束容量）。兩者用同一套方法論、目標不同。讀者可以把本章當作 06.6 的 *效能對應* 章節。

本章覆蓋 SLI/SLO/SLA 分層、latency budget 分解、performance budget vs error budget、SLO 等級的成本含義、多 SLO 對齊、SLO drift 維護。讀完後讀者能設計一套完整的 SLO + budget 系統、把容量決策跟 SLO 對接。

## SLI / SLO / SLA 三層分清

三個名詞常被混用、實際是三個不同層的概念。

**SLI（Service Level Indicator）**：客觀量測值。p99 latency、availability、throughput、error rate 都是 SLI。
**SLO（Service Level Objective）**：團隊內部目標。「99.95% 用戶請求 < 500ms」這類具體承諾。
**SLA（Service Level Agreement）**：對外合約承諾。達不到要退款、違約金、信用補償。

**SLO 比 SLA 嚴 — 給內部 buffer**。SLA 訂 99.9%、SLO 訂 99.95% — 萬一 SLO 沒達到、SLA 還沒違約、有反應時間。

**容量規劃針對 SLO、不是 SLA**：SLA 是「最低不能跌破」、SLO 才是「日常目標」。用 SLA 做容量規劃會經常 violate SLA、給用戶 / 客戶不好體驗。

詳見 [SLI / SLO 卡片](/backend/knowledge-cards/sli-slo/)。

## Latency budget 分解

[Latency budget](/backend/knowledge-cards/latency-budget/) 是把 SLO 翻成可分解工程目標的關鍵工具。

**從 end-to-end latency 開始**：

- 用戶感受到的 latency：DNS resolution + TLS handshake + CDN + load balancer + application + cache + DB + serialization + network back
- SLO 訂在 user-perceived：例如「p99 end-to-end < 500ms」

**拆到每個 stage 的 budget**：

- DNS：5ms（assume cached）
- TLS handshake：50ms（first request）
- CDN：20ms
- Load balancer：5ms
- Application：100ms
- Cache lookup：5ms（hit）/ 100ms（miss）
- DB query：30ms
- Serialization：10ms
- Network return：15ms
- **總和**：240ms（cache hit）/ 335ms（miss）

**每個 stage 的 budget 必須 *跟 SLO 對齊***：

- 每個 stage 加總 = SLO 上限
- 任何 stage 超 budget → 該 stage 必須改善（不是其他 stage 來補）
- 每個 stage 必須有 *current measurement* — 不能訂了沒量

**Cross-region call 自帶不可壓縮 latency**：

- 同 AZ：< 1ms
- 跨 AZ：1-2ms
- 跨 region 同 continent：20-30ms
- 跨 continent：100-200ms
- SLO 訂 50ms 但服務要跨 region 設計 → 不可能達成

**任何新增 stage 都會吃 budget**：middleware、sidecar、interceptor、API gateway 都會增加 latency。設計時要明確認知這層代價。

對應案例：[Coinbase sub-ms](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — sub-millisecond 反推所有架構選擇（Cluster Placement Group 壓網路、z1d 壓 CPU、RAFT 壓共識）；[Tubi p99 < 10ms](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) — ML inference 多 stage 各自分配 budget。

## Performance budget

[Performance budget](/backend/knowledge-cards/performance-budget/) 跟 error budget 是 *姊妹概念* — 用同一套方法論處理可靠性 vs 效能。

**Error budget**（[06.6](/backend/06-reliability/slo-error-budget/)）：

- 每月有允許的 unavailability 額度
- 例如 SLO 99.95% → error budget = 0.05% × 30 days = 21.6 分鐘 / 月
- 額度用完 → freeze new release、focus on reliability

**Performance budget**（本章）：

- 每月有允許的 latency 退化額度
- 例如「p99 允許比 baseline 高 10ms 連續 X 分鐘」、用 [burn rate](/backend/knowledge-cards/burn-rate/) alert
- 額度用完 → freeze new feature release、focus on perf

**兩個 budget 並列、不衝突**：

- 一個燒一個健康 → 部分 freeze（freeze 對應的那條）
- 兩個都健康 → 全速 release
- 兩個都燒 → 全面 freeze、deep review

**Burn rate alert 比 threshold alert 好**：

- threshold：p99 > 500ms 就 alert → false positive 多
- burn rate：過去 1 小時 budget burn rate > 14.4x 就 alert（Google SRE 推薦）→ 對應「再這樣下去 budget 5 分鐘內燒光」

對應案例：[Coinbase 延遲就是收入](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — 沒 performance budget 等於沒 release control；[FanDuel 多 SLO](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) — 直播 vs 投注不同 budget。

## SLO 等級的成本含義

不同 SLO 等級對應不同容量成本、選 SLO 就是選成本。

| SLO     | 年 downtime 上限 | 工程含義                               | 適用場景                       |
| ------- | ---------------- | -------------------------------------- | ------------------------------ |
| 99%     | 年 87.6 小時     | 單 AZ 部署可接受                       | B2C 內部工具、非 critical SaaS |
| 99.9%   | 年 8.76 小時     | 多 AZ、reactive failover               | B2C consumer-facing            |
| 99.95%  | 年 4.38 小時     | 多 AZ active-active、autoscale 必要    | B2B SaaS minimum               |
| 99.99%  | 年 52.6 分鐘     | 多 region active-active、無人工介入    | mission-critical SaaS          |
| 99.999% | 年 5.26 分鐘     | 全球多 region、即時 failover、人工極少 | 金融 / 醫療 / 電信             |

**每多一個 9、容量成本指數成長**：

- 99 → 99.9：成本 +30-50%
- 99.9 → 99.99：成本 +50-100%
- 99.99 → 99.999：成本 +200-500%

**選 SLO 不是 marketing 決策、是工程經濟決策**：選太高、燒錢；選太低、用戶不滿。要算 *每個 9 對應的業務價值*、是否值得對應的容量投資。

對應案例：[Amazon Ads 99.999%](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) — 廣告計費 1 分鐘斷線損失幾百萬美金、5 個 9 是真實營收邊界；[Genesys 99.999%](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) — B2B 客服 SaaS、客戶停線 = 客戶失去用戶信任、5 個 9 是合約義務。

## 多 SLO 對齊

同一系統不同工作負載可以有不同 SLO、按業務重要性分級。

**設計原則**：

- 按「業務重要性 × 用戶感知」分級
- 同一個 endpoint 不同情境可能有不同 SLO（例如登入 vs 結帳）
- 多 SLO 必須有 *優先順序*、衝突時知道犧牲哪個

**範例**：
| Endpoint | SLO        | 業務影響                 |
| -------- | ---------- | ------------------------ |
| 登入     | p99 200ms  | 用戶 onboarding          |
| 瀏覽商品 | p99 500ms  | 用戶 retention           |
| 結帳     | p99 300ms  | 直接影響收入             |
| 推薦     | p99 1000ms | 影響 conversion 但非阻斷 |

**衝突處理**：當 capacity 不夠時、優先保 *結帳* 而非 *推薦*、即使技術上推薦比較好擴容。

對應案例：[FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 直播秒級 SLO vs 投注毫秒級 SLO、同一個 user 同一場 NFL Super Bowl、兩個服務必須分開部署、各自 SLO。

## SLO 演進：baseline drift

[SLO 不是訂了就不動](/backend/knowledge-cards/slo-baseline-drift/) — 業務變化要重新校準。

**SLO drift 來源**：

- Structural surge：COVID 類外部衝擊讓 baseline 永久上移
- Product change：新 feature 改變用戶 journey
- Architectural improvement：DB 換型、cache 加強、CDN 擴點
- User behavior：mobile share 上升、跨 region 比例變化

**Drift 不是 anomaly、是 *新常態***。

**Review 節奏**：

- 每季 review SLO：拉過去 90 天 SLI 分布、看是否需要調整
- 重大產品改動立即 review
- Drift 確認後要更新：alert threshold、autoscaler trigger、performance budget 額度、容量規劃 baseline

對應案例：[Zoom 30x COVID](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) — 30 倍成長後 baseline 永久上移、SLO threshold 跟著重新校準、不能套用 COVID 前的標準。

## SLO 跟容量規劃對接

回到本章開頭的論點 — SLO 是容量決策的目標。

**容量公式**：能撐多少 RPS @ SLO 條件。
**規劃時用「SLO-constrained capacity」、不是「max capacity」**：

- max capacity：絕對極限、進 cliff
- SLO-constrained capacity：知道在 SLO 條件下能撐多少
- 兩者差 30-50%（headroom）

**9.4 saturation 找 knee 是技術指標、9.6 容量規劃用 SLO-constrained knee**：

- saturation 在 utilization 80% 時開始
- 但 SLO 可能要求 utilization 60% 以下
- 容量規劃用 60% 而非 80%

**跟 [9.7 成本工程](/backend/09-performance-capacity/cost-engineering/) 對接**：

- 每多一個 9 多花多少錢
- 業務需要這個 9 嗎
- 不需要的話降 SLO 省成本

## SLO 跟 performance budget 一起用

最後的整合 — error budget + performance budget 一起治理 release 節奏。

**Error budget 控制 *變更節奏***：

- error budget 健康 → release 可以快
- error budget 燒光 → freeze release

**Performance budget 控制 *容量決策***：

- performance budget 健康 → 新 feature 可以引入 perf cost
- performance budget 燒光 → freeze new feature

**兩個 budget 並列**：

- 都健康 → 全速 release + 新 feature
- error 健康 + perf 燒 → release 但只接 perf-neutral 變更
- error 燒 + perf 健康 → 暫停 release、修可靠性
- 都燒 → 全面 freeze、deep review

對應 [06.6 SLO](/backend/06-reliability/slo-error-budget/) 跟 [06.8 release gate](/backend/06-reliability/release-gate/)。

## 案例對照

| 案例                                                                                                    | 教學重點                  |
| ------------------------------------------------------------------------------------------------------- | ------------------------- |
| [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/)       | latency budget 反推架構   |
| [9.C5 / C24 99.999%](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)            | 5 個 9 的容量代價         |
| [9.C25 Tubi ML stage budget](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) | p99 多 stage 分配         |
| [9.C28 FanDuel 多 SLO](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/)     | 直播 vs 投注不同 SLO 並存 |
| [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)                         | SLO baseline 重新校準     |

## 下一步路由

- 上游：[9.1 壓測理論](/backend/09-performance-capacity/performance-theory/)（latency budget 反推）
- 上游：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)（SLO-constrained capacity）
- 跨模組：[06.6 SLO 與 Error Budget 政策](/backend/06-reliability/slo-error-budget/)（可靠性 SLO）
- 跨模組：[04.16 SLI / SLO 訊號](/backend/04-observability/sli-slo-signal/)（量測層）

## 既建知識卡片

- [SLI / SLO](/backend/knowledge-cards/sli-slo/)
- [Latency Budget](/backend/knowledge-cards/latency-budget/)
- [Performance Budget](/backend/knowledge-cards/performance-budget/)
- [SLO Baseline Drift](/backend/knowledge-cards/slo-baseline-drift/)
- [Error Budget](/backend/knowledge-cards/error-budget/)
