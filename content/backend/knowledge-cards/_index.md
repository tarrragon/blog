---
title: "前置知識卡片"
date: 2026-04-23
description: "用原子化卡片整理後端服務選型前需要理解的 domain knowhow"
weight: -1
---

前置知識卡片的核心目標是把後端服務中的高密度術語拆成可獨立閱讀的 domain knowhow。服務選型文章會使用 broker、consumer lag、dead-letter、replay、降級、停機、readiness 等詞彙；這些詞彙背後都包含產品後果、操作責任與排障方式。

這個模組先建立共同語言。每張卡片只處理一個知識節點，並用「概念位置、可觀察訊號、接近真實網路服務的例子、設計責任」說明它在後端系統中的角色。

## 資料與一致性

| 卡片                                          | 核心問題                           | 常見出現位置                         |
| --------------------------------------------- | ---------------------------------- | ------------------------------------ |
| [Database](database/)                         | 正式狀態如何保存、查詢與保護       | source of truth、transaction、backup |
| [Source of Truth](source-of-truth/)           | 哪個位置承擔正式資料判斷           | database、cache、search index        |
| [Search Index](search-index/)                 | 搜尋體驗如何有獨立讀取模型         | full-text、filter、ranking           |
| [Full-Text Search](full-text-search/)         | 文本檢索如何支援關鍵字與相關性排序 | search、documents、catalog           |
| [Facet Query](facet-query/)                   | 搜尋結果如何提供可篩選聚合維度     | filter、aggregation、UX              |
| [Object Storage](object-storage/)             | 大型檔案如何保存與控管生命週期     | upload、export、backup               |
| [Event Log](event-log/)                       | 歷史事件如何保存與重播             | replay、audit、projection            |
| [Read Model](read-model/)                     | 查詢需求如何有獨立讀取資料形狀     | projection、query model              |
| [Projection](projection/)                     | 來源資料如何轉換成查詢視圖         | events、materialized view            |
| [資料生命週期](data-lifecycle/)               | 資料如何建立、保留、封存與刪除     | retention、audit、export             |
| [資料不一致](data-inconsistency/)             | 多份資料暫時不同步時如何辨識與修復 | cache、replica、eventual consistency |
| [Transaction](transaction/)                   | 一組資料變更如何一起成功或一起回復 | database、commit、rollback           |
| [Transaction Boundary](transaction-boundary/) | 哪些變更要一起成功或回復           | database、unit of work               |
| [Migration](migration/)                       | 系統如何從舊狀態受控移到新狀態     | release、cutover、backfill           |
| [Schema Migration](schema-migration/)         | 資料庫結構如何隨版本安全演進       | release、rollback、migration         |
| [Expand / Contract](expand-contract/)         | 先擴充相容面再收斂舊路徑的遷移做法   | schema migration、online migration   |
| [Migration Gate](migration-gate/)             | 遷移流程如何決定能否進入下一階段   | backfill、correctness check          |
| [Release Gate](release-gate/)                 | 變更如何在正式釋出前通過或阻擋     | error budget、migration、review      |
| [Rollback Rehearsal](rollback-rehearsal/)     | 回滾流程如何在正式事故前演練       | rollback strategy、migration         |
| [Isolation Level](isolation-level/)           | 並發交易彼此看見哪些資料           | transaction、lock、retry             |
| [Connection Pool](connection-pool/)           | application 如何限制下游連線壓力   | database、Redis、broker              |

## 快取與流量

| 卡片                                          | 核心問題                              | 常見出現位置                 |
| --------------------------------------------- | ------------------------------------- | ---------------------------- |
| [Timeout](timeout/)                           | 單一步驟最久可以等待多久              | API、database、broker        |
| [Deadline](deadline/)                         | 整體操作何時必須完成                  | request、job、workflow       |
| [Exponential Backoff](exponential-backoff/)   | 重試間隔如何逐步拉長                  | retry、API、worker           |
| [Jitter](jitter/)                             | 如何分散同步重試與排程尖峰            | retry、TTL、reconnect        |
| [Retry Storm](retry-storm/)                   | 大量重試如何放大下游壓力              | timeout、dependency failure  |
| [Thundering Herd](thundering-herd/)           | 大量工作同時醒來如何形成尖峰          | reconnect、cache、lock       |
| [Transient Failure](transient-failure/)       | 暫時性故障如何影響重試與告警          | network、failover、timeout   |
| [Partial Failure](partial-failure/)           | 局部失效時如何保留整體可用性          | distributed system、fallback |
| [Cascading Failure](cascading-failure/)       | 局部故障如何擴散成整體故障            | dependency、retry、pool      |
| [Load Shedding](load-shedding/)               | 過載時如何主動拒絕低優先工作          | overload、priority           |
| [Token Bucket](token-bucket/)                 | 如何用配額與補充速率控制流量          | rate limit、retry budget     |
| [Dependency Isolation](dependency-isolation/) | 如何避免單一下游耗盡共享資源          | pool、queue、dependency      |
| [Bulkhead](bulkhead/)                         | 如何用資源分艙限制故障擴散            | worker、tenant、pool         |
| [In-Process Channel](in-process-channel/)     | 單一 process 內如何傳遞工作或訊號     | channel、local queue         |
| [Local Worker](local-worker/)                 | 同 process 背景工作的責任與邊界       | background task、shutdown    |
| [Worker Pool](worker-pool/)                   | 如何限制同時處理量                    | worker、background job       |
| [HTTP Client](http-client/)                   | 呼叫外部 HTTP 依賴時如何管理資源      | API、dependency              |
| [Webhook](webhook/)                           | 外部系統回呼事件如何驗證與處理        | callback、signature、retry   |
| [WebSocket](websocket/)                       | 長連線雙向即時通訊如何運作            | chat、presence、push         |
| [Server-Sent Events (SSE)](sse/)              | HTTP 單向事件串流如何推送更新         | notification、progress       |
| [Stream Pipeline](stream-pipeline/)           | 連續資料流如何管理吞吐與 backpressure | stream、CDC、ETL             |
| [Throughput](throughput/)                     | 單位時間內可處理多少工作              | load test、queue、broker     |
| [Buffer](buffer/)                             | 暫存空間如何吸收短暫速度差            | queue、socket、cache         |
| [Queue](queue/)                               | 等待處理的工作如何形成容量邊界        | producer、consumer、backlog  |
| [Socket](socket/)                             | 網路連線如何成為資料讀寫與資源邊界    | network、connection、timeout |
| [Fallback](fallback/)                         | 主要路徑失敗時使用什麼替代結果        | degradation、circuit breaker |
| [Fail Fast](fail-fast/)                       | 已知無法完成時如何快速回應            | circuit breaker、validation  |
| [Retry Budget](retry-budget/)                 | 重試量如何受整體容量限制              | retry、SLO、token bucket     |
| [Cache Aside](cache-aside/)                   | application 如何讀快取與正式來源      | Redis、read path             |
| [Cache Hit / Miss](cache-hit-miss/)           | 讀取是否命中快取                      | cache、database pressure     |
| [Cache Hit Rate](cache-hit-rate/)             | 命中比例如何衡量快取效益              | dashboard、capacity          |
| [Cache Warmup](cache-warmup/)                 | 正式流量前如何預先載入快取            | deployment、event            |
| [Cache Prefetching](cache-prefetching/)       | 如何在資料被需要前預先載入            | user flow、hot data          |
| [Cold Start](cold-start/)                     | 新 instance 或空快取如何造成延遲      | autoscaling、readiness       |
| [Write-Through Cache](write-through-cache/)   | 寫入時如何同步更新快取                | write path、freshness        |
| [Write-Behind Cache](write-behind-cache/)     | 先寫緩衝層再非同步持久化的風險        | analytics、buffer            |
| [Stale Data](stale-data/)                     | 過期資料如何影響產品結果              | cache、replica               |
| [Soft TTL](soft-ttl/)                         | 進入刷新期後如何短暫使用舊資料        | stampede、refresh            |
| [Singleflight](singleflight/)                 | 相同工作如何合併成一次下游請求        | cache miss、hot key          |
| [TTL](ttl/)                                   | 資料何時自動過期                      | cache、session、presence     |
| [Eviction](eviction/)                         | 容量不足時哪些資料會被淘汰            | Redis、local cache、CDN      |
| [快取失效策略](cache-invalidation/)           | 快取資料何時更新、刪除或重建          | Redis、CDN、多層快取         |
| [Hot Key](hot-key/)                           | 少數 key 如何形成容量瓶頸             | Redis、partition、counter    |
| [Cache Stampede](cache-stampede/)             | 快取同時 miss 如何壓垮正式來源        | hot key、TTL、database       |
| [Rate Limit](rate-limit/)                     | 如何限制主體在一段時間內的資源使用量  | API、tenant、worker          |
| [Backpressure](backpressure/)                 | 下游變慢時如何讓上游放慢              | queue、worker、stream        |

## 入口與部署

| 卡片                              | 核心問題                              | 常見出現位置                        |
| --------------------------------- | ------------------------------------- | ----------------------------------- |
| [Service Endpoint](endpoint/)    | 服務入口如何被路由與存取               | API、service discovery、internal    |
| [Public API Endpoint](public-api-endpoint/) | 面向 client 的穩定對外入口     | product API、SDK、client            |
| [API Gateway](api-gateway/)      | 外部流量如何集中路由、驗證與轉發       | auth、rate limit、routing、request id |
| [Request Routing](request-routing/) | 入口流量如何分派到不同服務或版本      | host、path、tenant、version        |
| [Admin Endpoint](admin-endpoint/) | 高權限管理入口如何被隔離與稽核       | admin、backoffice、control plane    |
| [Diagnostic Endpoint](diagnostic-endpoint/) | health、readiness 與 debug 入口 | liveness、probe、metrics snapshot   |
| [Internal Endpoint](internal-endpoint/) | 服務內部通訊入口如何受控         | service-to-service、control plane   |
| [Container](container/)           | 服務如何被包裝成可交付單位            | image、runtime、CI、Kubernetes      |
| [Load Balancer](load-balancer/)   | 流量如何分散、排空與導向健康節點      | ingress、draining、rolling update   |
| [Draining](draining/)             | 服務如何先停新流量再完成既有工作      | rolling update、shutdown、cutover   |
| [Sticky Session](sticky-session/) | 同一 client 如何維持命中同一實例      | session affinity、load balancer     |
| [Idle Timeout](idle-timeout/)     | 連線或會話多久沒活動後要回收         | socket、load balancer、proxy        |
| [Health Check](health-check/)     | 平台如何快速判斷服務狀態             | load balancer、probe、diagnostic    |
| [Resource Limit](resource-limit/) | 服務可用的 CPU / memory 上限如何影響行為 | container、scheduler、runtime       |
| [Probe](probe/)                   | 平台如何判斷存活與接流量條件          | readiness、liveness、startup        |
| [Config Rollout](config-rollout/) | 設定如何安全下發到運作中的服務實例    | feature flag、secret、runtime config |
| [Runtime Config](runtime-config/) | 執行時設定如何被讀取、組合與覆寫       | env var、secret、feature flag       |

## 通訊協定

| 卡片                              | 核心問題                              | 常見出現位置                        |
| --------------------------------- | ------------------------------------- | ----------------------------------- |
| [Communication Protocol](protocol/) | 不同系統如何對齊資料交換與錯誤語意   | request/response、message、webhook  |
| [Request/Response Protocol](request-response-protocol/) | 同步呼叫如何對齊互動規則 | HTTP API、gRPC、RPC                 |
| [Message Protocol](message-protocol/) | queue / stream 訊息如何對齊格式與語意 | event、job、delivery                |
| [Webhook Protocol](webhook-protocol/) | 外部回呼如何對齊簽章與 payload        | callback、signature、retry          |

## 邊界與治理

| 卡片                           | 核心問題                      | 常見出現位置                      |
| ------------------------------ | ----------------------------- | --------------------------------- |
| [Boundary Contract](contract/) | 邊界兩端如何維持一致約定      | API contract、deployment contract、queue contract、load balancer contract |
| [API Contract](api-contract/)  | request / response 如何維持相容 | client、SDK、public API           |
| [Deployment Contract](deployment-contract/) | application 與 platform 如何對齊生命週期 | readiness、shutdown、rollout |
| [Queue Contract](queue-contract/) | producer / broker / consumer 如何對齊交付語意 | ack、retry、DLQ、redelivery |
| [Load Balancer Contract](load-balancer-contract/) | 服務與流量入口如何對齊健康與切流 | health check、draining、idle timeout |
| [Integration Adapter](adapter/) | 外部系統如何轉成內部需要的形狀 | repository、payment、notification |
| [Repository Adapter](repository-adapter/) | 持久化存取如何對齊應用模型 | SQL、transaction、row mapping |
| [Provider Adapter](provider-adapter/) | 第三方服務如何被包裝成穩定介面 | payment、email、SMS、storage |
| [Notification Adapter](notification-adapter/) | 通知通道如何轉成外部發送格式 | email、push、webhook |
| [Request Middleware](middleware/)      | 共通請求處理如何放在邊界上    | auth、logging、tracing、validation |
| [Authentication Middleware](authentication-middleware/) | 請求進入前如何驗證身份 | token、session、signature |
| [Authorization Middleware](authorization-middleware/) | 請求進入前如何判斷權限 | role、tenant、resource owner |
| [Observability Middleware](observability-middleware/) | 請求如何補上觀測欄位 | request id、trace context |
| [Security Middleware](security-middleware/) | 請求如何套用共通安全控制 | rate limit、redaction |
| [Validation Middleware](validation-middleware/) | 請求如何先做共通驗證 | schema、header、payload shape |

## 訊息與事件

| 卡片                                          | 核心問題                                    | 常見出現位置                       |
| --------------------------------------------- | ------------------------------------------- | ---------------------------------- |
| [Broker](broker/)                             | 訊息離開單一 process 後由誰保存、路由與交付 | queue、event、worker、stream       |
| [Topic](topic/)                               | 事件如何依主題分流給不同訂閱者              | broker、event、stream              |
| [Pub/Sub](pub-sub/)                           | 訊息如何即時分發給多個訂閱者                | realtime、notification、broadcast  |
| [Fan-out](fan-out/)                           | 單一事件如何同時送到多個下游                | topic、subscription、event flow    |
| [Durable Queue](durable-queue/)               | 工作如何在故障後仍可被處理                  | persistence、ack/nack、retry       |
| [Reliability Boundary](reliability-boundary/) | 系統在哪些邊界內承諾可恢復傳遞              | request、process、service boundary |
| [Offline Catch-up](offline-catchup/)          | 離線期間漏失事件如何補齊                    | websocket、sync、reconnect         |
| [Strong Reliability](strong-reliability/)     | 關鍵事件如何達到高可靠路徑                  | payment、inventory、audit          |
| [Routing Rule](routing-rule/)                 | 訊息如何依規則進入不同處理路徑              | broker、queue、priority            |
| [Producer](producer/)                         | 誰把工作、事件或資料送入處理路徑            | queue、broker、stream              |
| [Consumer](consumer/)                         | 誰取得等待處理的工作並產生結果              | queue、worker、side effect         |
| [Prefetch](prefetch/)                         | consumer 一次可持有多少未確認訊息           | broker、consumer tuning            |
| [In-Flight Message](in-flight-message/)       | 訊息已交給 consumer 但尚未完成              | consumer、shutdown                 |
| [Unacked Message](unacked-message/)           | broker 尚未收到 consumer 確認的訊息         | queue health、prefetch             |
| [Ack / Nack](ack-nack/)                       | consumer 如何回報處理結果                   | broker、retry、DLQ                 |
| [Redelivery](redelivery/)                     | broker 重新投遞訊息時如何保持安全           | at-least-once、idempotency         |
| [Requeue](requeue/)                           | 處理失敗訊息如何重新排回 queue              | retry、nack                        |
| [Redelivery Loop](redelivery-loop/)           | 同一訊息反覆投遞失敗如何消耗容量            | poison message、DLQ                |
| [Poison Message](poison-message/)             | 特定訊息內容如何穩定造成失敗                | DLQ、schema                        |
| [Queue Depth](queue-depth/)                   | queue 中等待處理的訊息數                    | backlog、capacity                  |
| [Publisher Confirm](publisher-confirm/)       | producer 如何確認 broker 已接收訊息         | publish、outbox                    |
| [Message Persistence](message-persistence/)   | 訊息是否落盤保存                            | durability、cost                   |
| [Delivery Mode](delivery-mode/)               | 投遞模式如何影響可靠性與延遲                | broker、event semantics            |
| [Delivery Semantics](delivery-semantics/)     | 事件投遞承諾如何決定補償策略                | retry、idempotency、replay         |
| [Consumer Capacity](consumer-capacity/)       | consumer 群組每秒能處理多少工作             | lag、scaling                       |
| [Competing Consumers](competing-consumers/)   | 多個 consumer 如何共同處理同一 queue        | worker、throughput                 |
| [Consumer Group](consumer-group/)             | 多個 consumer 如何共同分攤 stream           | Kafka、Redis Streams               |
| [Partition](partition/)                       | 事件流如何切成可並行處理片段                | ordering、hot key                  |
| [Offset](offset/)                             | consumer 在事件流中的讀取位置               | replay、checkpoint                 |
| [Retention](retention/)                       | 資料或事件保留多久                          | stream、log、audit                 |
| [Retry Policy](retry-policy/)                 | 失敗後何時再試、何時停止                    | timeout、broker、API               |
| [Consumer Lag](consumer-lag/)                 | consumer 處理速度落後多少                   | queue health、capacity、alert      |
| [Dead-Letter Queue](dead-letter-queue/)       | 多次處理失敗的訊息如何隔離與診斷            | retry、poison message、incident    |
| [Replay Runbook](replay-runbook/)             | 事件重放時如何控制範圍、順序與副作用        | migration、事故復原、補資料        |
| [重複投遞](duplicate-delivery/)               | 同一個工作被處理多次時如何保持結果穩定      | at-least-once、idempotency         |
| [Idempotency](idempotency/)                   | 同一操作多次執行時如何保持結果穩定          | retry、payment、worker             |
| [Outbox Pattern](outbox-pattern/)             | 資料變更與事件發布如何維持一致              | transaction、broker                |

## 遷移與資料同步

| 卡片                                        | 核心問題                         | 常見出現位置                  |
| ------------------------------------------- | -------------------------------- | ----------------------------- |
| [Online Migration](online-migration/)       | 服務持續接流量時如何遷移資料     | database、release             |
| [Cutover / Switchover](cutover-switchover/) | 正式流量如何切到新路徑           | migration、feature flag       |
| [Fallback Plan](fallback-plan/)             | 變更失敗時如何回到可接受狀態     | release、migration            |
| [Change Data Capture](change-data-capture/) | 資料變更如何被捕捉並傳送         | CDC、event stream             |
| [Replication Lag](replication-lag/)         | 副本落後正式來源多久             | replica、read model           |
| [Checkpoint](checkpoint/)                   | 長流程如何記錄可恢復進度         | backfill、consumer            |
| [Backfill](backfill/)                       | 既有資料如何補上新欄位或新狀態   | migration、repair             |
| [Dual Write](dual-write/)                   | 同一變更同時寫兩個系統的風險     | migration、split service      |
| [Shadow Read](shadow-read/)                 | 正式讀舊路徑時如何暗中比對新路徑 | cutover、validation           |
| [Correctness Check](correctness-check/)     | 新舊結果如何依規則比對           | migration、refactor           |
| [Data Completeness](data-completeness/)     | 資料是否完整到足以支持目標用途   | migration、audit              |
| [Data Reconciliation](data-reconciliation/) | 多來源差異如何比對與修復         | payment、eventual consistency |

## 可觀測性與可靠性

| 卡片                                              | 核心問題                              | 常見出現位置                        |
| ------------------------------------------------- | ------------------------------------- | ----------------------------------- |
| [Log](log/)                                       | 單一事件如何留下可搜尋的上下文        | incident、debug、audit              |
| [Log Schema](log-schema/)                         | log 欄位如何支援搜尋與關聯            | structured log、incident            |
| [Metrics](metrics/)                               | 指標如何描述趨勢、容量與健康          | Prometheus、dashboard               |
| [Histogram](histogram/)                           | 如何用分桶統計延遲與分布              | latency、SLO                        |
| [Bucket](bucket/)                                 | histogram 分桶如何影響解析度          | metrics、cost                       |
| [Percentile](percentile/)                         | p95 / p99 如何描述長尾延遲            | latency、UX                         |
| [Metric Cardinality](metric-cardinality/)         | label 組合數如何影響成本              | metrics、storage、query             |
| [Trace](trace/)                                   | 跨服務流程如何重建路徑與耗時          | tracing、dependency                 |
| [Trace Context](trace-context/)                   | 跨服務 request 如何串起路徑           | tracing、OpenTelemetry              |
| [Trace ID](trace-id/)                             | 同一條 trace 的識別碼                 | tracing、log correlation            |
| [Span](span/)                                     | trace 中一段工作如何記錄耗時          | tracing、dependency                 |
| [Correlation ID](correlation-id/)                 | 跨事件與跨服務如何關聯業務流程        | order、payment、queue               |
| [Request ID](request-id/)                         | 單次 request 如何被追蹤               | API、support                        |
| [Dashboard](dashboard/)                           | 多個觀測訊號如何組成服務狀態畫面      | incident、capacity、SLO             |
| [SLI / SLO](sli-slo/)                             | 服務品質如何連到產品承諾              | alert、incident、error budget       |
| [Error Budget](error-budget/)                     | SLO 允許的失敗額度如何決策            | release、reliability                |
| [Burn Rate](burn-rate/)                           | error budget 消耗速度如何告警         | SLO alert                           |
| [Sampling](sampling/)                             | 如何抽樣觀測資料以控制成本            | trace、log                          |
| [Alert](alert/)                                   | 服務症狀如何轉成可行動通知            | on-call、SLO、incident              |
| [Runbook](runbook/)                               | 事故判斷與操作步驟如何標準化          | on-call、incident、replay           |
| [Alert Runbook](alert-runbook/)                   | 告警如何連到可執行排障流程            | on-call、dashboard                  |
| [Symptom-Based Alert](symptom-based-alert/)       | 告警如何優先偵測產品症狀              | SLO、on-call                        |
| [Runbook Link](runbook-link/)                     | 告警如何直接連到處理流程              | alert、dashboard                    |
| [Alert Fatigue](alert-fatigue/)                   | 低品質告警如何降低反應品質            | on-call、alert policy               |
| [降級](degradation/)                              | 服務部分能力失效時如何保留核心功能    | failover、fallback、capacity        |
| [Circuit Breaker](circuit-breaker/)               | 下游持續失敗時如何暫停呼叫            | timeout、fallback、degradation      |
| [Failover](failover/)                             | 主要路徑失效時如何切到備援            | HA、region、provider                |
| [Autoscaling](autoscaling/)                       | 容量如何依指標自動擴縮                | HPA、capacity、traffic burst        |
| [Rolling Update](rolling-update/)                 | 版本如何逐批替換並維持可用            | deployment、release                 |
| [Service Registry](service-registry/)             | 服務實例如何被註冊、維護與摘除        | heartbeat、TTL、metadata            |
| [Service Discovery](service-discovery/)           | 服務實例如何被查找與路由              | registry、DNS、load balancing       |
| [停機](downtime/)                                 | 服務中斷時要先保護哪些產品結果        | incident、SLO、deployment           |
| [Readiness](readiness/)                           | instance 何時可以安全接收流量         | Kubernetes、load balancer、rollout  |
| [Liveness](health-check-liveness/)               | 平台如何判斷 process 是否仍然存活     | Kubernetes、systemd                 |
| [Graceful Shutdown](graceful-shutdown/)           | instance 停止前如何排空流量與保存狀態 | deployment、worker、long connection |

## 事故處理與復盤

| 卡片                                                | 核心問題                       | 常見出現位置                  |
| --------------------------------------------------- | ------------------------------ | ----------------------------- |
| [On-Call](on-call/)                                 | 值班制度如何承接告警與事故流程 | paging、handover、incident    |
| [Handover Protocol](handover-protocol/)             | 值班或事故責任如何安全交接     | on-call、escalation、incident |
| [Playbook](playbook/)                               | 場景化處置如何快速啟動與執行   | incident workflow、recovery   |
| [CI Pipeline](ci-pipeline/)                         | 合併前如何自動驗證品質與相容性 | tests、checks、merge gate     |
| [Load Test](load-test/)                             | 預期流量下如何驗證容量與延遲   | performance、SLO、capacity    |
| [Chaos Test](chaos-test/)                           | 受控故障注入如何驗證韌性       | resilience、failover、runbook |
| [Game Day](game-day/)                               | 事故演練如何驗證流程與協作     | drill、readiness、training    |
| [Incident Severity](incident-severity/)             | 事故如何依產品影響分級         | on-call、incident、SLO        |
| [Incident Command System](incident-command-system/) | 事故期間如何分配指揮與執行角色 | commander、scribe、owner      |
| [Incident Communication Channel](incident-communication-channel/) | 事故期間如何同步對內對外資訊 | internal chat、status update、bridge |
| [Escalation Policy](escalation-policy/)             | 事故無回應或無進展時如何升級   | on-call、paging、handover     |
| [Incident Timeline](incident-timeline/)             | 事故事件如何形成一致時間軸     | incident log、communication   |
| [Blast Radius](blast-radius/)                       | 故障影響面如何估算與隔離       | dependency、shared resource   |
| [Rollback Strategy](rollback-strategy/)             | 事故期間何時回滾與回切         | deployment、release gate      |
| [Post-Incident Review](post-incident-review/)       | 事故後如何形成改進閉環         | retrospective、action items   |
| [RCA](rca/)                                         | 根因分析如何從證據推導改進     | timeline、control gap         |
| [RTO](rto/)                                         | 服務回復時間目標如何定義       | SLA/SLO、DR                   |
| [RPO](rpo/)                                         | 可接受資料損失窗口如何定義     | backup、replication           |
| [MTTR](mttr/)                                       | 平均修復時間如何反映處置能力   | incident metrics、review      |

## 資安與資料保護

| 卡片                                                                    | 核心問題                             | 常見出現位置                   |
| ----------------------------------------------------------------------- | ------------------------------------ | ------------------------------ |
| [Authorization](authorization/)                                         | 誰能對哪些資源執行哪些操作           | RBAC、ABAC、tenant             |
| [Authentication](authentication/)                                       | 系統如何確認呼叫者身份               | login、API key、mTLS           |
| [Credential](credential/)                                               | 身分與系統存取用秘密如何保存與輪替   | API key、password、private key  |
| [IAM](iam/)                                                             | 身分與權限如何集中治理               | SSO、roles、policy             |
| [BOLA / IDOR](bola-idor/)                                               | 使用者如何被限制只能存取授權物件     | API、resource ID               |
| [BOPLA](bopla/)                                                         | 欄位層級如何授權讀寫                 | DTO、field policy              |
| [Mass Assignment](mass-assignment/)                                     | 自動綁定欄位如何造成未授權修改       | API、ORM                       |
| [Excessive Data Exposure](excessive-data-exposure/)                     | API 回傳過多資料如何增加外洩風險     | response、DTO                  |
| [Unrestricted Resource Consumption](unrestricted-resource-consumption/) | API 如何限制昂貴資源使用             | upload、export、query          |
| [Function-Level Authorization](function-level-authorization/)           | 功能操作本身如何授權                 | refund、export、admin          |
| [Tenant Boundary](tenant-boundary/)                                     | 多租戶資料與資源如何隔離             | SaaS、RBAC                     |
| [Least Privilege](least-privilege/)                                     | 身份如何只取得必要權限               | IAM、database user             |
| [Security Misconfiguration](security-misconfiguration/)                 | 設定錯誤如何暴露內部能力             | CORS、debug、cloud             |
| [Attack Surface](attack-surface/)                                       | 系統哪些對外暴露面最先被探測       | public API、admin route、webhook |
| [Trust Boundary](trust-boundary/)                                       | 哪些位置開始不能沿用原本信任假設   | auth boundary、tenant、network  |
| [Abuse Case](abuse-case/)                                               | 合法功能如何被惡意轉用             | export、invite、reset           |
| [WAF](waf/)                                                             | 入口層如何過濾常見攻擊與濫用         | edge、bot、attack             |
| [Feature Flag](feature-flag/)                                           | 功能開關如何分離部署與啟用           | rollout、experiment、rollback  |
| [Input Validation](input-validation/)                                   | 入口資料如何檢查格式與語意           | API、webhook                   |
| [SSRF](ssrf/)                                                           | 伺服器端請求如何被濫用               | URL fetch、webhook             |
| [PII](pii/)                                                             | 可識別個人的資料如何保護             | masking、retention             |
| [Data Classification](data-classification/)                             | 資料分級如何決定保護規則             | security、compliance           |
| [Data Masking](data-masking/)                                           | 敏感資料如何降低暴露                 | export、log、support tool      |
| [Secret Management](secret-management/)                                 | token、key、password 如何保存與輪替  | credential、deployment         |
| [TLS / mTLS](tls-mtls/)                                                 | 傳輸加密與雙向身份驗證如何保護資料流 | service-to-service、API        |
| [Website Certificate Lifecycle](website-certificate-lifecycle/)         | 網站憑證從簽發到續期與撤銷如何治理   | HTTPS、edge、ingress           |
| [ACME Automation](acme-automation/)                                     | 網站憑證如何自動簽發與續期           | Let's Encrypt、DNS-01、HTTP-01 |
| [Certificate Chain and Trust Root](certificate-chain-trust/)            | 憑證鏈與信任根如何影響握手           | intermediate CA、trust store   |
| [Certificate Rotation and Renewal](certificate-rotation-renewal/)       | 憑證與私鑰如何不中斷更新             | expiry、zero-downtime          |
| [Certificate Revocation](certificate-revocation/)                       | 憑證失效時如何撤銷與替換             | key compromise、incident       |
| [Audit Log](audit-log/)                                                 | 高風險操作如何留下責任證據           | admin、export、permission      |

## 使用方式

知識卡片是章節引用單位。選型文章遇到術語時，應連到對應卡片；服務實體章節需要更深入時，再從卡片延伸到具體工具操作。

卡片先回答概念本質，再放例子與提醒。這個順序讓讀者先知道該概念在系統裡承擔什麼責任，再理解 RabbitMQ、Redis、Kubernetes 或 observability 平台中的具體名稱。
