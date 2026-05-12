---
title: "9.9 Performance Improvement Loop"
date: 2026-05-12
description: "壓測 → profile → fix → re-test → release gate 的閉環"
weight: 9
tags: ["backend", "performance", "capacity", "improvement"]
---

## 概念定位

Improvement loop 的責任是把效能優化從「事件型 hotfix」變成「持續改進的工程流程」。沒有 loop 時、效能問題靠 oncall 觸發、改了又改、改完又退化；有 loop 之後、每次 release 都通過 perf gate、退化在發布前就攔住。

跟 [06.13 perf regression gate](/backend/06-reliability/performance-regression-gate/) 的關係：06.13 是 release gate 的一個環節、9.9 是這個 gate 背後的完整工程閉環。06.13 處理「進 gate 後怎麼判斷」、9.9 處理「進 gate 前怎麼產生比較資料」。

本章聚焦在 *閉環設計* — 怎麼建 baseline、怎麼跑 re-test、怎麼用 profile diff、怎麼整合 CI。讀完後讀者能設計一個 perf improvement workflow、不是只有 ad-hoc 壓測。

## Loop 五個階段

完整的 improvement loop 包含五個階段、缺一不可：

**1. Baseline 建立**：壓測 + profile 取得「當前正常」snapshot。
**2. 變更 + re-test**：每次 release candidate 跑壓測、跟 baseline diff。
**3. Profile diff**：用 flame graph diff 定位退化原因。
**4. Fix**：rollback 或修正 code path。
**5. Update baseline**：通過後更新 baseline、進下個 cycle。

少了 baseline → re-test 沒有比較對象、看絕對數字會錯判。
少了 profile diff → 退化定位靠猜、修錯方向。
少了 update baseline → 永遠跟 old baseline 比、退化累積看不出來。
少了 fix → 退化通過 gate、production 出事。

## Baseline 設計

Baseline 不是「歷史最佳」、是「最低可接受效能」。

**設計原則**：

- 不只一個 baseline、按 workload model 訂多個（不同 endpoint、不同 user tier 各自 baseline）
- baseline 必須可重複：固定 seed、固定資料集、固定環境、固定壓測參數
- 定期 review：硬體 / 軟體升級會讓 baseline 該往好的方向走、不更新就是裝盲

**儲存策略**：

- baseline as artifact：存進 release artifact、隨 release 帶走
- baseline as code：用 Pulumi / Terraform / dedicated config 管理、可 version control
- baseline as service：dedicated service 管 baseline、提供 query API

**Drift 監控**：baseline 每月對比上月、看趨勢是否往好方向。drift 超門檻 → re-baseline 並 review 原因。

## Profile diff

退化定位的關鍵工具是 [profile diff](/backend/knowledge-cards/profile-diff/) — 對比兩次 profile 找 hottest 變化。

**工具實作**：

- Brendan Gregg 的 differential flame graph：開源、需要手動 generate
- Pyroscope diff：UI 直接對比兩個時間段
- Datadog Continuous Profiler diff：跟 deployment marker 整合
- Parca compare：CNCF 標準
- AWS CodeGuru Profiler：自動偵測 CPU / memory anti-pattern

**正確使用方法**：

- 在 *相同負載 + 相同硬體 + 相同 sampling rate* 下取兩次 profile
- 比較 *相對變化*、不是絕對 CPU%
- 看 wider stack（不只看 leaf function）找 systemic regression

**Profile diff 結果通常需要工程師判讀**：「多花 20% CPU 但 throughput 多 50%」可能是好變化、不能純自動化判斷退化是否可接受。

對應案例：[Netflix Aurora 統一](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — DB 層統一後 profile diff 噪音降低、退化來源更容易識別。

## Regression gate 整合 CI

效能改進閉環必須整合到 CI、不能只在 release 前一次性跑。

**Multi-tier 壓測策略**：

- 每個 PR：跑 lightweight perf test（單 endpoint、5 分鐘）、合併前比 baseline
- 主分支 nightly：跑 medium perf test（多 endpoint、30 分鐘）
- Release candidate：跑 complete perf test（完整 workload model、數小時）

**Gate 觸發條件**：

- p99 退化 > X%（例如 10%）
- 吞吐降 > Y%（例如 5%）
- error rate 升 > Z%
- cost per request 升 > W%

**Gate 通過 / 不通過的後果**：

- 通過：自動 promote 到下個 stage（staging / canary / production）
- 不通過：block release、自動 notify owner、附 profile diff link

**Gate 太敏感的反模式**：

- 每天 false positive、最後沒人看（alert fatigue）
- false positive 來源：壓測環境噪音、baseline drift 未更新、業務變化
- 對策：multi-window detection（變化必須持續 N 個 sample）、配合 manual override（資深工程師判斷異常正常）

對應案例：[06.13 perf regression gate](/backend/06-reliability/performance-regression-gate/) 的實作建議。

## Canary perf check

[Canary perf check](/backend/knowledge-cards/canary-perf-check/) 是 release 階段的另一道 perf gate。跟 regression gate（pre-release）對應、是 *production* 階段的監控。

**Canary 階段除了看 error rate、也看**：

- latency p99 / p999（最先看到的 regression 訊號）
- throughput（是否處理變慢）
- resource utilization（CPU / RAM / connection 變化）
- cost per request（是否更貴）

**Canary 流量 vs control 流量比較**：

- 同樣流量同樣時段、不同版本的差才有意義
- 不能拿 canary 跟 historical baseline 比（外部變數太多）
- abort condition：canary p99 比 control 退化 > X%

**漸進放大策略**：1% → 5% → 25% → 50% → 100%、每階段觀察足夠時間（至少 15 分鐘看 long-tail）。

對應案例：[Prime Day FIS 8x chaos](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) — canary 模式跟 chaos test 並行、確保新版本在故障場景也撐得住。

## Pre-release 改進迴圈頻率

不同層級的 review 在不同節奏：

- **每日 PR 級 perf check**：lightweight、單 endpoint、5 分鐘
- **每週 release candidate 完整壓測**：完整 workload model、數小時
- **每月 baseline review + drift 評估**：對比歷史趨勢、決定是否 re-baseline
- **每季容量地圖 review**：跟 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 連動

頻率不夠 → 退化累積看不到；頻率太高 → 工程資源吃緊。按團隊規模跟 release 節奏調整。

## 退化的常見來源

知道退化怎麼來、才能設計對應的 detection：

- **新功能引入 N+1 query**：ORM lazy loading、loop 內 query。看 DB call count 變化
- **ORM 沒下 index、cache miss 飆升**：看 slow query 跟 cache hit rate
- **第三方 library upgrade 帶來 overhead**：新版本可能多了 telemetry / validation。看 profile diff
- **GC tuning 變動**：JVM / Go GC config 調整造成 pause time 變化。看 p999
- **container resource limit 變動**：Kubernetes limit 改、限制更嚴造成 throttling。看 CPU throttling event

## 反模式

- **只在 release 前一次性壓測**：退化已累積數月、找不出原因
- **baseline 不更新**：永遠跟舊版本比、低估目前狀態
- **改了又改、改完忘記更新 baseline**：下次 release 又跟過時 baseline 比、迴圈失效
- **缺 profile diff、退化原因靠猜**：修錯方向、退化還在
- **gate 訊號跟業務無關**：技術指標退化但業務 metric 沒事、被當 false positive

## 案例對照

| 案例                                                                                              | 教學重點                  |
| ------------------------------------------------------------------------------------------------- | ------------------------- |
| [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)             | 統一 DB 後 profile 變單純 |
| [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)         | 遷移後重新做 baseline     |
| [9.C1 Prime Day FIS 8x](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) | 持續改進的混沌 + 壓測迴圈 |

## 下一步路由

- 上游：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) / [9.5 瓶頸定位](/backend/09-performance-capacity/bottleneck-localization/)
- 下游：[9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)
- 跨模組：[06.13 perf regression gate](/backend/06-reliability/performance-regression-gate/) / [06.8 release gate](/backend/06-reliability/release-gate/)

## 既建知識卡片

- [Profile Diff](/backend/knowledge-cards/profile-diff/)
- [Continuous Profiling](/backend/knowledge-cards/continuous-profiling/)
- [Canary Perf Check](/backend/knowledge-cards/canary-perf-check/)
