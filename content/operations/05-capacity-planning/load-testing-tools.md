---
title: "壓力測試工具與方法"
date: 2026-07-03
description: "要用壓測驗證容量規劃時，釐清壓測到底在找什麼、k6 與 wrk 各自的定位、怎麼讀壓測輸出的延遲分布，以及讓結果失真的幾個反模式"
weight: 3
tags: ["devops", "capacity-planning", "load-testing", "k6", "wrk"]
---

壓測要回答的問題是「這個服務在什麼負載下開始撐不住」，不是「跑一次看會不會掛」。有價值的壓測是階梯加壓、觀察系統行為在哪個點從穩定轉為劣化，把 [流量模型](/operations/05-capacity-planning/traffic-model/) 的假設拿到真實負載下驗證。工具選對，這個劣化點測得準；工具選錯，測到的是工具自己的極限、不是被測系統的。

工具選型的核心不是「哪個最強」，是「哪個最貼合本團隊的 workload model 表達能力與 CI 整合需求」。同樣一組流量，能不能用工具複製出來，決定壓測結果可不可信。

## 選型看六個維度

選壓測工具要按六個維度評估，只看「能不能發 HTTP 請求」會選錯：

- **腳本表達能力**：能不能寫完整的用戶動線（登入到瀏覽到結帳），而不只是打單一端點。複雜系統的瓶頸常在跨端點的資源競爭，單端點壓測看不到。
- **協議支援**：HTTP、WebSocket、gRPC、TCP。現代後端常用 WebSocket 與 gRPC，有些老工具要靠外掛才支援。
- **規模能力**：單機能發多少 RPS、能不能分散式擴容。單機 wrk 能發一到五萬 RPS，分散式部署的工具能到百萬級。
- **CI 整合**：能不能在 PR 上跑輕量效能檢查、結果能不能機器可讀、能不能跟 baseline 比對。沒有 CI 整合的工具只能做事件型壓測，做不了持續的效能治理。
- **結果分析**：原生儀表板、或整進既有的 metric 系統、或純文字輸出。
- **學習曲線**：腳本語言與團隊熟悉度。工具再好、團隊不會用，就會變成一兩個人的孤島技能。

主流開源工具的定位大致是：k6（JavaScript 腳本、CI 友善、現代專案首選）、Locust（Python、適合複雜業務邏輯、單機吞吐受限要靠分散式）、Gatling（Scala、報表精美、學習曲線陡）、JMeter（協議廣、腳本是 XML 難版控、已在用的團隊再續用）、wrk 與 Vegeta（單機極限壓測、找天花板用）。選型的完整維度與雲端託管服務見 [backend 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)，這一章聚焦怎麼實際跑一次、怎麼讀結果。

## 用 k6 實際跑一次

k6 的壓測腳本是一段 JavaScript，定義加壓的階段（stages）與通過標準（thresholds）。下面這段腳本把虛擬用戶（VU）在 5 秒內拉到 20、維持 10 秒、再 5 秒降回 0，並設一條「p95 延遲要低於 500 毫秒」的通過線：

```javascript
import http from 'k6/http';
import { check } from 'k6';
export const options = {
  stages: [
    { duration: '5s', target: 20 },
    { duration: '10s', target: 20 },
    { duration: '5s', target: 0 },
  ],
  thresholds: { http_req_duration: ['p(95)<500'] },
};
export default function () {
  const res = http.get('http://target/');
  check(res, { 'status is 200': (r) => r.status === 200 });
}
```

對一個 nginx 目標實跑這段腳本，輸出的關鍵段落是：

```text
  █ THRESHOLDS
    http_req_duration
    ✓ 'p(95)<500' p(95)=1.3ms

  █ TOTAL RESULTS
    checks_succeeded...: 100.00% 637011 out of 637011
    http_req_duration..: avg=403µs min=11µs med=126µs max=562ms p(90)=749µs p(95)=1.3ms
    http_req_failed....: 0.00%  0 out of 637011
    http_reqs..........: 637011 30971/s
```

讀這份輸出的順序是：先看 `THRESHOLDS` 有沒有通過（打勾代表 p95 通過了 500 毫秒的線），再看 `http_req_failed` 確認錯誤率（0% 代表沒有失敗請求），接著看 `http_reqs` 的每秒數（這次是 30971 RPS）。真正的判讀重點在 `http_req_duration` 那一行的分布：平均 403 微秒沒什麼資訊量，要看的是 p90、p95 跟 max 之間的差距。這次 p95 是 1.3 毫秒、max 卻是 562 毫秒——絕大多數請求很快，但有極少數慢了三個數量級。這種「平均漂亮、尾巴很長」正是只看平均會漏掉的問題，也是壓測要看 percentile 而非平均的理由。

這次測出的 sub-millisecond 延遲有一個前提：壓測機跟被測的 nginx 跑在同一台主機的容器網路裡，沒有真實的網路往返。這正好示範了下一節第一個反模式——壓測機跟被測機太近，延遲會被嚴重低估、p99 比 production 樂觀。

## wrk 找單機天花板

wrk 的定位跟 k6 不同：它不寫複雜動線，專門對單一端點灌到極限、找這個服務的天花板。saturation discovery 的第一輪常用它——`wrk -t4 -c100 -d30s --latency http://target/` 開 4 個執行緒、100 條連線、壓 30 秒，回報 RPS 與延遲分布。k6 適合驗證「這條用戶動線在預期負載下的行為」，wrk 適合回答「這個端點的絕對上限在哪」，兩者常搭配：wrk 先找到天花板的量級，k6 再在天花板以下驗證真實動線。

## 讓結果失真的反模式

壓測最大的風險是測出一個看起來漂亮、但不能外推到 production 的數字。幾個常見的失真來源：

- **只測單一 API、不測用戶動線**：找不到跨端點的資源競爭、也累積不出真實的 session 狀態。
- **壓測機跟被測機在同一網段**：網路延遲被低估，p99 比 production 樂觀——上一節的 sub-millisecond 結果就是這個例子。
- **壓測時 throttle 到自己的工具**：測出的是工具的極限、不是被測系統的，訊號是壓測機自己的 CPU 先滿。
- **只看平均延遲**：尾延遲看不到，p99 的劣化被平均值蓋掉。
- **壓測環境跟 production 硬體不一致**：CPU 型號、網路、磁碟 IOPS 差很多，結果不可外推。
- **跑了壓測卻沒驗證模型**：沒拿結果跟 production metric 比對，不知道壓測用的流量模型貼不貼近真實。

## 下一步路由

- 壓測用的流量模型怎麼建、怎麼驗證 → [流量模型建立](/operations/05-capacity-planning/traffic-model/)
- 用階梯加壓找飽和點、讀哪些訊號 → [規模拐點判斷](/operations/05-capacity-planning/scaling-inflection-point/)
- 工具選型的完整維度、雲端託管壓測、production 流量重播 → [backend 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)
