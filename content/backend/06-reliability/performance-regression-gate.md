---
title: "6.13 Performance Regression Gate"
date: 2026-05-01
description: "把效能 baseline 從一次性壓測變成持續對齊的 release gate，涵蓋 baseline 設定、判讀方法、variance 控制與退化定位"
weight: 13
tags: ["backend", "reliability"]
---

## 概念定位

Performance regression gate 守住系統的效能餘裕 — 避免看似功能正確的變更悄悄拖垮延遲、吞吐或成本。

這一頁關心的是變更有沒有偷走系統的效能餘裕。沒有 gate，效能退化常常要等使用者感受到才會被看見。跟 [6.2 load test](/backend/06-reliability/load-testing/) 的分工是：6.2 訂定 baseline 與 saturation point，6.13 確保每次變更不會讓 baseline 被偷走。

## 核心判讀

效能 gate 的健康度取決於 baseline 是否穩定、regression 偵測是否足夠敏感。

重點訊號包括：

- baseline 是否來自 production-like workload
- regression 是否能分辨 noise 與真實退化
- perf budget 是否跟 release gate 綁定
- 當退化出現時，是否能快速定位到 code path 或依賴

## Baseline 設定

Baseline 的責任是提供可比較的效能基準。沒有穩定 baseline，gate 判讀就無法區分「系統真的變慢了」跟「環境噪音」。

Baseline 有三種來源，各自的可信度與維護成本不同。

**Production percentile**：從 production 的 latency / [throughput](/backend/knowledge-cards/throughput/) 分佈取 p50 / p95 / p99 作為基準。優點是最接近真實使用者體驗；限制是 production 流量本身有時段波動，需要選定穩定時段的統計窗口。適合作為最終判準，但不適合作為 CI 內的即時 gate（CI 環境跟 production 差異太大）。

**CI benchmark history**：在同一 CI 環境、同一 workload 下累積歷史趨勢。優點是環境一致，regression 可歸因到 code 變更；限制是 CI 環境本身可能有波動（runner 硬體、鄰居效應），需要 variance 控制。適合作為每次 merge 的即時 gate。

**Load test 結果**：[6.2 load test](/backend/06-reliability/load-testing/) 產出的 saturation point 與 latency inflection。優點是覆蓋高負載場景；限制是執行成本高、不適合每次 push 跑。適合作為 scheduled path 的 baseline 校準來源。

Baseline 更新頻率跟系統變更頻率對齊。高頻變更服務（每日多次 deploy）需要 rolling baseline（取最近 N 次 CI 結果的中位數）；低頻變更服務可以用固定 baseline 搭配季度校準。

Baseline 品質的判準是自身 variance。若 baseline 的 p99 波動超過 5-10%，任何小於這個幅度的 regression 都落在噪音區間內，gate 無法可靠判讀。此時應先控制 variance（見下段），再設定 regression 門檻。

## Regression 判讀方法

Regression 判讀有三種方法，選擇取決於 CI 環境的穩定性與測試時間預算。

### 絕對門檻

設定 p99 latency 上限（例如 200ms）或 throughput 下限（例如 1000 RPS），超過就 fail。

這種方法實作最簡單，適合有明確 SLA 的服務。限制是容易誤報（環境噪音造成的瞬間飆高）或漏報（慢速退化每次只惡化 2-3ms，始終低於門檻，累積半年後才被注意到）。適合作為安全網而非主要判讀手段。

### 相對退化

跟前一版 baseline 比較，退化超過 Y%（例如 latency 增加 > 10%）就 fail。

這種方法能抓到漸進退化，因為每一次小幅惡化都會觸發。前提是 baseline 穩定 — 若 baseline 自身波動 8%，設定 10% 門檻幾乎沒有判讀空間。適合 variance 已被控制到 3-5% 以內的 CI 環境。

### 統計顯著性

用統計檢定（t-test、Mann-Whitney U）判斷兩組測量的分佈是否有顯著差異。

這種方法最準確，能在高 variance 環境中篩掉噪音。限制是需要足夠樣本量 — CI 短時間測試可能只跑 10-20 次 iteration，樣本不足時統計功效低，真實退化也可能被判為不顯著。適合測試時間預算充裕的 scheduled path。

三種方法可以組合：fast path 用絕對門檻做安全網，slow path 用相對退化做主要判讀，scheduled path 用統計檢定做精確校準。

## Variance 控制

CI 環境的噪音是 perf gate 最大的干擾源。噪音讓真實退化被遮蓋，也讓正常變更被誤報，兩者都會侵蝕團隊對 gate 的信任。

主要噪音來源與對應控制方式：

| 噪音來源               | 機制                                    | 控制方式                               |
| ---------------------- | --------------------------------------- | -------------------------------------- |
| Shared runner 鄰居效應 | 其他 job 搶 CPU / memory / I/O          | Dedicated runner 或 ephemeral instance |
| Cold start             | JIT warmup、cache miss、connection 建立 | Warmup iteration（丟棄前 N 次結果）    |
| GC pause               | 記憶體壓力觸發 stop-the-world GC        | 固定 heap size、GC log 同步收集        |
| Network jitter         | 跨服務通訊的延遲波動                    | Local dependency（mock / sidecar）     |
| Hardware 差異          | 不同世代 runner 的 CPU 效能不同         | Pinned hardware config / instance type |

Variance 控制的投資報酬是讓 regression 門檻可以設得更敏感。當 variance 從 15% 降到 3%，gate 就能攔住 5% 的退化；否則只能設 20% 門檻，等於放過大量漸進退化。

連到 [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/) 的 environment 隔離段 — perf gate 需要的 runner 隔離等級通常高於一般功能測試。

## Micro benchmark vs End-to-end perf test

兩種測試粒度服務不同的判讀需求，分工而非替代。

**Micro benchmark** 對準單一函式、code path 或演算法。variance 小（不涉及 I/O、network、GC 壓力低）、回饋快（秒級）、定位精準（退化直接指向特定函式）。限制是覆蓋不到跨服務退化、serialization 成本或 middleware 堆疊的效能影響。適合跑在 CI fast path（每次 push）。

**End-to-end perf test** 覆蓋真實請求路徑，從 API gateway 到 database 到 response。能抓到跨層退化（middleware 累積、serialization 成本、connection pool 競爭），但 variance 大、定位困難（退化可能來自任何一層）。適合跑在 CI slow path（merge gate）或 scheduled path。

分工原則：micro benchmark 負責守住 code-level baseline，end-to-end perf test 負責守住 service-level baseline。兩者都 fail 時，micro benchmark 的結果通常能直接定位 regression 來源；只有 end-to-end fail 時，需要搭配 profiling diff 做進一步歸因。

## 退化定位與行動

Gate 攔住 regression 後，下一步是定位來源並決定行動。

**Profiling diff**：比較兩版的 flame graph 或 CPU profile，找出新增的 hot path。連到 [4.9 continuous profiling](/backend/04-observability/continuous-profiling/) — 若 production 已有 continuous profiling，可以直接比較 canary 與 stable 版本的 profile 差異，定位精度高於 CI 環境的 benchmark。

**Commit bisect**：在 CI benchmark history 中二分搜尋 regression 引入點。當多個 commit 合併後才觸發 gate fail，bisect 能縮小到具體 commit。前提是 CI benchmark 有逐 commit 的歷史紀錄。

定位後的行動有三種：

- **修復**：regression 來源明確、修復成本可接受。這是預設行動。
- **接受**：regression 是預期的 trade-off（例如安全性改善帶來的加密成本）。此時更新 baseline，並在 [6.23 evidence handoff](/backend/06-reliability/verification-evidence-handoff/) 記錄接受理由。
- **延後**：regression 來源複雜、修復需要大幅重構。記錄到 [6.21 reliability debt backlog](/backend/06-reliability/reliability-debt-backlog/) 並設定修復期限。延後的風險是多次延後累積成使用者可感知的退化。

## 產業情境：串流與媒體服務

串流服務的效能 regression 量測維度跟一般 web service 不同。API latency 只是其中一層，媒體交付品質才是使用者直接感受的指標。

串流特有的 regression 指標包含 video start time（TTFB to first frame）、rebuffering rate（播放中斷頻率）、bitrate switches per session（畫質跳動次數）與 ABR algorithm response time（adaptive bitrate 的反應速度）。這些指標需要專門的量測管線，CI 環境的 mock player 很難完全模擬真實觀看行為，canary 階段的 real user monitoring 是更可靠的 regression 偵測來源。

Transcoding pipeline 的 regression 需要三維判讀。新 codec 或 encoder 版本可能改善壓縮率但增加 encoding latency，CI gate 需要同時量化 encoding speed、output quality 與 cost — 只看其中一個維度會漏掉 trade-off。例如 AV1 encoder 比 H.264 壓縮率更好，但 encoding 時間可能增加數倍，若 gate 只看 latency 就會擋住合理的品質升級。

CDN cache hit rate 是隱性的 regression 指標。code 變更如果改變了 cache key 策略或 content fingerprint，CDN cache hit rate 會下降，回源流量上升，間接造成 origin latency 惡化與成本跳升。這類 regression 在 staging 壓測中看不到（staging 沒有 CDN 快取層），需要 canary 階段的 CDN 層監控才能偵測。

## 案例對照

- [Google G1](/backend/06-reliability/cases/google/error-budget-policy-and-release-gating/)：效能退化會加速 error budget 消耗。當 latency regression 導致 SLO breach 頻率上升，perf gate 的門檻應與 error budget 政策連動 — budget 健康時接受較寬鬆的門檻，budget 緊繃時收緊。
- [LinkedIn L1](/backend/06-reliability/cases/linkedin/capacity-headroom-and-oncall-tiering/)：效能退化直接壓縮 capacity headroom。當 p99 latency 上升 20%，等效 headroom 下降，可能觸發 on-call 層級升級。perf gate 的門檻應考慮 headroom ratio 的安全邊界。
- [Shopify H1](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)：高峰前的效能退化風險比平時更高。BFCM 前收緊 perf gate 門檻，避免峰值期間 latency regression 與流量尖峰疊加。
- [LinkedIn L2](/backend/06-reliability/cases/linkedin/automated-load-testing-and-capacity-forecasting/)：持續壓測作為 regression 偵測的輸入來源 — 自動化壓測的 saturation point 趨勢可以補充 CI benchmark 看不到的系統級退化。

## 判讀訊號

| 訊號                                 | 判讀條件                                                        | 行動建議                                        |
| ------------------------------------ | --------------------------------------------------------------- | ----------------------------------------------- |
| 連續多版微小退化、累積後才被發現     | 相對退化門檻未設或太寬鬆，改用 rolling baseline + 相對退化判讀  | 設 rolling baseline + 5-10% 相對退化 threshold  |
| 大版本升級 latency 漲、定位困難      | 缺少逐 commit benchmark history，補 commit bisect 機制          | 每個 commit 跑 micro benchmark、保留歷史        |
| Benchmark variance > 退化幅度        | CI 環境噪音未控制，先降 variance 再設門檻                       | 改用 dedicated runner + warmup iteration        |
| Canary 只看 error rate、不看 latency | perf gate 與 canary 判讀脫鉤，把 latency percentile 加入 canary | 補 p95/p99 latency 到 canary 判讀指標           |
| 第三方依賴效能變化未納入 baseline    | baseline 只看本服務、漏掉依賴，補 end-to-end perf test 覆蓋     | 加 end-to-end perf test 到 slow path            |
| Gate 頻繁誤報、團隊開始忽略          | 門檻未對齊 variance，或測試環境不穩定，先修 variance 再調門檻   | 先量測 variance、再設 threshold = baseline + 2σ |

## 交接路由

- [4.9 continuous profiling](/backend/04-observability/continuous-profiling/)：退化定位到 callstack
- [5 部署平台](/backend/05-deployment-platform/)：canary 階段的 perf gate
- [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/)：perf test 在 CI 分層中的位置與 runner 隔離
- [6.2 load test](/backend/06-reliability/load-testing/)：baseline 來源與 saturation point
- [6.8 release gate](/backend/06-reliability/release-gate/)：退化觸發 freeze
- [6.17 feature flag](/backend/06-reliability/feature-flag-governance/)：flag 切換後的效能驗證
- [6.21 reliability debt](/backend/06-reliability/reliability-debt-backlog/)：延後修復的 regression 進入 debt backlog
- [6.23 evidence handoff](/backend/06-reliability/verification-evidence-handoff/)：接受 regression 時的理由留存
