---
title: "JMeter → k6：k6 不是 JMeter 的「script 版本」、是 VU model 取代 thread model"
date: 2026-05-19
description: "JMeter → k6 是 Type E paradigm shift、不是把 .jmx XML 翻成 JavaScript — VU (virtual user) model 跟 thread group model 是兩種對「使用者行為」不同的建模方式。本文走 6 維 audit（Schema High / Paradigm High / Operational Medium）、釐清反向定義、4-phase partial migration（多數 org 停 Phase 2-3 hybrid）、5 production 踩雷（thread group 翻譯失真 / arrival rate vs concurrent VU 混淆 / protocol gap / 結果 schema 改 / CI integration 重做）、protocol gap（JDBC / JMS / LDAP 在 k6 沒原生對應）、何時不要切"
tags: ["backend", "performance", "capacity", "vendor", "migration", "type-e", "paradigm-shift"]
---

k6 不是 JMeter 的 *「script 版本」*。

這個誤解是 JMeter → k6 migration 第一週最常見的事故來源。Migration 啟動會議常聽到「JMeter 的 thread group 翻成 k6 的 VU 就好了吧」、然後團隊把 `.jmx` 內 100 thread → k6 `vus: 100`、跑下去發現 RPS 差三倍、p95 延遲表完全不同形狀、以為 k6 壞了。

實際上 k6 的 *Virtual User (VU)* 跟 JMeter 的 *Thread* 是 *兩種不同的使用者行為建模方式*：

- **JMeter Thread**：一個 OS thread = 一個 user、`numThreads=100` 就 *固定 100 個 concurrent 使用者一直跑*、ramp-up period 控制怎麼啟動、無 explicit arrival rate 概念
- **k6 VU**：一個 goroutine-like execution context、預設 `vus` 是 *concurrent VU pool*、但 k6 更推薦用 `arrival-rate executor` — 直接表達 *每秒進來幾個 request*、VU 是 *為了達到 arrival rate 動態起的 worker*

差別在 *測量視角*：JMeter 預設視角是 *「我有 100 個使用者在用系統」*、k6 預設視角是 *「我每秒有 N 個請求進來」*。兩種視角下 *同一個系統的瓶頸結果完全不同*：100 concurrent user 模型在 server 慢時 throughput 會自動降（user 等回應）、100 RPS arrival rate 模型在 server 慢時 queue 會累積、暴露 *真實 production behavior*（user 不會體諒、會繼續送請求）。

這篇 migration playbook 不是 schema translation 文（`.jmx` 翻成 `.js` 只是表面）、是 *paradigm shift* — 從 closed-system model（thread）到 open-system model（arrival rate）的視角轉換。

## 為什麼是 Type E（schema + paradigm 同 High）

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/#6-維-diff-dimension-audit)：

| 維度        | 評     | 說明                                                                           |
| ----------- | ------ | ------------------------------------------------------------------------------ |
| Schema      | High   | `.jmx` XML vs JavaScript scenario、test plan 完全不同 file format / DSL        |
| Operational | Medium | CLI / distributed run 接近、CI integration 差別大、distributed runner 模型不同 |
| Paradigm    | High   | thread group closed model → arrival rate open model、測試思維不同              |
| Components  | Low    | 都是 load test runner、no multi-tool decomposition                             |
| App change  | N/A    | 是 test code、不是 production code                                             |
| Topology    | Low    | 都是 CLI / runner 跑、無 sharding                                              |

Schema High + Paradigm High 兩軸 High。按優先序 Schema > Paradigm、預設選 Type A。但對 JMeter → k6 的讀者來說、*paradigm shift 才是難關* — schema translation 是工作量、但搞錯 paradigm 會讓 migration 後的測試結果 *跟 production 不對應*。所以選 **Type E paradigm shift** 結構、schema translation 抽出 Phase 1-2 補充。

## Driver：developer ergonomic + CI gate friendly

從 JMeter 遷出 k6 的核心拉力是 *developer ergonomic + CI 友善*：

- **`.jmx` XML 在 git 內 diff 不可讀**：兩個 `.jmx` PR 的 diff 是 XML attribute reorder noise、reviewer 看不出來實際邏輯改了什麼；JavaScript 是純文字 + AST、PR diff 直接可讀
- **GUI 學習曲線**：JMeter GUI 不是現代 IDE、不熟的工程師寫一個 scenario 要花半天找對的 sampler 跟 listener；JavaScript 用既有 IDE（VS Code / IntelliJ）、autocomplete + lint + format 全有
- **CI integration 步驟差**：JMeter 在 CI 跑要 packaging plugin + non-GUI mode + result XML parser；k6 直接 `k6 run script.js`、result 是 JSON / Prometheus metrics、threshold pass/fail 直接 exit code
- **單機 VU 容量**：JMeter 單機通常 ~500-1000 thread（受 JVM 跟 OS thread limit）、k6 單機可跑 30K-50K VU（Go runtime + goroutine）、distributed runner 需求降低
- **Workload model expressiveness**：k6 `arrival-rate executor` + `ramping-vus` + `constant-vus` 三種 executor 直接對應 *open system / ramping / closed system* 三種測量視角、不像 JMeter 需要組合 Constant Throughput Timer + Synchronizing Timer + thread group 才達到

這條 driver 在 *QA 團隊 GUI 維護 .jmx asset* 的 org 沒拉力（GUI 反而是優勢）、但對 *dev / SRE 寫 performance test 進 CI* 的 org 是強拉力。Audience 不同、migration value 完全不同。

## 4-phase partial migration（不收斂）

Type E 的特徵是 *不收斂* — 多數 org 不會把 `.jmx` 全退役、會停在某個 phase 變成 hybrid：

### Phase 1：學會 k6 paradigm（不寫實際 test）

寫一個 throwaway script 跑當前 production-like API、不為了 migrate、為了搞清楚 k6 paradigm：

```javascript
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  // 不要用 vus: 100、用 arrival rate
  scenarios: {
    open_model: {
      executor: 'constant-arrival-rate',
      rate: 100,           // 每秒 100 request
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 200, // 預先準備 VU 數
      maxVUs: 500,          // 上限
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500'], // p95 < 500ms
    http_req_failed: ['rate<0.01'],   // 失敗率 < 1%
  },
};

export default function () {
  const res = http.get('https://api.example.com/orders');
  check(res, { 'status 200': (r) => r.status === 200 });
}
```

對比同一個 test 用 `.jmx` 寫的形狀、思考 *為什麼 arrival rate 跟 thread group 測出來不一樣*。這 phase 的目標是 *paradigm internalization*、不是產出 migration artifact。團隊每個寫 performance test 的人都要過這一關、不能跳。

完成標準：寫的人能講清楚「arrival rate 100 / 5 分鐘」跟「100 thread / 5 分鐘 ramp-up」的 production behavior 差異。

### Phase 2：高價值 critical path 改 k6（GUI 留 JMeter）

選 *最常跑 + 最重要* 的 1-3 條 scenario 改寫 k6、不全部一次轉。典型候選：

- Pre-release smoke test（核心 API 的 baseline check）
- Nightly regression（per-commit performance gate）
- Peak readiness rehearsal scenario（活動前 T-7 跑的 stress test）

GUI / QA 團隊維護的 `.jmx` *不動* — 那些通常是 multi-protocol（JDBC / JMS / FTP）、不在 k6 適合 scope。

工作主要塊：

- `.jmx` thread group → k6 scenario executor 的 *paradigm-correct* 翻譯（不是欄位翻譯）
- HTTP request 跟 assertion 翻譯（payload / header / cookies）
- CSV data source（JMeter CSV Data Set Config）→ k6 `SharedArray` from JSON
- 結果輸出 schema 改變（XML / JTL → JSON / Prometheus / k6 Cloud）
- CI integration 重做（GitHub Actions / GitLab CI 直接 `k6 run`、不需要 packaging）

完成標準：critical path 的 k6 baseline 跟 `.jmx` baseline 數據對比一致（p50 / p95 / throughput 在 10% 誤差內、行為不一致時知道是 paradigm 差還是 bug）。

### Phase 3：QA 團隊雙工具技能（hybrid 穩定形態）

很多 org 停在這個 phase：QA 團隊用 GUI 維護 multi-protocol .jmx（covering JDBC / JMS / LDAP / SOAP / FTP）、dev / SRE 用 k6 維護 HTTP / gRPC / WebSocket performance test in CI。Two-tool stack 不是 broken state、是 *not-converged-by-design*。

這個 phase 的工作主要塊：

- 文件化：哪類 test 用 k6、哪類用 JMeter、決策樹寫在 team handbook
- 結果整合：兩個工具的 metrics 都進同一個 Grafana dashboard（k6 → Prometheus 直接、JMeter → InfluxDB / Prometheus exporter）
- Release gate 用 k6 為主（CI 整合直接）、JMeter 用於 manual QA campaign / multi-protocol 場景

多數 org 不進 Phase 4。

### Phase 4：JMeter 退役（少見）

只有當 *所有 protocol 都換到 k6 extension* 或 *捨棄了 multi-protocol coverage* 時、才 fully 退役 JMeter。常見路徑：

- 用 k6 xk6 extensions 補 protocol（xk6-sql for JDBC、xk6-kafka for Kafka、xk6-amqp for RabbitMQ、xk6-mqtt for MQTT）
- 評估每個 extension 的 maturity / community support — xk6 ecosystem 比 JMeter plugin 小很多
- 接受 part of legacy `.jmx` test 直接 deprecate（covered by integration test 而非 load test）

完成標準：所有 protocol 都在 k6 + xk6 內可表達、`.jmx` 全部 archive。

## 5 個 production 踩雷

### 1. Thread group → VU 直接翻譯（最常見、Phase 2 必踩）

把 `numThreads=100` 翻成 `vus: 100` 就完事 — 結果 RPS 跟 JMeter 不一致、p95 完全不同形狀。原因：JMeter 100 thread 是 *closed model*（thread 等回應才送下一個）、k6 `vus: 100` 預設也是 closed model、但 *iteration 結束就立刻送下一個*（無 think time）— 兩者的 *throughput 行為* 差異來自 think time / response time。

修法：

- 不用 `vus: N`、用 `constant-arrival-rate` 或 `ramping-arrival-rate`、直接表達 *每秒幾個請求*
- 如果一定要 closed model（pre-existing JMeter scenario 對比）、在 default function 內加 `sleep(thinkTime)` 模擬 JMeter Think Time

### 2. Arrival rate vs concurrent VU 混淆

`arrival-rate` executor 的 `rate: 100` 意思是 *每秒進來 100 request*、`preAllocatedVUs: 200` 是 *預先準備 200 個 VU worker pool*。如果 service 變慢（p95 從 100ms 飄到 500ms）、需要的 VU 數會從 100/sec * 0.1s = 10 暴增到 100/sec * 0.5s = 50、`preAllocatedVUs` 不夠就會 warning「ran out of VUs」、實際 arrival rate 達不到 spec。

修法：

- `preAllocatedVUs` 設為 `maxVUs / 2`
- `maxVUs` 設為 `rate * worst_case_response_time_seconds * 5`（5x safety margin）
- Monitor `dropped_iterations` metric — 不該 > 0、> 0 表示 worker pool 不夠

### 3. Protocol gap（k6 沒原生對應 JMeter 的部分）

k6 原生支援 HTTP/1.1 / HTTP/2 / gRPC / WebSocket / SSE。**沒有**原生支援：

- JDBC（要 xk6-sql extension）
- JMS（要 xk6-amqp / xk6-kafka extension）
- LDAP（無 extension、要外接 LDAP client）
- FTP（無 extension）
- SMTP / IMAP / POP3（無 extension）
- SOAP（HTTP module 內手寫 XML body、無 helper）

如果 `.jmx` 用了這些 protocol、評估 xk6 extension 成熟度（GitHub stars、recent commit、issue volume）、不成熟就把這些 test 留在 JMeter。

### 4. 結果輸出 schema 改變（result post-processing 全部要重寫）

JMeter 預設輸出 JTL XML（per-sample 一行）、有 listener 後處理。k6 預設輸出 stdout summary + optional JSON / CSV / Prometheus / k6 Cloud。如果有既有 *result analysis pipeline*（從 JTL 拉 data 進 BI tool、產 trend chart）、Phase 2 必須重寫。

修法：

- 評估直接接 Prometheus + Grafana（k6 native）取代既有 BI dashboard
- 或寫 k6 JSON output → 自家 BI 的 transformation script

### 5. CI integration 重做（distributed runner 模型不同）

JMeter 在 CI 跑要：JVM provision、plugin install、`.jmx` upload、non-GUI mode 跑、JTL 結果 parse、exit code 對應 threshold。k6 在 CI 跑：`k6 run script.js`、threshold pass / fail 直接 exit code、result 進 Prometheus / k6 Cloud。

看起來 k6 簡單、但有踩雷：

- Distributed run model 不同：JMeter 用 master-slave、k6 OSS 不內建 distributed、要 Grafana Cloud k6 或自建 k6-operator on Kubernetes
- 大規模負載（> 50K VU）必須 distributed、Phase 2 評估時要先確認 distributed setup 不是 blocker
- CI runner 資源：k6 是 native binary、CPU / memory 用量比 JMeter（JVM）低、但 runner spec 要按 max VU 估

## Protocol gap 詳表

| Protocol       | JMeter sampler              | k6 對應                 | 成熟度 / 替代方案                   |
| -------------- | --------------------------- | ----------------------- | ----------------------------------- |
| HTTP/1.1       | HTTP Request                | `k6/http`               | 原生、成熟                          |
| HTTP/2         | HTTP/2 sampler              | `k6/http`（auto）       | 原生、成熟                          |
| gRPC           | （無原生、要 plugin）       | `k6/net/grpc`           | 原生、成熟                          |
| WebSocket      | WebSocket sampler（plugin） | `k6/ws`                 | 原生、成熟                          |
| SSE            | （無原生）                  | xk6-sse                 | extension、中等                     |
| JDBC           | JDBC Request                | xk6-sql                 | extension、不成熟、留 JMeter        |
| JMS            | JMS sampler                 | xk6-amqp / xk6-kafka    | extension、protocol-specific        |
| LDAP           | LDAP Request                | （無）                  | 外接 / 留 JMeter                    |
| FTP            | FTP Request                 | （無）                  | 留 JMeter                           |
| SMTP / IMAP    | Mail sampler                | （無）                  | 留 JMeter                           |
| SOAP / XML-RPC | SOAP / XML-RPC Request      | `k6/http` 手寫 XML body | 工作量大、留 JMeter                 |
| TCP socket     | TCP sampler                 | `k6/net/tcp`            | 原生但簡單、複雜 protocol 留 JMeter |

## 容量與成本對照

| 項目                    | JMeter            | k6 OSS                  | Grafana Cloud k6          |
| ----------------------- | ----------------- | ----------------------- | ------------------------- |
| Cost                    | Free (Apache)     | Free (Apache 2.0)       | $49+ / mo (Pro)           |
| 單機 VU 容量            | ~500-1000 thread  | 30K-50K VU              | unlimited（cloud runner） |
| Distributed             | master-slave 內建 | 不內建、需 k6-operator  | cloud-native              |
| Result store            | JTL XML（local）  | stdout / JSON / Prom    | cloud retained            |
| CI integration          | 需 packaging      | native CLI              | native + cloud            |
| Multi-protocol coverage | 廣                | 窄（HTTP/gRPC/WS）+ xk6 | 同 OSS                    |

對 dev-driven CI gate use case：k6 OSS 已經夠用、Grafana Cloud k6 在 *跨 region runner + result retention + dashboard 整合* 時才有 ROI。對既有 multi-protocol .jmx asset：考慮 Phase 3 hybrid stable state、不要強推 Phase 4。

## 何時不要切

- **multi-protocol coverage 是核心需求**：JDBC + JMS + LDAP + FTP 必要、xk6 extension 不夠成熟、留 JMeter
- **QA 團隊維護 GUI .jmx**：QA 不寫 code、`.jmx` GUI 是團隊資產、貿然轉 k6 等於 throwaway QA team
- **既有 multi-year .jmx asset 大量**：500+ scenario 全部翻譯成本 > k6 ergonomic 收益、考慮 Phase 3 stable hybrid
- **Distributed run 需求極大（> 100K VU）但 ops budget 緊**：k6-operator on Kubernetes 不便宜、Grafana Cloud k6 對應 tier 也不便宜、JMeter master-slave 仍是 cost-effective 選項

## 下一步路由

- 平行 batch：[Pyroscope → Datadog Profiler](/backend/09-performance-capacity/vendors/datadog-continuous-profiler/migrate-from-pyroscope/)（Type C operational hybrid）
- 同 batch Type E：[PagerDuty → incident.io](/backend/08-incident-response/vendors/pagerduty/migrate-to-incident-io/)（IR paradigm shift）
- 上游：[9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/) / [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)
- 下游：[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)（CI gate integration）
- vendor 對照：[JMeter](/backend/09-performance-capacity/vendors/jmeter/) / [k6](/backend/09-performance-capacity/vendors/k6/) / [Gatling](/backend/09-performance-capacity/vendors/gatling/) / [Locust](/backend/09-performance-capacity/vendors/locust/)
- 方法論：[Migration Playbook Methodology](/posts/migration-playbook-methodology/)（Type E paradigm shift 結構說明）
