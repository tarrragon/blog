---
title: "Backend 服務實務指南"
date: 2026-04-22
description: "用跨語言教學路線整理資料庫、快取、訊息佇列、觀測、部署、可靠性、資安、事故與容量等後端服務能力"
weight: 34
tags: ["backend"]
---

Backend 教材的核心目標是教讀者理解後端服務如何共同支撐一個 production system。資料庫、快取、訊息佇列、觀測平台、部署平台、可靠性驗證、資安資料保護、事故處理與容量規劃，各自承擔一段服務責任；本教材把這些責任整理成可學習、可操作、可演進的跨語言知識路線。

服務能力、風險、成本與決策是理解後端服務的必要概念框架。讀者學資料庫時需要知道 transaction、schema migration、replication lag 與資料修復；學快取時需要知道 freshness、origin protection、eviction 與 hot key；學 queue 時需要知道 delivery、processing、replay 與 idempotency。這些判準服務教學目標：讓讀者能看懂一個後端問題該交給哪類能力處理，並理解多個能力如何串接。

語言教材負責各自的語法、標準庫、並發或非同步模型、測試方法與 interface / [protocol](/backend/knowledge-cards/protocol/) 邊界；Backend 教材負責「應該被 application interface 隔離」的外部服務能力。Go、Python 或其他後端語言可以各自說明如何定義抽象邊界、處理取消與逾時、回傳錯誤、寫 fake 或 [contract](/backend/knowledge-cards/contract/) test；Backend 章節則說明 SQLite、PostgreSQL、Redis、RabbitMQ、[broker](/backend/knowledge-cards/broker)、[migration](/backend/knowledge-cards/migration)、[metrics](/backend/knowledge-cards/metrics)、tracing、Kubernetes、identity、permission、[TLS / mTLS](/backend/knowledge-cards/tls-mtls/)、[WAF](/backend/knowledge-cards/waf/)、[Secret Management](/backend/knowledge-cards/secret-management/)、[Audit Log](/backend/knowledge-cards/audit-log/) 等具體技術如何運作。

Backend 是多個後端語言系列共用的教學層。未來若新增 frontend、data engineering、machine learning、mobile 或其他非後端主題，也可以用同樣方式把共用實作知識抽成獨立資料夾，讓特定語言教材保留在語言本身的能力邊界。

## 總體教學設計

Backend 教材用三層學習結構組織內容。第一層是心智模型，先讓讀者理解資料、快取、事件、觀測、部署、驗證、資安、事故與容量分別承擔什麼責任；第二層是服務路徑，用一條具體業務流程串起多個模組的 artifact 與交接；第三層是具體服務與工具，討論 PostgreSQL、Redis、Kafka、Kubernetes、PagerDuty、k6 等服務如何落到真實操作。

| 層級     | 教學責任                                                               | 主要入口                                                                                                                                                                           |
| -------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 心智模型 | 建立服務分類、責任邊界與共同術語                                       | [模組零](/backend/00-service-selection/) + [前置知識卡片](/backend/knowledge-cards/)                                                                                               |
| 服務路徑 | 用同一條業務流程演練資料、快取、事件、觀測、部署、驗證、資安與事故交接 | [0.15 後端實作教學大綱](/backend/00-service-selection/implementation-teaching-outline/) + [0.16 服務路徑細綱](/backend/00-service-selection/service-path-implementation-outlines/) |
| 真實服務 | 把分類語言落到 vendor / platform / tool 的能力、成本與遷移             | [0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/) + 各模組 `vendors/`                                                                  |

這三層對應三種讀者問題。讀者想知道「這是什麼問題」時，先讀心智模型；想知道「一個服務流程怎麼把多個能力接起來」時，讀服務路徑；想知道「具體要選哪個工具、怎麼遷移」時，再進入真實服務與 vendor 頁。

### 學習路線

Backend 教材可以依讀者目的分成六條路線。每條路線都有起點、主要順序與完成判準，讓讀者不用從能力地圖自行推導閱讀順序。

| 路線                       | 適合讀者                              | 建議順序                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 讀完能做什麼                                                                         |
| -------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| 系統心智模型               | 想理解後端服務分工                    | 00 → knowledge cards → 01 / 02 / 03 的共同觀念                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 能把需求分類成正式狀態、暫存副本、非同步交接、觀測、部署或可靠性問題                 |
| API 到資料流               | 想設計 API 背後的資料、快取與事件流程 | 01 Database → 02 Cache → 03 Queue → 04 Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | 能說明一次 checkout 如何跨 DB、cache、queue 與 evidence package                      |
| Production 操作            | 想學上線、觀測、驗證與事故閉環        | 04 Observability → 05 Deployment → 06 Reliability → 08 Incident                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | 能把 release、alert、gate、incident decision log 與 write-back 串成操作閉環          |
| Security / Data Protection | 想理解權限、秘密、資料、偵測與回應    | 07 Security → 04 audit evidence → 06 control validation → 08 security incident                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 能從身份、資料、入口、秘密與 audit evidence 判讀控制面                               |
| Vendor / Migration         | 已懂分類、要比較工具或遷移            | 對應模組主章 → `vendors/` → migration playbook → cases                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 能先判斷分類責任，再比較具體服務、操作成本與遷移風險                                 |
| 規模成長                   | 已能做出「能跑」的 SaaS、要學「能撐」 | [0.0](/backend/00-service-selection/backend-demand-taxonomy/) → [0.18](/backend/00-service-selection/service-decomposition-boundaries/) → [9.13](/backend/09-performance-capacity/scaling-axes/) → [1.13](/backend/01-database/query-anti-patterns/) → [1.1](/backend/01-database/high-concurrency-access/) → [2.2](/backend/02-cache-redis/cache-aside/) → [5.9](/backend/05-deployment-platform/edge-cdn-static-distribution/) → [03 Queue](/backend/03-message-queue/) → [9.11](/backend/09-performance-capacity/peak-event-readiness/) | 能描述一個服務從一臺機器演進到多區域多服務的時序、各階段該撞哪面牆、要先補哪一塊能力 |

這些路線共享同一組後端語言。讀者可以只走一條，也可以從「系統心智模型」開始，再按工作需求轉入 API、production、security、vendor 或規模成長專題。

#### 規模成長路線的閱讀重點

規模成長路線回答的核心問題是「為什麼系統會被迫長出新的架構」。每一階段的轉折都來自一個具體的撞牆訊號：單一服務承載不了業務分化（拆服務）、單機規格撞天花板（水平擴展）、應用層 query 變慢（反模式優化）、單一資料庫成為瓶頸（高併發策略 + 讀寫分離）、origin 被流量打爆（邊緣分發）、同步呼叫卡住事務流（非同步化）、可預期高峰需要事前準備（peak event readiness）。

這條路線跟「API 到資料流」路線的差別：API 路線教讀者「怎麼把功能做出來」，規模路線教讀者「做出來之後怎麼撐住」。兩條路線可以分開讀、也可以順序讀，建議寫完第一個 MVP 後就回到規模路線盤點。

### 貫穿式案例：Checkout 服務演進

貫穿式案例的責任是把平行模組串成同一個服務演進路徑。本系列使用簡化的 checkout / order / payment / notification 流程作為主案例：使用者建立訂單、付款服務回應、商品或價格資料被快取、事件送到下游通知與報表、服務上線時產出觀測與驗證證據，事故發生時留下決策紀錄並回寫改善。

| Episode | 問題                            | 主要模組          | 主要產物                                                         |
| ------- | ------------------------------- | ----------------- | ---------------------------------------------------------------- |
| E1      | 新增付款狀態欄位                | 01 + 04 + 08      | migration plan、validation query、incident decision route        |
| E2      | 商品價格快取失效與回源保護      | 02 + 04 + 06      | cache evidence、origin protection gate、warmup plan              |
| E3      | 訂單事件 consumer 失敗與 replay | 03 + 06 + 08      | idempotency evidence、DLQ handling、replay runbook               |
| E4      | Checkout service rollout        | 05 + 04 + 08      | rollout plan、canary evidence、drain signal、rollback condition  |
| E5      | Payment provider timeout 變更   | 06 + 04 + 09      | release gate、SLO evidence、capacity baseline                    |
| E6      | Webhook secret rotation         | 07 + 04 + 08      | scope map、audit evidence、rollback window                       |
| E7      | Flash-sale peak readiness       | 09 + 02 + 03 + 06 | workload model、saturation evidence、queue / cache capacity gate |

每個模組可以獨立閱讀；貫穿式案例提供跨模組記憶。讀者看到資料庫章節時，知道它處理 E1 的正式狀態演進；看到 queue 章節時，知道它處理 E3 的跨程序交接；看到事故章節時，知道它收斂 E1、E3、E4、E6 的決策與回寫。

### 教材完成判準

Backend 教材的完成判準是讀者能沿著一條路線走完並做出可操作判斷。內容覆蓋率、案例數與 vendor 數量只是素材面進度；教學面要看讀者能否取得起點、順序、案例與下一步路由。

| 判準            | 具體訊號                                                                      |
| --------------- | ----------------------------------------------------------------------------- |
| 學習路線成立    | 入口頁能依目的給出閱讀順序與完成判準                                          |
| 概念梯度成立    | 讀者先建立分類語言，再進入服務路徑，最後看 vendor / migration                 |
| 貫穿案例成立    | 多個模組能回到同一條 checkout 服務演進路徑                                    |
| Artifact 可演練 | Evidence package、release gate、decision log、rollback condition 能被讀者填寫 |
| 案例能回寫      | 07 / 09 案例庫能支撐主章判讀，也能揭露缺口                                    |
| Vendor 回到分類 | 具體服務頁先回扣分類責任，再比較功能、成本與遷移                              |

這套設計來自三張寫作反省卡：[教材目標先於決策框架](/report/teaching-goal-before-decision-frame/)、[教材完整性要用讀者旅程驗證](/report/teaching-completeness-by-learner-journey/) 與 [貫穿式案例是服務教材的教學骨架](/report/throughline-case-as-teaching-spine/)。

## 教材邊界

| 類型       | 放在語言教材                                                                                                                                                                                                            | 放在 Backend 教材                                                                                                                                                                                                                                                                                                                      |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 資料存取   | repository port、interface / [protocol](/backend/knowledge-cards/protocol/)、context / cancellation、error、[contract](/backend/knowledge-cards/contract/) test                                                         | SQLite、PostgreSQL、[transaction](/backend/knowledge-cards/transaction)、[schema migration](/backend/knowledge-cards/schema-migration)、index、[isolation level](/backend/knowledge-cards/isolation-level)                                                                                                                             |
| 快取       | cache port、[TTL](/backend/knowledge-cards/ttl) 概念、資料複製邊界、失效策略的程式邊界                                                                                                                                  | Redis 資料型別、[eviction](/backend/knowledge-cards/eviction)、distributed lock、[cache aside](/backend/knowledge-cards/cache-aside)、[pub/sub](/backend/knowledge-cards/pub-sub)                                                                                                                                                      |
| 訊息傳遞   | channel / [queue](/backend/knowledge-cards/queue) abstraction、[backpressure](/backend/knowledge-cards/backpressure)、publisher port、processor、[idempotency](/backend/knowledge-cards/idempotency) interface          | RabbitMQ、NATS、Kafka、Redis Streams、[ack/nack](/backend/knowledge-cards/ack-nack)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue)、[consumer group](/backend/knowledge-cards/consumer-group)                                                                                                                        |
| 可觀測性   | 標準 logger、執行環境訊號、diagnostics endpoint、[trace context](/backend/knowledge-cards/trace-context) 邊界、錯誤分類欄位                                                                                             | [log](/backend/knowledge-cards/log) aggregation、Prometheus、OpenTelemetry、trace、[dashboard](/backend/knowledge-cards/dashboard)、[alert](/backend/knowledge-cards/alert)                                                                                                                                                            |
| 部署平台   | [graceful shutdown](/backend/knowledge-cards/graceful-shutdown)、health/[readiness](/backend/knowledge-cards/readiness)、signal handling、resource limit、[failover](/backend/knowledge-cards/failover) hook 的程式設計 | Kubernetes、systemd、[load balancer](/backend/knowledge-cards/load-balancer/)、[container](/backend/knowledge-cards/container/) image、[service discovery](/backend/knowledge-cards/service-discovery/)                                                                                                                                |
| 可靠性驗證 | unit test、table-driven / parameterized test、race / async test、integration test、故障路徑測試                                                                                                                         | [CI pipeline](/backend/knowledge-cards/ci-pipeline)、[load test](/backend/knowledge-cards/load-test)、fuzz campaign、chaos testing、環境治理                                                                                                                                                                                           |
| 資安保護   | [Request Middleware](/backend/knowledge-cards/middleware/)、policy interface、error mapping、redaction helper、security test                                                                                            | identity、[authorization](/backend/knowledge-cards/authorization/)、[TLS / mTLS](/backend/knowledge-cards/tls-mtls/)、[WAF](/backend/knowledge-cards/waf/)、[Secret Management](/backend/knowledge-cards/secret-management/)、[Audit Log](/backend/knowledge-cards/audit-log/)、[data masking](/backend/knowledge-cards/data-masking/) |
| 效能容量   | algorithm、hot path、micro benchmark、runtime profiler 解讀、並發程式邊界                                                                                                                                               | workload model、production traffic replay、k6 / JMeter / Gatling / Locust、saturation metric、headroom budget、capacity planning、cost per request                                                                                                                                                                                     |

## 教學模組

### [前置知識卡片](/backend/knowledge-cards/)

用原子化卡片整理 [source of truth](/backend/knowledge-cards/source-of-truth)、transaction、migration、CDC、[backfill](/backend/knowledge-cards/backfill)、[cutover](/backend/knowledge-cards/cutover-switchover)、[timeout](/backend/knowledge-cards/timeout)、backoff、[jitter](/backend/knowledge-cards/jitter)、[retry storm](/backend/knowledge-cards/retry-storm)、[load shedding](/backend/knowledge-cards/load-shedding)、[bulkhead](/backend/knowledge-cards/bulkhead)、[fallback](/backend/knowledge-cards/fallback)、TTL、[cache warmup](/backend/knowledge-cards/cache-warmup)、[singleflight](/backend/knowledge-cards/singleflight)、broker、[consumer lag](/backend/knowledge-cards/consumer-lag)、[prefetch](/backend/knowledge-cards/prefetch)、[redelivery](/backend/knowledge-cards/redelivery)、[partition](/backend/knowledge-cards/partition)、[offset](/backend/knowledge-cards/offset)、idempotency、outbox、backpressure、[log schema](/backend/knowledge-cards/log-schema)、metrics、trace、[SLO](/backend/knowledge-cards/sli-slo)、[error budget](/backend/knowledge-cards/error-budget)、[authorization](/backend/knowledge-cards/authorization)、[BOLA](/backend/knowledge-cards/bola-idor)、[mass assignment](/backend/knowledge-cards/mass-assignment)、[data masking](/backend/knowledge-cards/data-masking)、[Secret Management](/backend/knowledge-cards/secret-management/)、[TLS / mTLS](/backend/knowledge-cards/tls-mtls/)、[Audit Log](/backend/knowledge-cards/audit-log/) 與 [Website Certificate Lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/) 等後端 domain knowhow。這些卡片負責補足服務選型文章中的先備知識，讓章節可以專注在需求判讀與服務取捨。

### [模組零：後端需求分析與服務選型](/backend/00-service-selection/)

整理後端需求分類、流量形狀、資料量、失敗代價、成本模型、錯誤定位、觀測訊號、備援切換與服務能力地圖，再從需求類型判斷資料庫、快取、訊息佇列、觀測平台與部署平台的選型方向。

### [模組一：資料庫與持久化](/backend/01-database/)

整理 relational [database](/backend/knowledge-cards/database)、embedded database、transaction、migration、repository [adapter](/backend/knowledge-cards/repository-adapter/) 與資料一致性。

### [模組二：快取與 Redis](/backend/02-cache-redis/)

整理 cache aside、TTL、eviction、Redis data structure、distributed lock、pub/sub 與快取一致性。

### [模組三：訊息佇列與事件傳遞](/backend/03-message-queue/)

整理 [durable queue](/backend/knowledge-cards/durable-queue)、broker、ack/nack、retry、dead-letter queue、outbox、idempotency 與 consumer 設計。

### [模組四：可觀測性平台](/backend/04-observability/)

整理 structured log aggregation、metrics、tracing、dashboard、alert 與操作診斷流程。

### [模組五：部署平台與網路入口](/backend/05-deployment-platform/)

整理 Kubernetes、systemd、[load balancer](/backend/knowledge-cards/load-balancer/)、[container](/backend/knowledge-cards/container/)、[service discovery](/backend/knowledge-cards/service-discovery/)、[rolling update](/backend/knowledge-cards/rolling-update) 與平台合約。

### [模組六：可靠性驗證流程](/backend/06-reliability/)

整理 CI、load test、fuzz、chaos testing、測試環境與回歸驗證策略。

### [模組七：資安與資料保護](/backend/07-security-data-protection/)

整理權限分級、伺服器防護、資料遮罩、傳輸保護、密鑰管理、稽核追蹤與資料匯出安全。

### [模組八：事故處理與復盤](/backend/08-incident-response/)

整理事故分級、指揮流程、止血回復、通訊節奏、復盤閉環與演練機制。

### [模組九：效能工程與容量規劃](/backend/09-performance-capacity/)

整理壓測理論、workload modeling、壓測工具選型、saturation discovery、瓶頸定位、容量規劃、成本邊界、效能可觀測性與改進閉環。跟模組六是 sibling 工程紀律：06 看「失敗模式如何被驗證」、09 看「正常負載如何被量化與規劃」。附 31 個 AWS / GCP / Azure 雲端公開實戰案例庫、覆蓋售票 flash-sale、極端可預期峰值、事件型峰值、surge、低延遲持續、持續成長六種負載形狀。

## 與語言教材的關係

Backend 教材提供跨語言的服務概念與操作語意。語言教材可以回連 Backend，說明特定語言如何實作 repository port、publisher port、cache interface、[Request Middleware](/backend/knowledge-cards/middleware/)、async worker 或 observability boundary；Backend 章節本身應保持獨立，讓 Go、Python、Node.js、Java、C#、PHP、Rust 或其他後端語言都能使用同一套服務判斷。

Backend 章節討論具體服務時，應加入跨語言適配評估。這個評估讓讀者從執行環境、語言生態與抽象邊界理解服務使用方式，並取代特定語言教材作為前置依賴。

1. 這個服務需要語言端提供哪些抽象邊界，例如 interface、protocol、[Integration Adapter](/backend/knowledge-cards/adapter/)、[Request Middleware](/backend/knowledge-cards/middleware/)、worker 或 client wrapper。
2. 哪些執行環境特性會影響服務使用方式，例如 thread model、event loop、async/await、goroutine、process model、GC、[connection pool](/backend/knowledge-cards/connection-pool) 或 cancellation。
3. 哪些語言特性適合這個服務，例如明確 context 傳遞、型別化錯誤、成熟 ORM、生態套件、背景 worker 框架或 observability SDK。
4. 哪些語言特性會形成風險，例如隱式全域狀態、阻塞 I/O 混入 event loop、連線池生命週期不清楚、例外處理邊界模糊或套件抽象過厚。
5. 語言教材若需要示範實作，應由語言教材回連 Backend；Backend 則保持跨語言概念完整。

這個方向讓 Backend 保持可重用：它先說明服務如何選型、如何使用、如何操作、如何承擔成本；各語言系列再各自說明如何接上這些服務。

## 與案例的關係

Backend 案例應從服務需求出發。高併發、長連線、事件處理、資料庫、雲端基礎設施、資安與可觀測性都可以用跨語言案例說明；案例的責任是提供需求情境，服務章節的責任是說明後端能力本身。

### 案例庫承接策略：用 07 + 09 案例庫擴展模組內容

Backend 各模組（01-08）的章節寫作、把 [07 資安資料保護](/backend/07-security-data-protection/) 跟 [09 效能容量](/backend/09-performance-capacity/) 兩個案例庫當成 *跨模組材料庫* 使用、不是各自獨立寫案例。寫每篇技術章節時、先盤點 07/09 哪些案例能 *承接* 該章節的主題、再決定要 link 哪些、要重述哪些、要新建案例補哪些缺口。

兩個案例庫的責任分工：

- **09 案例庫**：以 *效能 / 容量 / 規模* 為主軸的真實工程案例（35+ 個）、涵蓋 DynamoDB 億級 RPS、Aurora 跨 region、Cosmos DB Black Friday、Spanner planetary scale、KeyDB cross-cloud、Tixcraft flash sale 等。給技術章節提供「規模上限參考」、「設計取捨對照」、「失敗模式對照」。
- **07 案例庫**：分主案例（10+ 個）跟紅隊案例（49+ 個、分 data-exfiltration / edge-exposure / identity-access / supply-chain 四類）。給技術章節提供「攻擊鏈到該技術層的路徑」、「事故代價對照」、「控制面失效模式」。

承接的最小要求：

1. **每篇技術章節都要有「案例對照」段**：表格 + 每案的「跟本章關係」一句話、不是純列連結。
2. **案例的引用要在敘事中分散**：不只在文末列表、文中討論特定模式時就 inline link、讓讀者邊讀邊看到實證。
3. **盤點未承接案例是 backlog 項目**：寫完一個模組、跑一次 grep 看 09 / 07 紅隊案例庫剩下哪些沒 link、判斷是否該補。

判斷案例是否該承接的條件：

- **直接相關**：案例的核心議題就是本章技術（例：DynamoDB partition key → 1.10 KV 容量）→ 必引
- **對照相關**：案例展示了 *對立* 設計取捨（例：SeatGeek 明確排隊 vs Tixcraft 隱性緩衝）→ 強建議引、能展示判讀
- **失敗模式相關**：案例揭露了本章技術的失敗代價（例：MOVEit SQL injection → 1.5 紅隊）→ 必引
- **間接相關**：案例提到本章技術但不是核心（例：Niantic 提到 DB 但主要是 K8s scaling）→ 可不引、避免模板化

不承接的條件：

- 案例本質屬於別的模組（例：Snap KeyDB 屬 02 cache、不屬 01 DB）
- 案例對本章只是 passing reference、沒 substantive 對照價值
- 引用會把表格塞爆但每個只有一句話的形式化承接（情境優先於模板原則、見上）

實例：[01 資料庫模組](/backend/01-database/) 已承接 27/35 個 09 案例 + 6/10 個 07 主案例 + 6 個 07 紅隊案例。剩下未承接的多屬其他模組（K8s 屬 05、cache 屬 02、edge VPN CVE 屬 07 自身）。各模組寫作完成後做同類盤點、能確認案例庫被當成共享資源、不重複勞動、也不漏接。

## 教學寫作方向

Backend 教學文章以敘事說明為主。每篇先回答「這個能力在真實服務承擔什麼責任」，再展開判讀訊號、風險擴散、決策順序與回寫路由，讓讀者能沿著情境推導出操作判斷。

檢查清單與欄位表在本系列是輔助工具，不是文章主體。它們的責任是收斂判讀，不是取代推理；每一個條目都應回到案例脈絡，說明為何成立、失效時會發生什麼，以及下一步要交給哪個模組。

寫作時優先保留因果鏈：觀測到什麼、如何判讀、做了什麼決策、承擔什麼代價、後續如何修正。當文章只剩條列而缺少因果，讀者會知道要檢查什麼，卻不知道為什麼要這樣檢查。

## 補充知識卡片入口

下列卡片目前尚未從教學文章直接引用，先放在這裡作為補充入口。

| 卡片                                                                                             | 入口     |
| ------------------------------------------------------------------------------------------------ | -------- |
| [Authentication Middleware](/backend/knowledge-cards/authentication-middleware/)                 | 補充入口 |
| [Authorization Middleware](/backend/knowledge-cards/authorization-middleware/)                   | 補充入口 |
| [BOPLA](/backend/knowledge-cards/bopla/)                                                         | 補充入口 |
| [Bucket](/backend/knowledge-cards/bucket/)                                                       | 補充入口 |
| [Cache Prefetching](/backend/knowledge-cards/cache-prefetching/)                                 | 補充入口 |
| [Change Data Capture](/backend/knowledge-cards/change-data-capture/)                             | 補充入口 |
| [Cold Start](/backend/knowledge-cards/cold-start/)                                               | 補充入口 |
| [Competing Consumers](/backend/knowledge-cards/competing-consumers/)                             | 補充入口 |
| [Consumer Capacity](/backend/knowledge-cards/consumer-capacity/)                                 | 補充入口 |
| [Correctness Check](/backend/knowledge-cards/correctness-check/)                                 | 補充入口 |
| [Data Completeness](/backend/knowledge-cards/data-completeness/)                                 | 補充入口 |
| [Dual Write](/backend/knowledge-cards/dual-write/)                                               | 補充入口 |
| [Service Endpoint](/backend/knowledge-cards/endpoint/)                                           | 補充入口 |
| [HTTP Client](/backend/knowledge-cards/http-client/)                                             | 補充入口 |
| [In-Flight Message](/backend/knowledge-cards/in-flight-message/)                                 | 補充入口 |
| [Migration Gate](/backend/knowledge-cards/migration-gate/)                                       | 補充入口 |
| [Notification Adapter](/backend/knowledge-cards/notification-adapter/)                           | 補充入口 |
| [Observability Middleware](/backend/knowledge-cards/observability-middleware/)                   | 補充入口 |
| [Online Migration](/backend/knowledge-cards/online-migration/)                                   | 補充入口 |
| [Projection](/backend/knowledge-cards/projection/)                                               | 補充入口 |
| [Publisher Confirm](/backend/knowledge-cards/publisher-confirm/)                                 | 補充入口 |
| [Queue Contract](/backend/knowledge-cards/queue-contract/)                                       | 補充入口 |
| [Redelivery Loop](/backend/knowledge-cards/redelivery-loop/)                                     | 補充入口 |
| [Replication Lag](/backend/knowledge-cards/replication-lag/)                                     | 補充入口 |
| [Request/Response Protocol](/backend/knowledge-cards/request-response-protocol/)                 | 補充入口 |
| [Rollback Rehearsal](/backend/knowledge-cards/rollback-rehearsal/)                               | 補充入口 |
| [Routing Rule](/backend/knowledge-cards/routing-rule/)                                           | 補充入口 |
| [Security Misconfiguration](/backend/knowledge-cards/security-misconfiguration/)                 | 補充入口 |
| [Shadow Read](/backend/knowledge-cards/shadow-read/)                                             | 補充入口 |
| [Socket](/backend/knowledge-cards/socket/)                                                       | 補充入口 |
| [Soft TTL](/backend/knowledge-cards/soft-ttl/)                                                   | 補充入口 |
| [SSRF](/backend/knowledge-cards/ssrf/)                                                           | 補充入口 |
| [Stream Pipeline](/backend/knowledge-cards/stream-pipeline/)                                     | 補充入口 |
| [Unacked Message](/backend/knowledge-cards/unacked-message/)                                     | 補充入口 |
| [Unrestricted Resource Consumption](/backend/knowledge-cards/unrestricted-resource-consumption/) | 補充入口 |
| [Validation Middleware](/backend/knowledge-cards/validation-middleware/)                         | 補充入口 |
| [Webhook Protocol](/backend/knowledge-cards/webhook-protocol/)                                   | 補充入口 |
| [Write-Behind Cache](/backend/knowledge-cards/write-behind-cache/)                               | 補充入口 |
| [Write-Through Cache](/backend/knowledge-cards/write-through-cache/)                             | 補充入口 |

## 前置知識卡片規範

Backend 文章中的術語只要會影響讀者理解或實作判斷，就應優先抽成前置知識卡片，不以「是否高頻出現」作為必要條件。Source of truth、[transaction boundary](/backend/knowledge-cards/transaction-boundary)、schema migration、timeout、[deadline](/backend/knowledge-cards/deadline)、[exponential backoff](/backend/knowledge-cards/exponential-backoff)、jitter、retry storm、[thundering herd](/backend/knowledge-cards/thundering-herd)、[transient failure](/backend/knowledge-cards/transient-failure)、[partial failure](/backend/knowledge-cards/partial-failure)、[cascading failure](/backend/knowledge-cards/cascading-failure)、load shedding、[token bucket](/backend/knowledge-cards/token-bucket)、[dependency isolation](/backend/knowledge-cards/dependency-isolation)、bulkhead、fallback、[fail fast](/backend/knowledge-cards/fail-fast)、[retry budget](/backend/knowledge-cards/retry-budget)、TTL、eviction、broker、consumer lag、dead-letter queue、[replay runbook](/backend/knowledge-cards/replay-runbook)、[重複投遞](/backend/knowledge-cards/duplicate-delivery)、idempotency、outbox、backpressure、[rate limit](/backend/knowledge-cards/rate-limit)、log schema、metrics、trace context、SLO、authorization、data masking、[secret management](/backend/knowledge-cards/secret-management)、[TLS / mTLS](/backend/knowledge-cards/tls-mtls/)、[website certificate lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/)、[certificate rotation and renewal](/backend/knowledge-cards/certificate-rotation-renewal/)、[certificate revocation](/backend/knowledge-cards/certificate-revocation/)、[audit log](/backend/knowledge-cards/audit-log)、[降級](/backend/knowledge-cards/degradation)、[停機](/backend/knowledge-cards/downtime)、readiness 與 graceful shutdown 都是 domain knowhow；它們需要說明系統責任、產品後果、操作訊號與排障方式。

每張卡片應維持一個概念，並至少包含概念位置、可觀察訊號、接近真實網路服務的例子與設計責任。卡片內容要能獨立閱讀；定義只是一個入口，完整卡片要讓讀者理解這個概念在事故、擴容、部署或資料修復時會如何影響決策。

卡片與技術文章必須分離。卡片負責名詞與共同語言；技術文章負責情境判讀、設計取捨與決策順序。章節文章使用「情境、判讀流程、風險代價、設計取捨、最低控制面」結構，並以卡片連結補術語背景，不在文章區重寫卡片格式。

## 暫定章節來源

目前 Backend 目錄先承接多個後端語言都會遇到的外部實作議題：

- 資料庫 transaction、schema migration、isolation level
- durable queue、outbox、idempotency store
- Redis、distributed cache、presence store
- metrics、tracing、log aggregation、OpenTelemetry
- Kubernetes、systemd、[load balancer](/backend/knowledge-cards/load-balancer/)、[container](/backend/knowledge-cards/container/) runtime
- CI、load test、fuzz、chaos testing
- identity、[authorization](/backend/knowledge-cards/authorization/)、[data masking](/backend/knowledge-cards/data-masking/)、[TLS / mTLS](/backend/knowledge-cards/tls-mtls/)、[website certificate lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/)、[Secret Management](/backend/knowledge-cards/secret-management/)、[Audit Log](/backend/knowledge-cards/audit-log/)
- [incident severity](/backend/knowledge-cards/incident-severity)、command model、[escalation policy](/backend/knowledge-cards/escalation-policy)、[rollback strategy](/backend/knowledge-cards/rollback-strategy)、[post-incident review](/backend/knowledge-cards/post-incident-review)
- workload modeling、[saturation point](/backend/knowledge-cards/saturation-point/)、[USE method](/backend/knowledge-cards/use-method/)、[RED method](/backend/knowledge-cards/red-method/)、[peak forecast](/backend/knowledge-cards/peak-forecast/)、[headroom budget](/backend/knowledge-cards/headroom-budget/)、[predictive scaling](/backend/knowledge-cards/predictive-scaling/)、[performance budget](/backend/knowledge-cards/performance-budget/)、[latency budget](/backend/knowledge-cards/latency-budget/)

後續撰寫任何語言教材時，凡是涉及具體外部服務操作、部署平台設定或產品選型，都應優先放到 Backend；語言章節只保留足夠說明抽象邊界的最小背景。

## 服務分類開頭規範

每個 Backend 服務分類的 `_index.md` 必須先回答選型問題，再進入實作細節。服務分類與服務實體章節都要把成本權衡視為固定段落；資安限制、流量穩定性、伺服器成本、人力成本與機會成本會共同決定某個服務是否值得引入。

1. 說明這類服務解決哪一種工程問題
2. 列出可觀察需求訊號
3. 舉接近真實網路服務的例子
4. 比較同質服務或相近能力的差異
5. 討論資安限制下的成本權衡
6. 討論選擇此方案的機會成本與替代方案
7. 指向後續實作章節

表格只能作為索引。只要表格列出分類、工具或服務能力，後面就要補對應段落，說明如何辨識、何時選擇、與其他同質服務差在哪裡。

## 服務實體章節規範

每篇討論具體服務實體的章節，例如 PostgreSQL、Redis、RabbitMQ、Kafka、Prometheus、OpenTelemetry、Kubernetes、[WAF](/backend/knowledge-cards/waf/)、[Secret Management](/backend/knowledge-cards/secret-management/) 或 [IAM](/backend/knowledge-cards/iam/)，都必須包含「成本權衡與機會成本」段落。這個段落至少回答：

1. 這個服務降低哪一種風險
2. 在資安限制下會增加哪些設計、審核、遮罩、加密、稽核或權限成本
3. 在高流量、尖峰、長連線或大量資料下會增加哪些伺服器與雲端成本
4. 團隊需要承擔哪些維護、監控、升級、備份、演練與事故處理成本
5. 若選擇更簡單方案，會承擔哪些風險；若選擇更完整方案，會延後哪些產品或工程工作
6. 什麼條件出現時，原本的選型結論應該被重新評估

## 跨語言適配規範

每篇具體服務實體章節都必須包含「跨語言適配評估」段落。這個段落不連到特定語言教材，而是從語言特性評估使用風險：

1. 同步 thread-based runtime 如何管理 connection pool、blocking I/O 與 timeout。
2. async/event-loop runtime 如何避免 blocking client、長時間 CPU work 與 backpressure 失控。
3. goroutine 或 lightweight task runtime 如何限制下游資源，避免把廉價並發轉成昂貴連線壓力。
4. 強型別語言如何表達 schema、錯誤分類與 [contract](/backend/knowledge-cards/contract/) test。
5. 動態語言如何用 protocol、typing、fixture、runtime validation 或 framework convention 保護邊界。
6. 語言生態的 ORM、broker client、observability SDK、security [Security Middleware](/backend/knowledge-cards/security-middleware/) 是否成熟，是否會隱藏重要操作語意。

---

_文件版本：v0.1.0_
_最後更新：2026-04-22_
_系列狀態：分類索引建立中_
