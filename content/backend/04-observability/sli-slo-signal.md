---
title: "4.6 SLI 量測與 SLO 訊號設計"
date: 2026-06-22
description: "把可靠性目標的訊號從 metric 端設計好、餵給 6.6 SLO 政策"
weight: 6
tags: ["backend", "observability"]
---

## 大綱

- SLI 設計起點：user-journey 而非 system metric
- 量測點選擇：edge / gateway / service / dependency 各自代表什麼
- Ratio metric vs latency [percentile](/backend/knowledge-cards/percentile/)：何時用哪種
- [Burn rate](/backend/knowledge-cards/burn-rate/) 訊號：multi-window multi-burn-rate alert
- [Error budget](/backend/knowledge-cards/error-budget/) 計算所需的 metric 結構
- 跟 [4.2 metrics](/backend/04-observability/metrics-basics/) 的分工：4.2 是 counter/gauge/histogram 基礎、4.6 是 SLI 化的設計
- 跟 [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/) 的分工：4.4 是 alert 規則治理、4.6 是 alert 的訊號源頭
- 反模式

## 概念定位

SLI 訊號設計是把可靠性目標轉成可量測資料的步驟，責任是讓 SLO 政策建立在使用者旅程與服務結果上。

CPU、memory、queue depth 可以提供系統背景，但 [SLI](/backend/knowledge-cards/sli-slo/) 需要回答的是使用者層面的問題：request 是否成功、回應是否夠快、結果是否正確。SLI 量測的位置跟算式決定了 SLO 反映的是「使用者體驗」還是「基礎設施健康」— 兩者的判讀意義不同。

本章處理的是 metric 到 SLI 的轉換。[4.2](/backend/04-observability/metrics-basics/) 定義 counter / gauge / histogram 的基礎型別；本章定義怎麼用這些型別組出代表使用者體驗的 SLI，並設計 burn rate alert 的訊號結構。SLO 政策本身（error budget freeze、release gate 決策）由 [6.6 SLO 政策](/backend/06-reliability/) 處理。

## SLI 設計起點：User Journey

### 從使用者操作推導 SLI

SLI 的設計起點是「使用者在做什麼、期待什麼結果」，不是「系統有什麼 metric 可以用」。

一個 checkout 流程的使用者期待：request 成功（不會看到 error page）、回應夠快（不會等超過 3 秒）、結果正確（扣款金額正確）。對應三種 SLI：

- **Availability SLI**：成功 request 的比例（`successful_requests / total_requests`）
- **Latency SLI**：回應時間在閾值內的比例（`requests_under_3s / total_requests`）
- **Correctness SLI**：結果正確的比例（需要業務邏輯判定，通常用特定 error code 或 reconciliation 結果）

每個 user journey 不需要三種 SLI 都有。Checkout 的 availability 跟 latency 是核心；correctness 靠事後對帳驗證。搜尋頁面的 latency 比 availability 更關鍵 — 使用者容忍偶發的「搜不到結果」但不容忍 5 秒的載入。

### System metric 跟 SLI 的差異

CPU > 90% 不是 SLI — 它是 cause signal。CPU 高但 latency 正常，使用者沒受影響。Disk usage > 85% 也不是 SLI — 它是 capacity signal，需要處理但不代表當下使用者體驗退化。

System metric 的價值在 root cause analysis，不在 SLI。事故中先看 SLI 判斷「使用者是否受影響」，確認受影響後再看 system metric 判斷「原因是什麼」。把 system metric 當 SLI 會讓 SLO 反映基礎設施噪音而非使用者體驗。

## 量測點選擇

SLI 的量測點影響「看到的是誰的觀點」。同一個 request 在不同位置量測會得到不同的 latency 跟 success rate。

### Edge / Load Balancer

最貼近使用者的量測點。量到的 latency 包含 network round-trip + TLS handshake + 所有 backend 處理時間。Availability 反映的是使用者實際看到的 success rate（包含 load balancer 自身的 502/503）。

優點是最能代表使用者體驗。缺點是 load balancer 的 metric 粒度有限 — 通常只有 status code 跟 latency，不帶 service-level 的維度切分。

### API Gateway

比 edge 更有應用層上下文。可以按 route / method / tenant 切分 SLI。量到的 latency 不含 network round-trip（已經進入服務網路），但包含 authentication、rate limiting 跟所有下游處理。

API gateway 是多數團隊的 SLI 量測起點 — 粒度足夠、位置夠近使用者、通常已有 instrumentation。

### Service level

每個服務的 handler-level metric。可以看到單一服務的 latency 跟 error rate，但不含上下游的影響。適合做 service-level SLO（「order service 的 p99 latency < 200ms」），但不直接代表 user-journey SLO。

Service-level SLI 的價值在於 SLO 階層化 — user-journey SLO 拆分成每個服務的 SLO，事故時能快速定位是哪個服務的 SLO 被打破。

### Dependency level

量測外部依賴（database、cache、third-party API）的回應時間跟 error rate。Dependency metric 的角色是 SLI 退化時的歸因訊號，用來追溯因果鏈而非直接代表使用者體驗。Database latency 上升 → service latency 上升 → user-journey latency SLO 被打破 — dependency metric 幫助追溯因果鏈。

## SLI 的 Metric 結構

### Ratio metric：availability 跟 correctness

Availability SLI 的 metric 結構需要兩個 counter：total requests 跟 successful requests（或 failed requests）。SLI = good / total。

```text
# Availability SLI
http_requests_total{service="checkout", status="2xx"} / http_requests_total{service="checkout"}
```

定義「good」的邊界需要明確。5xx 算 bad，4xx 呢？Client error（400）通常不算服務失敗；authentication failure（401/403）也不算。但 429（rate limit）可能代表服務容量不足，視情境可能算 bad。這個邊界要在 SLI 定義時明確寫下來。

### Latency metric：threshold-based ratio

Latency SLI 用 [histogram](/backend/knowledge-cards/histogram/) 量測，SLI 值是「在閾值內的 request 比例」。

```text
# Latency SLI：p99 < 500ms 的比例
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{service="checkout"}[5m])) < 0.5

# 或用 ratio 形式
sum(rate(http_request_duration_seconds_bucket{le="0.5",service="checkout"}[5m]))
/ sum(rate(http_request_duration_seconds_count{service="checkout"}[5m]))
```

Latency 閾值的選擇要對齊使用者期待而非系統能力。使用者期待 checkout 在 3 秒內完成 — 這是閾值的來源，不是「系統平均 latency 是 200ms 所以閾值設 500ms」。

### Label 設計

SLI metric 的 label 需要足夠的切分能力（by service、by endpoint、by tenant），但受 [cardinality](/backend/knowledge-cards/metric-cardinality/) 預算約束。

最小 label set：service name + method（GET/POST）+ status class（2xx/4xx/5xx）。這組 label 支撐 service-level SLO 計算。

擴展 label：endpoint path（normalize 後，例如 `/api/orders/{id}` → `/api/orders/:id`）、tenant（多租戶場景）。每增加一個 label 維度，series 數量乘法增長 — 在 [4.7 cardinality](/backend/04-observability/cardinality-cost-governance/) 的 label 白名單中管理。

## Burn Rate 與 Multi-window Alert

### Burn rate 的概念

[Burn rate](/backend/knowledge-cards/burn-rate/) 是「error budget 被消耗的速度」。Burn rate = 1 代表按 SLO 允許的速度正常消耗；burn rate = 10 代表消耗速度是允許值的 10 倍 — 如果持續下去，error budget 會在 SLO 週期的 1/10 內耗盡。

用 burn rate alert 取代固定閾值 alert 的好處：burn rate 自動適應流量。低流量時段的幾筆 error 可能 burn rate 很低（因為 total 也少、對 error budget 影響小）；高流量時段的相同 error rate 可能 burn rate 很高（因為 total 多、影響的使用者量大）。

### Multi-window multi-burn-rate

單一時間窗口的 burn rate alert 會太吵（短窗口）或太晚（長窗口）。Multi-window 策略組合兩者：

| 視窗組合    | Burn rate 閾值 | 偵測速度 | 用途           |
| ----------- | -------------- | -------- | -------------- |
| 5min + 1hr  | 14.4x          | 快       | 急性問題、page |
| 30min + 6hr | 6x             | 中       | 持續退化       |
| 2hr + 3day  | 1x             | 慢       | 慢性消耗       |

14.4x 的來源：若 SLO 週期是 30 天、要在 1 小時內偵測到會耗盡 2% error budget 的問題，burn rate = (30 × 24) / 1 × 0.02 ≈ 14.4。6x 跟 1x 依此邏輯調整消耗比例跟偵測窗口。

短窗口（5min）抓急性：error rate 突然飆高、burn rate 衝到 14.4x。長窗口（1hr）做確認：退化確實持續、排除瞬間 spike。兩個窗口都超過閾值才觸發 alert，減少單一 spike 的 false alarm。

### Recording rule 支撐 burn rate 計算

Burn rate 的計算涉及多個時間窗口的 ratio metric。每次 alert evaluate 都重算會給 TSDB 帶來查詢壓力。用 [recording rule](/backend/knowledge-cards/recording-rule/) 把每個窗口的 error ratio 預計算，alert rule 讀 recording rule 的輸出：

```text
# Recording rule：5 分鐘窗口的 error ratio
- record: slo:checkout:error_ratio:rate5m
  expr: sum(rate(http_requests_total{service="checkout",status=~"5.."}[5m]))
      / sum(rate(http_requests_total{service="checkout"}[5m]))
```

Alert rule 讀 recording rule 比每次重算 raw series 高效，也讓 burn rate 的計算邏輯集中管理。

## Error Budget 的 Metric 結構

[Error budget](/backend/knowledge-cards/error-budget/) 是 SLO 週期內允許的錯誤量。SLO = 99.9% 代表 30 天內允許 0.1% 的 request 失敗。Error budget = total requests × 0.001。

Error budget 的 metric 結構需要：

- **Total requests（rolling window）**：過去 30 天的 total request count
- **Failed requests（rolling window）**：過去 30 天的 failed request count
- **Budget consumed**：failed / (total × (1 - SLO target))
- **Budget remaining**：1 - budget consumed

Budget remaining 作為 dashboard panel 跟 [release gate](/backend/knowledge-cards/release-gate/) 的輸入 — 餘額低於閾值時 freeze deployment。這個計算的 rolling window 用 recording rule 維護，避免每次查詢掃描 30 天的 raw data。

## 核心判讀

判讀 SLI 設計時，先看量測點是否貼近使用者，再看算式是否能穩定支援 error budget。

重點訊號包括：

- Edge / gateway / service / dependency 的量測點是否各自有清楚責任
- Latency percentile 與 ratio metric 是否對應不同使用者體驗
- [Burn rate](/backend/knowledge-cards/burn-rate/) 是否使用多時間窗，避免太吵或太晚
- SLI label 是否有足夠切分能力，同時受 cardinality 預算約束
- Error budget 的 rolling window 是否用 recording rule 維護

## 判讀訊號

- Alert 用 system metric（CPU / memory）而非 user-facing 訊號
- Burn rate 只有單窗、噪音多或偵測太晚
- SLI 計算用平均、不用 percentile
- Error budget 算式分母不穩（流量低時誤觸發、高時稀釋）
- SLI 量測點離使用者太遠（內部 service 而非 edge/gateway）
- SLI 沒有定義「什麼算 good request」的邊界（4xx 算不算 bad）
- Burn rate 計算每次重算 raw series、沒有 recording rule

## 反模式

| 反模式                  | 表面現象                                   | 修正方向                                       |
| ----------------------- | ------------------------------------------ | ---------------------------------------------- |
| System metric 當 SLI    | CPU/memory alert 頻繁但使用者沒受影響      | 改用 user-facing ratio / latency SLI           |
| Burn rate 單窗          | 短窗太吵或長窗太晚、alert 價值低           | 組合 5min+1hr / 30min+6hr 多窗策略             |
| SLI 用 average latency  | Tail latency 被掩蓋、p99 使用者體驗失真    | 改用 histogram percentile                      |
| Good request 邊界不明   | 4xx 算不算 bad、SLI 值忽高忽低             | 明確定義 good/bad 分類、寫進 SLI spec          |
| Error budget 無 rolling | 月初 budget 就耗盡、剩下 20 天沒有保護機制 | 用 rolling window 持續計算、預警消耗速度       |
| SLI label 無界          | 每個 URL path 都是獨立 SLI、series 爆炸    | Normalize path、label 白名單、cardinality 預算 |
| SLO 無 owner            | 沒人維護 SLI 定義跟閾值、退化時無人負責    | 每個 SLO 帶 owner、定期審視                    |

## 交接路由

- [4.2 metrics](/backend/04-observability/metrics-basics/)：counter / gauge / histogram 基礎型別
- [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/)：burn rate alert 的 noise control 跟 runbook
- [4.7 cardinality / cost](/backend/04-observability/cardinality-cost-governance/)：SLI metric 的 cardinality 預算
- [4.10 client-side / RUM](/backend/04-observability/client-side-monitoring/)：user-journey-centric SLI 的前端訊號來源
- [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)：recording rule 支撐 burn rate 計算
- [6.6 SLO 政策](/backend/06-reliability/)：error budget 餘額作為 freeze 條件
- [6.8 release gate](/backend/06-reliability/)：burn rate 觸發 freeze
- [8.1 incident severity](/backend/08-incident-response/)：burn rate 對應 severity 門檻
- [4.14 anomaly detection](/backend/04-observability/anomaly-detection/)：跟 SLO threshold 的訊號分工
- [11.11 錯誤回報的回饋迴路](/backend/11-api-design/error-feedback-loop/)：consumer 側用 error rate 與 SLO 判「偶發 vs 持續 vs 異常放大」、決定要不要升級或熔斷
