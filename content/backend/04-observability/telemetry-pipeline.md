---
title: "4.11 Telemetry Pipeline 架構"
date: 2026-05-01
description: "把 log / metric / trace 的 agent → collector → ingest → storage → query 分層治理"
weight: 11
tags: ["backend", "observability"]
---

## 大綱

- 為何要把 telemetry 當 pipeline 看：每層有獨立失敗模式與成本邊界
- 分層責任：agent（採集）、collector（聚合 / 轉換）、ingest（寫入 [buffer](/backend/knowledge-cards/buffer/)）、storage（保留 / 查詢）、query（dashboard / alert）
- [buffer](/backend/knowledge-cards/buffer/) 與 [backpressure](/backend/knowledge-cards/backpressure/)：collector 端緩衝、ingest 滿時的降級策略
- OpenTelemetry Collector 的角色：vendor-neutral 中介層
- pipeline 失敗時的 graceful [degradation](/backend/knowledge-cards/degradation/)：訊號斷一層、其他層仍可用
- multi-tenant 環境的 quota / 隔離
- 觀測遷移流程：先換 collector 再換 instrumentation、雙軌期保留對照
- 跟 [4.7 cardinality](/backend/04-observability/cardinality-cost-governance/) 的分工：4.7 是治理輸入、4.11 是 pipeline 執行
- 反模式：pipeline 是黑盒、無 self-monitoring；agent 直連 vendor 無 collector 中介；ingest 滿時直接 drop 無告警

## 概念定位

Telemetry pipeline 是把訊號從 service process 帶到查詢與告警面的資料路徑，責任是讓採集、轉換、寫入、儲存與查詢各層都有可觀測的邊界。

這一頁處理的是觀測系統本身的可靠性。當 pipeline 是黑盒，訊號消失時團隊需要額外排查服務是否真的沒事件，或 agent、collector、ingest、query 哪一層失效。

Pipeline 視角的另一個價值是把採集策略跟儲存後端解耦。應用層只需要產生標準訊號，pipeline 處理 schema 轉換、sampling、enrichment、routing 與 vendor 對接；當儲存後端或 vendor 改變時，應用層不必重新 instrument。

## 分層責任與失敗模式

Pipeline 各層責任不同，失敗模式也不同。把 pipeline 視為單一黑盒會讓事故定位停在「訊號不見了」這層觀察，無法回答是哪一層的問題。

| 分層      | 主要責任                        | 典型失敗模式                               | 健康訊號                                |
| --------- | ------------------------------- | ------------------------------------------ | --------------------------------------- |
| Agent     | 從 process / host 抓取原始訊號  | 升版需重啟、container restart 造成短期缺洞 | export queue depth、dropped batches     |
| Collector | 聚合、轉換、enrichment、routing | OOM、配置漂移、規則衝突                    | receiver / processor / exporter 指標    |
| Ingest    | 接收並寫入 buffer 或排隊        | 滿載拒收（429）、區域故障                  | ingestion success rate、queue depth     |
| Storage   | 保留資料、支援查詢索引          | 索引膨脹、保留策略誤刪、查詢退化           | storage size、query latency             |
| Query     | dashboard / alert / 即席查詢    | 查詢逾時、aggregate 失真、permission 漂移  | query QPS、p95 latency、permission 拒絕 |

Agent 層的關鍵風險是部署綁定。若 agent 跟應用同進程，升版需要重啟服務；若 agent 是獨立 DaemonSet 或 sidecar，升版可以獨立進行，但要承擔網路與資源額外開銷。Agent 自身故障時，service 看起來健康，dashboard 看起來空，事故指揮會把這個空白誤讀成系統靜默。

Collector 層是 pipeline 最有彈性的地方，也是最容易漏掉自我觀測的地方。OpenTelemetry Collector 的 receiver / processor / exporter 各自有 metrics，部署時要把這些 metrics 自身送回觀測平台。配置漂移是長期維護的主要失敗：sampling 規則改了沒紀錄、attribute 重命名沒同步、tail sampling decision window 縮短，都會讓下游看到的訊號跟以前不同。Collector 的三種部署位置（agent / gateway / sidecar）與 pipeline 設計細節見 [OTel Collector 部署模式](/backend/04-observability/vendors/opentelemetry/collector-deployment-patterns/)。

Ingest 層的失敗模式集中在容量邊界。當 vendor 端 quota 觸發或內部 queue 滿，ingest 會回 429 或直接丟棄；應用層通常無感、dashboard 顯示流量下降。這層需要把拒收事件本身變成告警訊號、讓事故定位即時看到拒收量、避免靠事後對賬發現。

Storage 跟 query 層的失敗多半是漸進式：保留策略誤刪、查詢隨時間退化、索引隨流量膨脹。這類失敗不會在當下觸發告警，要靠週期性審視 storage size、query latency 與 retention compliance 才能發現。

## Buffer 與 Backpressure

Buffer 是 pipeline 吸收瞬時尖峰的緩衝，責任是讓 collector 跟 ingest 在後端短暫故障或速率不足時仍保住高價值訊號。

- **In-memory queue**：吸收秒級尖峰、容量小、process 重啟會丟。
- **Persistent queue**（local disk、Kafka）：吸收分鐘到小時級積壓、有持久性、需要額外運維成本。
- **Spillover storage**（S3 等冷儲存）：當 hot path 滿載時，把低優先訊號暫存到便宜後端、之後 replay。

Backpressure 策略決定 buffer 滿時的行為。`block` 策略會讓上游採集慢下來、可能影響應用；`drop oldest` 跟 `drop newest` 各自影響 timeline 的開始或結束；`sample-by-priority` 則保留錯誤、長尾與低流量樣本、丟棄一般成功 request。Buffer 跟 backpressure 策略要在容量規劃階段顯式設定、進 release flow、避免事故時臨時拍定。

Buffer 對事故判讀的影響是 freshness。當 buffer 累積分鐘級資料時，dashboard 看到的指標其實落後當前狀態；incident commander 看到 error rate 下降時，需要知道是真的恢復還是 buffer 尚未排空。把 buffer depth 跟 ingest delay 暴露成 dashboard 指標，能避免事中決策建立在過期資料上。

Buffer 跟 backpressure 怎麼選：低延遲容忍 + 容量充足的場景用 in-memory queue + `drop oldest`（保留最新狀態）；高訊號完整性需求（例：audit log、事故證據）用 persistent queue + `block` 或 `sample-by-priority`；高流量爆量但允許部分遺失（例：debug log）用 spillover storage + `drop newest`。事故時的回退路徑是「在 backpressure 政策中先標明哪類訊號絕對保留、哪類訊號可丟」、避免事故當下臨時決定。

## OpenTelemetry Collector 的中介定位

OpenTelemetry Collector 把採集、轉換與 routing 從應用程式抽離，責任是讓觀測 vendor 跟採集 SDK 各自演進。

Collector 在 pipeline 中扮演三個角色：

1. **Vendor-neutral 中介**：應用層只需 export OTLP，collector 端決定要不要把資料同時送到多個後端（Datadog、Honeycomb、self-hosted Prometheus）。切換 vendor 時不需要改應用層。
2. **Schema / sampling 集中治理**：attribute 重命名、敏感欄位 redaction、tail sampling decision、cardinality 限制都集中在 collector，不分散在每個服務。
3. **Topology 適配層**：collector 可以部署為 sidecar（與應用同 Pod）、DaemonSet（每個 node 一份）或 gateway（集中接收）。不同部署形態適合不同規模與隔離需求，並不互斥；大型部署常見「應用 → sidecar → cluster gateway → 後端」的多級拓樸。

對應 [4.C5 Cloud Trace OTLP 導入](/backend/04-observability/cases/cloud-trace-otlp-adoption/)：標準化傳輸協定降低跨環境的 instrumentation 重複，揭露「資料通道標準化」是觀測平台轉換的常見起點。對應 [4.C6 ADOT on EKS 管線遷移](/backend/04-observability/cases/adot-eks-observability-pipeline-migration/)：多代理混用在規模化時放大配置漂移，揭露 collector 集中治理的營運價值。兩個案例的具體實作差異留給原案例，本章關注的是 collector 在 pipeline 中的責任邊界。

## 觀測遷移的執行順序

觀測遷移的執行順序決定短期雙軌成本能否轉化為長期語意一致性。把替換風險限制在採集中介層、是先換 collector / agent、再換應用層 instrumentation 的設計理由。

可重複套用的順序是先換採集中介、再換採集點：

1. **先換 collector / agent**：把 collector 從 vendor-specific 換成 vendor-neutral（如 OTel Collector），同時保留舊 vendor 的 exporter，讓資料同時送到新舊後端。這層替換對應用層無感，可以快速完成。
2. **建立雙軌對照**：以新舊後端對照 SLI 是否一致（query 設計、偏差閾值、退出條件等對照細節由 [4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/) 處理）、差異超過閾值時停止下一步。
3. **逐步改應用端 instrumentation**：把應用層的 vendor-specific SDK 換成 OTel SDK，分服務分批進行。每批切換後重跑對照驗證。
4. **以對照驗證進入 release gate**：在 release pipeline 加上「新舊管線 SLI 偏差」檢查，作為遷移階段的閘門。對照穩定後才能關閉舊管線。

執行順序的設計理由：collector 是 vendor-neutral 抽象、可以雙軌並存承受對照成本；應用層 instrumentation 改動會跨眾多 service team、變更面廣、要在 collector 對照穩定後才大規模推進。把次序反過來容易在 instrumentation 全面改完才發現 collector 抽象有缺失、被迫重做。

對應 [4.C4 X-Ray 到 OpenTelemetry 轉換](/backend/04-observability/cases/xray-to-opentelemetry-migration/)：揭露「先 collector 後 instrumentation」的階段切換方向。對應 [4.C7 Datadog OTel 相容遷移實務](/backend/04-observability/cases/datadog-otel-migration-practice/)：揭露「雙軌期成本跟語意漂移是遷移期主要風險」（單一 agent 安裝是次要議題）。本章關注的是執行順序，schema drift 跟資料品質的對照驗證細節由 [4.17](/backend/04-observability/telemetry-data-quality/) 處理。

## 規模差異下的遷移節奏

遷移節奏由團隊規模、可承受雙軌成本、配置漂移風險與治理成熟度共同決定。本段聚焦遷移期的節奏取捨；常態 ownership 配置由 [4.18 規模差異下的角色配置](/backend/04-observability/observability-operating-model/#規模差異下的角色配置) 處理，兩者 lens 不同。

對應 [4.C10 規模差異下觀測遷移](/backend/04-observability/cases/contrast-observability-rollout-by-scale/)：揭露三種規模團隊的失敗模式骨架；以下三段的具體操作做法均屬通用工程知識展開、case 本身只列方向。

小團隊的核心風險是雙軌維護消耗人力。同時看兩套 dashboard、雙倍 alert noise、雙倍 on-call 負擔，很容易讓遷移本身拖累業務維運。小團隊適合用「短期對照、快速收斂」策略：把對照期壓到一個迭代週期內，固定一個服務作為先導，把問題在小範圍內收斂，再快速複製到其他服務。

中型團隊的失敗模式集中在 schema 漂移。服務數量增加後，attribute 命名一致性、service name 規約、label cardinality 邊界容易在雙軌期擴散。中型團隊要在遷移開始前先固化 semantic convention，並在 collector 層自動校驗；不固化會在遷移後拼湊出多套互相矛盾的 dashboard。

大型團隊的主要失敗集中在治理面：collector 拓樸（sidecar / DaemonSet / gateway 的選擇）、sampling 政策、成本分攤、tenant 隔離都會在遷移後顯著影響成本與告警品質。大型團隊用「pilot region 先行、其他 region 批次跟進」策略、把 collector 配置版本化、變更接到 release gate。大型團隊的回退單位通常是 region 或 tenant 群、不是整體切回。

三類團隊的共同教訓是：先決定「何時可以關閉舊管線」的退出條件，再開始遷移。沒有退出條件的雙軌會無限期延長，最後在成本壓力下被動關閉，反而失去對照驗證的能力。

## 遷移漂移的回退判讀

漂移回退的責任是把降級決策權跟資料採集分離、讓回退保留可分析的對照證據。直接關閉新管線會失去漂移原因的線索、後續再遷移容易出同樣的事故。

對應 [4.C9 OTel 遷移訊號漂移反例](/backend/04-observability/cases/failure-otel-migration-signal-drift/)：揭露遷移失敗的主要型態是語意漂移、回退要保留對照證據。

漂移發生時，主要訊號是「兩套儀表板看似都有資料、但對同一事故的判讀不同」。新舊管線對同一服務的 error rate 長期偏離、missing span 或 missing metric 比例上升、alert 噪音增加但事故量沒對應增加，都是漂移在 pipeline 層的表現。

回退判讀的核心是分辨「遷移問題」跟「服務問題」。比較穩定的回退節奏：

1. 先停止讓新管線主導告警跟 SLO 判定，把告警入口切回舊管線。
2. 保留新管線採集、但只作為對照證據，不參與決策。
3. 用對照資料找出語意漂移點（attribute 名稱、sampling 規則、aggregation 視窗），分項修正。
4. 修正後重新進入雙軌對照、確認偏差收斂、再讓新管線恢復主導。

這個流程把回退視為降級決策權的釋放、而非整體關閉訊號採集。把回退做成可重播流程，下次遷移才能避免在錯誤訊號上做服務回退。

## Multi-tenant 與 Quota

Pipeline 的多租戶治理責任是讓單一服務或團隊的爆量不會拖累其他租戶。沒有租戶隔離時，單一服務的 cardinality 爆炸或 sampling 失控會直接耗盡 pipeline 容量。

可操作的隔離手段：

- **Ingestion quota per tenant**：限制單一服務的 ingest rate，超過時觸發降級或退單。
- **Buffer 與 storage 分區**：高優先 tenant 使用獨立 buffer 或 storage shard，避免 noisy neighbor。
- **Sampling 政策 per tenant**：成本敏感 tenant 走較高採樣比例，關鍵 tenant 走 minimum sample floor。
- **Cost attribution**：把 ingestion、storage、query 成本拆到 tenant，回到 [4.15 cost attribution](/backend/04-observability/cost-attribution/)。

Quota 觸發時的告警設計比 quota 本身更重要。沒有告警的 quota 等於沒有 quota，因為觸發後訊號靜默，事故定位會把靜默誤讀為系統穩定。

## 讀取路徑作為 pipeline 的延伸

Pipeline 的分層敘事（agent → collector → ingest → storage → query）在 query 這層停得太早。寫入路徑的資料從 agent 流到 storage 是單向的；讀取路徑從 query engine 向 storage 發起請求，方向相反、效能瓶頸不同、治理責任也不同。把 query 視為 pipeline 的終端消費者而非獨立系統，才能完整理解觀測資料的生命週期。

### Query engine 的責任邊界

Query engine 在 pipeline 中的責任是把儲存層的資料轉換成使用者可操作的回應。這包括 query planning（決定掃描哪些 shard、哪些 tier）、聚合計算（rate / sum / quantile）、結果快取與 query 排程。

Query engine 的設計取捨跟儲存層不同。儲存層追求寫入吞吐與持久性；query engine 追求查詢延遲與併發能力。兩者獨立擴展 — 寫入量大但查詢量小的場景，storage 需要更多容量但 query engine 不需要；反過來，dashboard 多但寫入量穩定的場景，query engine 需要更多 CPU 但 storage 不需要。

### Query-time 的資源隔離

Query engine 服務三種查詢模式：alert rule evaluation（系統關鍵、定期、不可延遲）、dashboard 刷新（高頻、穩定、可容忍短暫延遲）、即席診斷（偶發、突增、事故中最需要低延遲）。三者搶同一個 query engine 時，穩定的背景負載會擠壓突發的即席查詢。

資源隔離的可操作方式：

- **Query priority**：alert evaluation 最高、即席查詢次之、dashboard 最低。Alert 不能因為 dashboard 重查詢排隊而漏發。
- **Query queue 分離**：不同類型的查詢進不同的 queue，各自有併發上限。Thanos / Mimir 的 query-frontend 支援 query 分類與排程。
- **Query timeout 差異化**：alert evaluation 設短 timeout（跑不完就是問題）、即席查詢設中等 timeout、dashboard 的大範圍查詢允許較長 timeout。
- **Query cost estimation**：在查詢執行前估算掃描量，超過閾值的查詢降級或拒絕，避免單一 heavy query 拖垮整個 query engine。

### Buffer lag 對查詢 freshness 的影響

寫入面的 buffer lag 會直接影響讀取面的 freshness。當 collector 或 ingest 端有分鐘級的 buffer 累積，query engine 讀到的是延遲過的資料。Dashboard 顯示的 error rate 可能反映的是兩分鐘前的狀態；incident commander 看到 error rate 下降，可能是 buffer 開始排空而非服務真的恢復。

把 buffer lag 轉成查詢面的可見指標是基本的設計要求。在 dashboard 上顯示「資料延遲：目前最新資料點是 N 秒前」，讓讀取者知道自己看到的資料有多新。當 lag 超過告警閾值，除了觸發 pipeline 健康告警外，dashboard 本身也應該標示警告狀態。

跨訊號類型的查詢設計見 [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)。

## 核心判讀

判讀 telemetry pipeline 時，先看每一層是否有健康訊號，再看滿載時是否能降級。

重點訊號包括：

- agent、collector、ingest、storage、query 是否各自有 SLI
- buffer 與 backpressure 是否能保住高價值訊號
- multi-tenant quota 是否能隔離單一服務爆量
- collector 是否保留 vendor-neutral 的轉換空間
- 遷移期是否有雙軌對照、是否有退出條件

## 判讀訊號

- 訊號間歇性消失、需要人工判斷是 pipeline 還是 service 問題
- agent 升版需要 service 重啟、運維成本高
- ingest 拒收（429）發生時、應用層無感
- 切換 vendor 需要改所有 service 的 instrumentation
- pipeline 自身無 SLI、健康度靠經驗判斷
- 遷移期雙軌維護過久、退出條件不明

## 反模式

| 反模式                     | 表面現象                      | 修正方向                                  |
| -------------------------- | ----------------------------- | ----------------------------------------- |
| Pipeline 是黑盒            | 訊號消失時靠經驗判斷層級      | 每層暴露 SLI、量化 self-monitoring        |
| Agent 直連 vendor 無中介層 | 切換 vendor 要改所有應用層    | 加 collector 作為 vendor-neutral 中介     |
| Ingest 拒收靜默            | 429 觸發但應用層 / 告警都無感 | 把拒收事件變成告警與 dashboard 指標       |
| 雙軌無退出條件             | 遷移期無限延長、成本不斷雙倍  | 預設退出 SLI 偏差閾值、加入 release gate  |
| 配置漂移無版本控制         | collector 規則改了沒紀錄      | collector 配置進 git、變更走 release flow |

## 交接路由

- [4.7 cardinality / cost](/backend/04-observability/cardinality-cost-governance/)：pipeline 各層的 quota
- [4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/)：雙軌對照的資料品質判讀
- [4.18 operating model](/backend/04-observability/observability-operating-model/)：collector / pipeline 的 ownership 邊界
- [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)：讀取路徑的系統設計與資源治理
- [05 部署](/backend/05-deployment-platform/)：collector 部署形態（DaemonSet / sidecar / gateway）
- [6.4 chaos](/backend/06-reliability/)：pipeline 故障模擬作為 chaos 場景
- [4.15 cost attribution](/backend/04-observability/cost-attribution/)：pipeline 各層的成本歸屬
