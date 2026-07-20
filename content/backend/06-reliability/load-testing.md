---
title: "6.2 load test"
date: 2026-04-23
description: "把 production 流量結構轉成可重播壓力情境，定位 saturation 轉折與容量邊界"
weight: 2
tags: ["backend", "reliability"]
---

## 概念定位

當系統需要回答「這個流量撐不撐得住」，[load test](/backend/knowledge-cards/load-test/) 把真實 workload model 變成可重播的壓力情境，找出吞吐、延遲與瓶頸轉折點。

這一頁關心的是實際流量長什麼樣，不是把數字推高而已。模型若不接近 production shape，壓測結果就只是在驗證假場景。

## 核心判讀

Load test 的品質先看模型是否貼近流量結構，再看系統在 saturation 前後的行為。曲線在 saturation 前後如何變形才是關鍵，單點 [throughput](/backend/knowledge-cards/throughput/) 只是其中一個讀數。

判讀時的關鍵面向：

- workload 是否包含尖峰、長尾與不同 cohort
- latency 是否在接近飽和時快速劣化
- bottleneck 是否能被定位到具體 resource
- load 結果是否能回寫到 capacity planning

## Workload model 設計

Workload model 的責任是把 production 流量結構轉成可重播的測試情境。模型越接近真實流量的形狀，壓測結果對容量決策的支撐力越高。

設計 workload model 時先分析三個維度：

**Traffic shape**：production 流量很少是均勻的。峰值時段的 request rate 可能是均值的數倍到數十倍，而且峰值持續時間、上升斜率與衰退曲線各有差異。Shopify 的 BFCM 流量結構是短時間爆量加上高寫入比例；若模型只用日均流量推算，會漏掉峰值集中在數小時內的壓力集中度。模型需要把 peak / off-peak / burst 三種時段分開描述。

**[Cohort](/backend/knowledge-cards/cohort/) 拆分**：讀與寫的資源消耗模式不同，混合比例會改變瓶頸位置。API gateway 層可能由讀主導，但 checkout 或 order-create 路徑的寫入比例明顯偏高。把不同 cohort（讀 / 寫 / 混合 / 背景任務）分開量測，才能判斷瓶頸是在哪個路徑上出現。

**資料量對齊**：staging 環境的資料量常與 production 差一到兩個數量級。query plan、index scan、[connection pool](/backend/knowledge-cards/connection-pool) 飽和與 cache 行為都跟資料量高度相關。模型要盡可能用 production-like 資料量，或至少在結果判讀時標註資料量差異帶來的偏移。

LinkedIn 的實踐揭露另一個面向：workload model 會隨時間漂移。流量結構、使用者行為與功能上線都會改變真實壓力形狀。當 load-test 模型不再定期校準，壓測結果與 production 壓力之間的差距會持續擴大。定期用 production traffic replay 或 access log 分析重建模型，是維持壓測可信度的必要動作。

判斷 workload model 是否仍然有效的實務做法：把最近一次 load test 的 latency distribution 與 production 同時段的 latency distribution 對齊。若兩者的 p50 / p95 / p99 比率偏離超過 20%，模型已經需要校準。20% 是通用起點。latency 敏感的服務（交易、即時通訊）應使用更嚴格的門檻（10%），batch 類服務可適度放寬。偏離來源通常是三個之一：流量結構變了（新功能改變 read/write 比例）、資料量成長了（query plan 改變）、依賴行為變了（上游回應時間漂移）。

## Saturation 與瓶頸定位

Saturation 的轉折點決定了系統的實際容量上限 — 在什麼負載下，系統從線性擴展轉為劣化。

判讀 saturation 先看 latency curve。在低負載時，latency 通常穩定；隨著負載上升，會出現一個 inflection point，之後 latency 開始加速上升。這個轉折點通常比 throughput ceiling 更早出現，是真正的容量邊界。

在 inflection point 之後，系統行為會進入幾種退化模式。逐漸退化型的 latency 緩慢爬升，通常來自 queue 堆積或 GC 壓力加重；崩落型的 latency 在某個點突然跳升數倍，通常來自 connection pool 耗盡或 thread pool 飽和。兩種退化的應對策略不同：逐漸退化有 load shedding 的緩衝空間，崩落型需要提早在更低負載觸發限流。壓測結果需要標註系統屬於哪種退化模式，這個資訊直接影響 [stop condition](/backend/knowledge-cards/stop-condition/) 的門檻設定。

瓶頸定位需要對齊資源層。常見瓶頸包括 CPU saturation、memory pressure、[connection pool](/backend/knowledge-cards/connection-pool) 耗盡、queue depth 堆積與 disk I/O。壓測時需要同步觀測這些資源指標，才能把 latency 劣化歸因到具體 resource。歸因的價值在於讓擴容或優化的投資方向可決策：CPU 瓶頸指向 compute scaling、connection pool 瓶頸指向 pool config 或 connection reuse、queue depth 瓶頸可能指向 consumer 吞吐不足。若只看 latency 劣化但不做歸因，團隊容易直覺式擴容，花了成本卻沒打到真正瓶頸。

Pinterest 的快取可靠性案例揭露一種不直覺的瓶頸類型：cache 命中率崩落時，瓶頸會從 compute 層移到 storage throughput。回源壓力瞬間上升，資料層的 I/O 成為新瓶頸。這種情境在純 compute 壓測中看不到，需要特別設計包含 cache miss 場景的 workload。實務上，cache miss 場景可以用兩種方式模擬：清空 cache 後立即打流量（cold start），或在壓測過程中讓部分 key 過期（partial eviction）。兩者暴露的瓶頸位置可能不同，cold start 偏向 storage 吞吐、partial eviction 偏向 connection pool 與 retry 放大。

## Load test 與容量規劃的接口

Load test 的產出不只是 pass/fail，它是容量規劃的主要輸入。壓測結果要能轉成 headroom 計算與成本預測。

**Headroom 計算**：peak load 佔 capacity ceiling 的比率決定安全緩衝。比率超過 70-80% 時，任何流量突增或依賴劣化都可能觸發 saturation。headroom 的安全值跟系統的退化模式綁在一起：崩落型退化的系統需要更大 headroom，因為從健康到故障的過渡窗口很短。LinkedIn 的做法是把 headroom 預算綁到值班分層，當 headroom 低於門檻時自動升級 [on-call](/backend/knowledge-cards/on-call/) 層級，讓容量風險直接轉成團隊行動。

**成本曲線**：擴容的邊際成本會在跨越 availability zone、region 或 tier 邊界時跳升。load test 結果要標註「容量到多少時需要跨越哪個擴容邊界」，讓容量規劃能把成本跳升點納入決策。這類資訊在高峰前特別有價值：團隊能提前決定是靠 load shedding 撐過峰值，還是提前擴容跨區，兩者的成本與風險完全不同。

**隔離單位的容量量測**：全域容量規劃在多租戶或 cell-based 架構下會失真。Amazon 的做法是按 cell 獨立量測 saturation，每個隔離單位有自己的 headroom，避免一個 cell 的容量需求拖動全域擴容。這種設計讓 load test 的量測粒度從「整個服務」降到「每個隔離單位」，容量決策更精準。

load test 結果的完整路由是：壓測產出 saturation point 與 headroom ratio → 餵給 [6.9 容量與成本邊界](/backend/06-reliability/capacity-cost/) 做容量預算 → 餵給 [6.13 performance regression gate](/backend/06-reliability/performance-regression-gate/) 做持續守護。

## 持續性 load test 與事件性壓測

Load test 的執行模式依用途分兩類，兩者設計邏輯不同。

**持續性 load test** 跑在 CI pipeline 中，用固定 workload 做 baseline regression 偵測。每次變更跑同一套 scenario，比較 latency 與 throughput 是否偏離 baseline。這類測試的 workload 不需要貼近峰值，但需要穩定到能偵測 5-10% 的 regression。連到 [6.13 performance regression gate](/backend/06-reliability/performance-regression-gate/) 做自動化 gate。

**事件性壓測** 針對特定事件（產品上線、促銷、峰值季節）做一次性或年度壓測。workload 設計要貼近該事件的流量形狀與資料量。Shopify 把 game day 做成年度制度化流程：每輪 BFCM 前跑容量驗證，演練結果回寫 resiliency matrix 與 runbook，讓下一輪從更高基準開始。事件性壓測的關鍵是結果留存與回寫，不是跑完就結束。

兩類測試的分工：持續性負責守住 baseline，事件性負責探索邊界。只跑持續性會漏掉峰值場景；只跑事件性會漏掉漸進退化。

判斷要用哪一類時，先問兩個問題。第一，這個服務是否有可預期的流量事件（促銷、賽季、發布日）？有的話，事件性壓測是必要的，因為峰值壓力的形狀跟日常完全不同。第二，這個服務的變更頻率是否超過每週一次？是的話，持續性 load test 是必要的，因為 regression 可能在任何一次 deploy 進入。多數生產系統兩類都需要。

## 環境與工具考量

**Staging vs production**：staging 壓測控制成本低、風險低，但跟 production 的差異（資料量、網路拓撲、依賴行為）會讓結果偏移。Production load test（dark traffic、shadow read、canary traffic）結果更可信，但需要嚴格的 [blast radius](/backend/knowledge-cards/blast-radius/) 控制與 [stop condition](/backend/knowledge-cards/stop-condition/) 設計。選擇哪種環境取決於系統成熟度與風險承受能力。

**Synthetic traffic 的限制**：synthetic 請求不帶真實 session、auth token 或 cache warm-up 狀態，行為與真實使用者不同。對 cache 敏感的系統，synthetic traffic 可能打出比真實流量更高的 miss rate，產生虛假瓶頸。對 auth 與 session 敏感的系統，synthetic 請求可能繞過 rate limit 或 WAF 路徑，壓測結果會低估 production 的真實負載。判讀時要標註 synthetic 與 real traffic 的行為差異，避免把假瓶頸或假安全當結論。

**資料隔離**：production load test 需要確保測試流量不會污染真實資料。常見做法包括 shadow read（讀路徑複製、寫路徑丟棄）、test tenant 隔離（獨立資料空間）、與 feature flag 控制的 dark traffic。每種做法的隔離強度與實作成本不同，選擇時要對齊系統的資料敏感度。

工具選擇路由：CI-first 場景偏向 CLI 工具（[k6](/backend/06-reliability/vendors/k6/)）、JVM 生態偏向 [Gatling](/backend/06-reliability/vendors/gatling/)、Python 團隊偏向 [Locust](/backend/06-reliability/vendors/locust/)、既有 .jmx 資產偏向 [JMeter](/backend/06-reliability/vendors/jmeter/)。工具對照見 [vendors/](/backend/06-reliability/vendors/)。

## Load test 結果的證據留存

Load test 結果需要結構化留存，讓下游（容量規劃、release gate、事故決策）可以直接調用，而不是每次都要重跑或找人解釋。

留存的最小欄位：workload model 版本、測試環境、saturation point（latency inflection 的 RPS）、throughput ceiling、主要瓶頸歸因、headroom ratio、退化模式分類、測試日期。這些欄位讓 [6.23 verification evidence handoff](/backend/06-reliability/verification-evidence-handoff/) 可以把 load test 結論直接納入 release 決策，也讓 [6.9 容量與成本邊界](/backend/06-reliability/capacity-cost/) 可以追蹤 saturation point 隨時間的變化趨勢。

若結果只以 dashboard 截圖或口頭摘要留存，下次壓測時團隊無法判斷「是系統變了還是模型變了」，校準失去基準。

## 案例對照

- [Shopify H1](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)：高峰型流量要求 load model 涵蓋短時間爆量與高寫入比例，game day 把事件性壓測制度化。
- [LinkedIn L1](/backend/06-reliability/cases/linkedin/capacity-headroom-and-oncall-tiering/)：headroom 預算綁值班分層，load-test drift 需要定期校準模型。
- [Pinterest P1](/backend/06-reliability/cases/pinterest/cache-reliability-and-capacity-surprises/)：cache 命中率崩落改變瓶頸位置，壓測要涵蓋 cache miss 場景。
- [Amazon A1](/backend/06-reliability/cases/amazon/shuffle-sharding-and-cell-boundary/)：cell-based architecture 讓容量規劃按隔離單位量測，避免全域擴容失控。
- [LinkedIn L2](/backend/06-reliability/cases/linkedin/automated-load-testing-and-capacity-forecasting/)：自動化壓測接入 CI pipeline，用 production traffic replay 定期更新 saturation point，讓容量預測的輸入持續校準。

## 產業情境：電商與零售

電商流量的核心特徵是可預期的季節性峰值（雙十一、Black Friday、Prime Day）與不可預期的閃購爆量。兩者對 workload model 的需求不同，混用同一套模型會讓壓測結論對其中一種場景失真。

季節性峰值的 workload model 需要涵蓋三個電商特有維度：流量上升斜率（開賣瞬間的階梯式爆增 vs 活動期間的漸進增長）、讀寫比例變化（瀏覽階段讀為主 → 結帳階段寫入爆增）、庫存查詢的 cache miss 率（熱門商品快取因庫存變動頻繁失效）。[Shopify 的 BFCM 容量治理](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)把這類峰值的容量驗證制度化為年度 game day。

閃購型流量的特徵是持續時間極短（分鐘級）但倍率極高（日常的 10-50 倍）。常規壓測用日均流量推算會完全漏掉這種尖峰，需要獨立的 burst scenario 模擬開賣瞬間的並發衝擊。

轉換率是電商特有的穩態指標。load test 的判讀不只看 latency 和 error rate，還要看結帳轉換率是否在壓力下劣化。研究顯示 latency 上升 100ms 可能讓轉換率下降 1-7%，這個商業影響在純技術指標中看不到。壓測結果要同時記錄技術指標與業務指標，容量決策才能對齊商業價值。

## 操作判讀

| 觀察到的狀況                         | 可能原因                                          | 下一步行動                                                                                                                      |
| ------------------------------------ | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 壓測通過但 production peak 仍故障    | workload model 未涵蓋峰值形狀或 cohort 比例       | 用 access log 重建 peak 時段模型                                                                                                |
| latency 在低負載就開始劣化           | staging 資料量不足、query plan 與 production 不同 | 用 production-like 資料量重測                                                                                                   |
| throughput ceiling 遠高於 production | synthetic traffic 繞過 auth/cache 路徑            | 加入 realistic session 與 cache miss scenario                                                                                   |
| 壓測結果每月差異大                   | workload model drift                              | 建立定期校準流程、對比 p50/p95 偏移                                                                                             |
| 瓶頸定位不出來                       | 缺少資源層同步觀測                                | 壓測時同步收 CPU / memory / pool / queue 指標                                                                                   |
| cache miss 場景未被覆蓋              | workload 只有 warm cache 情境                     | 參考 [Pinterest P1](/backend/06-reliability/cases/pinterest/cache-reliability-and-capacity-surprises/) 設計 cold start scenario |

## 判讀訊號

- workload 是合成的、跟 production traffic shape 不同
- 壓測通過但 production peak 失敗、模型未涵蓋實際模式
- 只測 throughput、不測 saturation 與 cost curve
- bottleneck 識別靠經驗、無系統定位流程
- capacity 規劃靠一次性 load test 結論、無持續對齊
- load-test 模型超過 6 個月未校準、drift 累積

## 交接路由

- [6.9 容量與成本邊界](/backend/06-reliability/capacity-cost/)：load test 餵給容量規劃輸入
- [6.13 performance regression gate](/backend/06-reliability/performance-regression-gate/)：load baseline 升級為持續 gate
- [6.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/)：production load test 的 blast radius 與 stop condition
- [6.22 steady state definition](/backend/06-reliability/steady-state-definition/)：load test 驗證 saturation 前後的穩態維持
- [6.8 release gate](/backend/06-reliability/release-gate/)：load test 結果作為 release 放行的容量證據
- [6.18 reliability metrics](/backend/06-reliability/reliability-metrics-governance/)：把流量與可靠性指標接起來
