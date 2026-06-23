---
title: "k6：Threshold CI Gate 與 Scenario 設計"
date: 2026-06-23
description: "用 threshold 把 load test 結果變成 CI pass/fail，用 scenario 讓 workload model 貼近 production traffic shape。"
weight: 1
tags: ["backend", "reliability", "vendor", "load-test"]
---

## 問題情境

Load test 跑完會產生大量指標，但 CI pipeline 需要的是 pass/fail 訊號。若沒有 threshold 把指標轉成判讀結論，效能退化只能靠人工看 dashboard 發現，等到看見時通常已經累積數個版本。

另一面，threshold 的判讀品質取決於 workload model 的真實度。用 `--vus 10 --duration 30s` 跑出來的結果跟 production 流量結構差距太大時，threshold 通過也無法證明 production 安全。

這篇處理兩個問題：怎麼設 threshold 讓 CI gate 可靠，怎麼設 scenario 讓 workload 接近真實。

## Threshold 設計

Threshold 的責任是把 load test 指標轉成 CI 的 pass/fail 訊號。k6 在所有 threshold 都通過時回傳 exit code 0，任一 threshold 失敗就回傳非零 — CI pipeline 直接用 exit code 判斷。

### 多指標 threshold

單一指標 threshold 容易漏風險。latency 正常但 error rate 偏高代表系統在丟請求；throughput 正常但 latency 偏高代表排隊開始堆積。完整的 threshold 至少涵蓋三個面向：

```javascript
export const options = {
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed:   ['rate<0.01'],
    http_reqs:         ['rate>100'],
  },
};
```

latency threshold 用 percentile 而不是 average — average 會被長尾稀釋，p95/p99 更接近使用者感知的最差體驗。

### 門檻來源

Threshold 的門檻從 production baseline 出發。先從 observability 系統（Grafana / Datadog）取最近 7-30 天的 p95/p99 latency 與 error rate，加上可接受退化幅度（通常 10-20%）作為 threshold。門檻太緊會讓 CI 環境噪音觸發 false positive；門檻太寬會讓真退化滑過去。

校準節奏：每月或每次重大架構變更後重新對齊 production baseline，避免 threshold 跟真實系統漂移。

### Path-level threshold

不同 API path 的效能特徵不同。checkout 路徑的 latency 容忍度可能比 listing 路徑低很多。k6 的 group + tag 機制讓 threshold 可以按 path 設定：

```javascript
import { group } from 'k6';

export default function () {
  group('checkout', function () {
    // checkout 請求
  });
  group('listing', function () {
    // listing 請求
  });
}

export const options = {
  thresholds: {
    'http_req_duration{group:::checkout}': ['p(95)<300'],
    'http_req_duration{group:::listing}':  ['p(95)<800'],
  },
};
```

path-level threshold 讓 gate 的判讀粒度從「整體效能」細化到「關鍵路徑效能」。

## Scenario 設計

Scenario 的責任是讓壓測的流量結構接近 production。k6 提供五種 scenario executor，選擇取決於要控制什麼變量。

| Executor              | 控制變量     | 適用場景                      |
| --------------------- | ------------ | ----------------------------- |
| constant-vus          | 並發使用者數 | 簡單 smoke test               |
| ramping-vus           | 並發使用者數 | 階梯式升壓找 saturation       |
| constant-arrival-rate | 固定 RPS     | CI regression（穩定輸入）     |
| ramping-arrival-rate  | 變化 RPS     | 模擬 production peak/off-peak |
| externally-controlled | 外部 API     | 結合 production 流量 replay   |

### Executor 選擇判準

constant-vus 最簡單，但 throughput 會隨 response time 波動 — 伺服器變慢時 RPS 自動下降，掩蓋了真正的壓力。constant-arrival-rate 控制 RPS 穩定，能讓 threshold 的判讀基準一致，但需要設定足夠的 preAllocatedVUs 避免 k6 因為 VU 不足而主動降速。

CI regression 測試建議用 constant-arrival-rate：輸入固定、輸出可比較、版本間的差異才有意義。

### Production traffic shape 對齊

用 ramping-arrival-rate 模擬 production 的流量形狀：

```javascript
export const options = {
  scenarios: {
    peak_simulation: {
      executor: 'ramping-arrival-rate',
      startRate: 50,
      stages: [
        { target: 200, duration: '2m' },  // ramp up
        { target: 200, duration: '5m' },  // sustain peak
        { target: 50,  duration: '1m' },  // ramp down
      ],
      preAllocatedVUs: 300,
    },
  },
};
```

流量形狀的參數（startRate / target / duration）從 production access log 的 peak 時段推算。Shopify 的 BFCM 準備流程把 game day 的 load test scenario 跟實際峰值形狀對齊 — 短時間爆量加高寫入比例需要特別設計 scenario 來覆蓋。

### Cohort 模擬

Production 流量不是單一類型。用多 scenario 並行模擬不同 cohort：

```javascript
export const options = {
  scenarios: {
    read_traffic: {
      executor: 'constant-arrival-rate',
      rate: 150, exec: 'readFlow',
      preAllocatedVUs: 200,
      duration: '5m',
    },
    write_traffic: {
      executor: 'constant-arrival-rate',
      rate: 30, exec: 'writeFlow',
      preAllocatedVUs: 50,
      duration: '5m',
    },
  },
};

export function readFlow() { /* GET 請求 */ }
export function writeFlow() { /* POST 請求 */ }
```

讀寫比例從 production 的 access log 或 APM 資料推算。比例偏差會讓瓶頸位置失真 — 讀為主的模型抓不到寫入引起的 lock contention。

### 資料驅動

測試資料用 SharedArray 載入，避免每個 VU 各自載入造成記憶體浪費：

```javascript
import { SharedArray } from 'k6/data';

const users = new SharedArray('users', function () {
  return JSON.parse(open('./users.json'));
});
```

資料來源可以是 production sample（脫敏後）或 synthetic generation。資料分佈需要接近 production — ID 範圍、key 分佈、payload 大小都會影響 query plan 與 cache 行為。

## CI 整合實務

### Fast path（每次 push）

固定 scenario + 短 duration（30s-2min），用 constant-arrival-rate 做 regression 偵測。threshold 設在 production baseline + 10%。這一層的目的是快速攔住明顯退化，不需要模擬完整峰值。

### Slow path（merge gate）

完整 scenario + 較長 duration（5-15min），包含多 cohort 與 ramping 模擬。threshold 涵蓋 path-level 指標。這一層的目的是深層驗證變更在接近真實壓力下的行為。

### 結果留存

k6 結果預設輸出到 stdout。CI 整合時用 `--out` flag 把結果送到時序資料庫（InfluxDB / Prometheus Remote Write / Grafana Cloud k6），讓歷史趨勢可查詢。趨勢比較能偵測 threshold 內但持續惡化的 slow drift。

LinkedIn 的自動化壓測實踐把 load test 結果跟容量預測接在一起 — saturation point 隨時間的變化趨勢直接驅動擴容決策。

## 邊界與陷阱

**Threshold variance**：CI runner 的硬體差異（shared runner 的鄰居效應、network jitter、GC pause）會讓同一份 code 在不同 run 產生不同結果。控制方式：dedicated runner 消除鄰居效應、warmup iteration 丟棄前幾輪結果、多次 run 取中位數。若 variance 超過 threshold 的退化幅度，gate 判讀就不可信。

**門檻過寬或過緊**：threshold 永遠通過代表 gate 形同虛設；threshold 頻繁 false positive 會讓團隊忽略 CI 結果。兩者都會讓 gate 失去判讀價值。校準的判準是：過去 30 天的 threshold 結果中，真正需要關注的退化是否都被攔住，同時 false positive 率低於 5%。

**Scenario 跟 production drift**：production 的流量結構會隨產品演進改變。定期（每月或每次重大功能上線）用 access log 校準 scenario 的 RPS、cohort 比例與資料分佈，避免模型越跑越偏。

## 整合路由

- 上游概念：[6.2 load testing](/backend/06-reliability/load-testing/) 的 workload model 設計
- 下游能力：[6.13 performance regression gate](/backend/06-reliability/performance-regression-gate/) 的 baseline 管理與退化定位
- 平行 vendor：[Gatling](/backend/06-reliability/vendors/gatling/)、[Locust](/backend/06-reliability/vendors/locust/)、[JMeter](/backend/06-reliability/vendors/jmeter/)
- 案例回寫：[Shopify BFCM 容量治理](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)（game day load test 對齊峰值形狀）、[LinkedIn Automated Load Testing](/backend/06-reliability/cases/linkedin/automated-load-testing-and-capacity-forecasting/)（持續壓測驅動容量預測）
