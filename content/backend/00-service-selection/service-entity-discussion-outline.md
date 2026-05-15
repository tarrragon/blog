---
title: "0.17 後端真實服務討論大綱"
date: 2026-05-15
description: "規劃各 backend 分類從共同觀念與服務路徑示範，推進到真實服務介紹、取捨與案例回寫的寫作順序"
weight: 17
tags: ["backend", "service-entity", "outline", "vendor"]
---

後端真實服務討論的核心責任是把分類觀念落到具體服務能力。PostgreSQL、Redis、Kafka、Kubernetes、k6 或 PagerDuty 這些名稱本身是服務能力入口；它們各自承擔某種資料、流量、交付、驗證或協作責任，文章要先說清楚這個責任，再討論適用場景、替代方案、操作成本與案例回寫。

## 階段定位

真實服務層是後端教材的第三層。第一層是分類共同認知，回答資料庫、快取、queue、觀測、部署、可靠性、資安與事故流程分別解什麼問題；第二層是服務路徑示範，用單一業務流程串起 evidence、gate、decision log 與 write-back；第三層才討論具體服務如何承擔這些責任。

這個階段的主要風險是把服務頁寫成產品介紹。服務頁要把工具能力翻成 backend 判準：它承擔哪種狀態、怎麼觀測、什麼負載形狀會壓垮它、什麼團隊能力才維護得起、什麼條件下應該換到同類或相鄰服務。

## 撰寫判準

每篇服務實體文章都要回答同一組決策問題。固定問題提供交接語言，正文段落仍要保留該服務自己的情境語言。

| 判準       | 文章要回答的問題                                | 失焦訊號                       |
| ---------- | ----------------------------------------------- | ------------------------------ |
| 服務責任   | 這個服務承擔哪一類 backend 能力                 | 只列功能，不說解什麼服務問題   |
| 適用壓力   | 哪種流量、資料、組織或合規壓力會讓它值得引入    | 只寫「適合大規模」這類空泛描述 |
| 替代邊界   | 什麼情境下同類服務或相鄰分類更划算              | 把同一類工具寫成單一路線       |
| 操作成本   | 引入後誰負責升級、備份、容量、監控、事故與稽核  | 只比較雲端價格或效能           |
| 案例回寫   | 哪些公開案例能回寫到分類主章或服務路徑示範      | 案例停在「某公司使用 X」       |
| 下一步路由 | 讀者下一步該回到哪個主章、case、artifact 或卡片 | 文章讀完沒有決策出口           |

服務責任段要把產品名稱放回分類語言。PostgreSQL 承擔 SQL transaction、schema evolution、query boundary 與 migration safety；Kafka 承擔 event log、consumer group、replay window 與 topic governance。

適用壓力段要用真實服務訊號描述引入理由。資料量、QPS、hot key、consumer lag、connection limit、multi-region latency、compliance evidence、on-call 負擔與 vendor support 都是可判讀訊號；單純寫「效能更好」或「比較穩定」會讓讀者失去選型依據。

替代邊界段要保留機會成本。Redis 在簡單快取路徑很合理，但 durable workflow 要轉向 queue；DynamoDB 在高峰 KV workload 很合理，但複雜 ad-hoc query 要回到 SQL 或 search；Kubernetes 在多服務平台很合理，但單機服務可能由 systemd 承擔更低操作成本。

操作成本段要把服務帶來的長期責任寫出來。Managed 服務降低 patch、failover 與容量維護成本，但增加雲端約束、費用模型與 vendor 依賴；自管服務保留控制權，但要求團隊承擔升級、備援、演練與事故處理。

案例回寫段要把公開案例變成判準來源。案例的核心責任是提供流量形狀、失敗代價、組織能力與回退路徑，讓主章可以回寫更準確的服務判斷。

## LLM 教學設計移植

LLM 目錄提供的可重用設計是「先建立心智模型，再進入工具，最後才處理延伸與排錯」。Backend 服務頁要採同一種教學骨架：先說服務在分類模型裡的位置，再給讀者最短判讀路徑，接著展開日常操作、進階主題、替代路由與不收錄主題。

這個設計避免服務頁變成產品百科。Ollama、LM Studio、llama.cpp 的文章都先說它在「介面 / 伺服器 / 模型」三層架構中的位置；Backend 服務頁也要先說 PostgreSQL、Redis、Kafka、Kubernetes、Prometheus、PagerDuty 等服務在「資料 / 副本 / 交接 / 流量 / 訊號 / 驗證 / 協作」哪一層承擔責任。

## 服務頁標準大綱

每篇真實服務頁先依下列章節建稿。章節名稱可以依分類調整，但語意責任要完整保留。

| 章節                 | 作用                                           | Backend 服務頁要回答的問題                                         |
| -------------------- | ---------------------------------------------- | ------------------------------------------------------------------ |
| 服務定位             | 對應 LLM 文章的三層架構定位                    | 這個服務屬於資料、快取、broker、平台、觀測、驗證或協作哪一層       |
| 本章目標             | 對應 LLM 文章的「讀完後你應該能」              | 讀者讀完後能做哪幾個判斷、辨識哪幾個風險                           |
| 最短判讀路徑         | 對應 LLM 文章的「5 分鐘 / 1 小時最短路徑」     | 只用一個真實服務壓力，如何快速判斷是否該考慮這個服務               |
| 日常操作與決策形狀   | 對應 LLM 文章的日常使用段                      | 服務在日常運作中有哪些固定決策：容量、備份、升級、權限、觀測       |
| 核心取捨表           | 對應 LLM 文章的工具對照表                      | 它跟同類或相鄰服務的差異，哪些情境下比較划算                       |
| 進階主題             | 對應 LLM 文章的按需閱讀段                      | cluster、multi-region、HA、managed mode、SLO、cost 等何時才需要    |
| 排錯與失敗快速判讀   | 對應 LLM 文章的排錯段                          | 出現 lag、hot key、failover、cardinality、alert fatigue 時先看哪裡 |
| 何時改走其他服務     | 對應 LLM 文章的「何時改回 Ollama / llama.cpp」 | 什麼條件下該改用 SQL、queue、managed platform、SaaS、OSS 或自建    |
| 不在本頁內的主題     | 對應 LLM 文章的 scope boundary                 | 哪些議題交給主章、案例、語言教材、資安或更專門的模組               |
| 案例回寫與下一步路由 | 對應 LLM 文章的下一章 / 模組路由               | 讀完後回到哪個主章、case、artifact、knowledge card                 |

「最短判讀路徑」定位為決策教學。Backend 服務頁的最短路徑是決策路徑，例如「Redis 是否只是可重建副本」「Kafka 是否需要 replay window」「Kubernetes 是否真的需要多服務調度」「PagerDuty 是否已經有 service ownership 與 escalation policy」。這段要讓讀者在短時間內排除明顯不適合的選項。

「排錯與失敗快速判讀」定位為第一輪分流。它只列第一輪定位問題，讓讀者知道應該回到哪個主章或案例：cache 先看 hit/miss 與 origin QPS；queue 先看 lag、DLQ、redelivery；deployment 先看 readiness、drain、per-version SLI；observability 先看資料品質與 cardinality；incident 先看 alert route、incident timeline 與 stakeholder update。

## WRAP 分類差異判斷

分類差異判斷的錨點是「服務頁教讀者做決策，而非填同一份模板」。每個分類都有自己的主要責任：資料庫處理正式狀態，快取處理可重建副本，佇列處理跨程序交接，部署處理生命週期與流量，觀測處理訊號，可靠性處理驗證，資安處理控制面，事故處理協作，效能容量處理壓力與成本。因此服務頁可以共用教學骨架，但正文結構要跟分類責任對齊。

Step 0 的資料充足度判斷是：現有主章、case、vendor index 已足以規劃大綱，但還不足以直接寫每個服務正文。下一步應先補「分類特化補充軸」，讓每篇正文開工前知道該連到哪些壓力、安全、觀測、可靠性與事故問題。

Widen Options 後的選項有三種。第一種是同一模板寫全部服務，交接成本低，但會抹平 Redis、Kafka、Kubernetes、PagerDuty 這些服務的責任差異。第二種是每個分類完全自由寫，表面彈性高，但容易漏掉資安、壓力、觀測、可靠性與事故交接。第三種是「分類主結構 + 共同護欄」，每類保留自己的教學順序，同時強制檢查 04 / 06 / 07 / 08 / 09 的交叉議題；這是後續採用的策略。

Reality Test 的反向驗證是：如果服務頁沒有明確連到 07 security、09 pressure / capacity、04 observability、06 reliability 與 08 incident response，讀者會把服務理解成單點工具；如果服務頁只列這些共同欄位，讀者會失去分類語言。因此共同護欄只作為每篇的檢查軸，分類自己的正文順序仍是主體。

Prepare to be Wrong 的回退條件是：若後續撰寫某分類時出現「每篇段落順序完全相同」或「資安 / 壓力 / 事故只出現在最後一段」兩種訊號，要先回到本節調整該分類大綱，再寫下一篇服務頁。

## 共同護欄與路由

共同護欄的核心責任是防止服務頁只停在功能介紹。每篇服務頁都要有分類自己的主結構，並至少處理下列五個交叉軸。

| 交叉軸     | 必答問題                                             | 主要路由                                                   |
| ---------- | ---------------------------------------------------- | ---------------------------------------------------------- |
| 壓力問題   | 什麼流量、資料量、併發、延遲、成本或容量形狀會壓垮它 | [09 效能與容量](/backend/09-performance-capacity/)         |
| 資安問題   | 它新增哪個身份、秘密、入口、資料、供應鏈或稽核控制面 | [07 資安與資料保護](/backend/07-security-data-protection/) |
| 可觀測性   | 讀者要看哪些訊號才能知道它健康、退化或失真           | [04 可觀測性](/backend/04-observability/)                  |
| 可靠性驗證 | 它的變更、故障模式或降級路徑要如何被驗證             | [06 可靠性驗證](/backend/06-reliability/)                  |
| 事故交接   | 它失效時誰接手、如何分級、如何記錄決策與回寫         | [08 事故處理](/backend/08-incident-response/)              |

這五軸在正文中要貼近分類語言。資料庫的壓力問題是 connection、lock、replication lag、hot partition；快取的壓力問題是 hot key、miss storm、origin QPS；佇列的壓力問題是 consumer lag、DLQ、redelivery；部署的壓力問題是 rollout batch、drain、target health；事故工具的壓力問題是 alert volume、ack time、stakeholder update freshness。

## 分類特化補充軸

每個分類要補的內容由「主責任」決定。共同護欄只提醒要連到哪些模組，真正的段落順序由下表的分類主問題決定。

| 分類             | 主結構要優先回答的問題                                      | 壓力軸                                                            | 資安軸                                                    | 04 / 06 / 08 交接軸                                                                             |
| ---------------- | ----------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 01 Database      | 正式狀態、transaction、query、schema、migration             | connection、lock、slow query、replica lag、hot partition          | 權限、資料遮罩、備份、資料駐留、稽核                      | 04 看 query / replication 訊號；06 驗證 migration / failover；08 記錄資料事故決策               |
| 02 Cache         | 可重建副本、新鮮度、回源保護、記憶體成本                    | hot key、miss storm、eviction、origin QPS、stale read             | cache poisoning、敏感資料快取、ACL、管理面                | 04 看 hit/miss / origin QPS；06 驗證 warmup / rollback；08 處理 stampede / stale incident       |
| 03 Queue         | delivery、processing、recovery、replay、DLQ                 | publish rate、consumer lag、redelivery、DLQ depth、poison message | payload 敏感資料、topic ACL、producer credential          | 04 看 lag / retry / DLQ；06 驗證 idempotency / replay；08 記錄 pause / drain / replay 決策      |
| 04 Observability | signal contract、data quality、cardinality、retention       | ingest volume、cardinality、query cost、sampling gap              | PII in logs、trace leakage、audit evidence                | 06 依賴 evidence gate；08 依賴 timeline / query link；09 依賴 saturation / cost signal          |
| 05 Deployment    | lifecycle、traffic、config、resource、rollback              | rollout batch、readiness、drain、target health、config drift      | secret delivery、TLS、management plane、image trust       | 04 看 per-version SLI；06 驗證 release gate / rollback；08 記錄 freeze / cutover / rollback     |
| 06 Reliability   | gate、experiment、fault injection、SLO governance           | runner bottleneck、false gate、blast radius、experiment load      | secret in CI、test credential、experiment permission      | 04 提供 evidence；08 接收 failed gate / unsafe experiment；09 提供 workload / capacity baseline |
| 07 Security      | identity、secret、key、entrypoint、artifact、detection      | auth spike、WAF false positive、rotation load、scan noise         | 本分類主軸：控制面、信任邊界、例外治理                    | 04 提供 audit / detection signal；06 驗證 control / release gate；08 處理 security incident     |
| 08 Incident      | alert routing、command、status、postmortem、learning        | alert storm、missed ack、timeline drift、status update freshness  | incident channel 權限、customer data、postmortem sharing  | 04 提供事件證據；06 回收 action item 到 gate；09 回收 capacity incident lessons                 |
| 09 Performance   | workload、saturation、capacity、cost、production validation | throughput plateau、latency knee、runner limit、cost curve        | replay data masking、profiler sensitive data、FinOps 權限 | 04 提供 metric / profile；06 接 regression gate；08 接 capacity incident / cost incident        |

分類特化補充軸的使用方式是先選分類主問題，再把五個交叉軸嵌入最自然的位置。資料庫服務頁的「資安」通常進入權限、備份、稽核段；快取服務頁的「資安」通常進入敏感資料與管理面段；佇列服務頁的「資安」通常進入 topic ACL 與 payload 段；事故工具頁的「可觀測性」通常進入 timeline evidence 與 query link 段。

## 主流覆蓋檢查

主流覆蓋檢查的核心責任是防止 vendor index 只列出已寫過的工具。T1 代表近期要寫成服務頁的主線選項；T2 代表主流但要等分類語言更穩後再寫；T3 代表相鄰分類或特殊場景，先保留路由，等案例需要時再升級。

| 分類             | T1 已有基線                                                                                                                                       | T2 補強方向                                                                                                                           | T3 / 相鄰路由                                             |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| 01 Database      | PostgreSQL、MySQL、SQLite、MongoDB、DynamoDB、Aurora、Spanner、Cosmos DB、CockroachDB                                                             | Oracle、SQL Server、MariaDB、Cassandra / ScyllaDB、OpenSearch / Elasticsearch、ClickHouse                                             | Snowflake / BigQuery 走 analytics；Redis 走 02 Cache      |
| 02 Cache         | Redis、Valkey、Memcached、DragonflyDB、ElastiCache                                                                                                | KeyDB、Garnet、Momento、Azure Cache、GCP Memorystore、Hazelcast、Aerospike                                                            | CDN / HTTP cache 連到 05 / edge；local cache 連到語言教材 |
| 03 Queue         | RabbitMQ、Kafka、NATS、Redis Streams、SQS、Pub/Sub                                                                                                | Pulsar、Redpanda、Kinesis、Azure Service Bus、EventBridge、SNS、Temporal                                                              | Celery / Sidekiq 走語言框架；MQTT broker 走 IoT 場景      |
| 04 Observability | OpenTelemetry、Prometheus、Grafana Stack、Datadog、Elastic、Honeycomb、CloudWatch、GCP Operations、Sentry                                         | Jaeger、OpenSearch、Fluent Bit / Fluentd、Vector、VictoriaMetrics、Thanos / Cortex、Splunk、New Relic、Dynatrace                      | Security SIEM 走 07；capacity profiling 走 09             |
| 05 Deployment    | Kubernetes、Docker、systemd、nginx、Envoy、AWS ELB、Terraform、Traefik、Consul                                                                    | Argo CD、Flux、Helm、Kustomize、ingress-nginx、Envoy Gateway、Istio、Linkerd、HAProxy、ECS / Fargate、Cloud Run                       | CI/CD gate 走 06；secret / policy control 走 07           |
| 06 Reliability   | GitHub Actions、CircleCI、k6、Gatling、JMeter、Locust、Chaos Mesh、LitmusChaos、Gremlin、Toxiproxy、Nobl9、Sloth                                  | GitLab CI、Jenkins、Buildkite、Tekton、Harness、Artillery、BlazeMeter、AWS FIS、Azure Chaos Studio、Pyrra、OpenSLO                    | capacity tool 走 09；incident tooling 走 08               |
| 07 Security      | Identity、IAM、Secrets、KMS、WAF、PKI、Supply Chain、SIEM、DLP 服務群                                                                             | Teleport、Boundary、Tailscale SSH、OPA、Kyverno、Falco、Wiz、Prisma Cloud、GitGuardian、Cloudflare Access                             | alert routing 走 08；evidence dashboard 走 04             |
| 08 Incident      | PagerDuty、Opsgenie、Grafana OnCall、incident.io、FireHydrant、Rootly、Statuspage、Instatus、Jeli                                                 | ServiceNow、Jira Service Management、Squadcast、xMatters、Splunk On-Call、Better Stack、Status.io、Cachet                             | observability source 走 04；release action 走 06          |
| 09 Performance   | k6、JMeter、Gatling、Locust、Vegeta、GoReplay、Traffic Mirroring、Datadog Profiler、Pyroscope、Parca、Akamas、Vantage、CloudHealth、Cost Explorer | Artillery、wrk、hey、Grafana k6 Cloud、AWS Distributed Load Testing、LoadRunner / BlazeMeter、Kubecost / OpenCost、CloudZero、CAST AI | release gate 走 06；FinOps ownership 走 04 / 09           |

主流覆蓋的判斷依據要保留時間戳。資料庫可以參考 DB-Engines 這類長期 popularity ranking；cloud-native 服務可參考 CNCF project / landscape 與近期技術雷達；incident tooling 要注意產品生命週期與收購 / sunset；雲端服務要以官方文件與主流 provider 分類為準。每次要把 T2 升級成 T1 前，先重新確認服務仍活躍、官方文件穩定、案例可回寫。

## 第一批：資料庫服務

資料庫服務討論的核心順序是先建立 SQL baseline，再處理 managed、KV/document 與全球分散式資料庫。這樣讀者會先知道 transaction、schema、query boundary 與 migration safety 如何成立，再看各服務把哪一部分能力交給平台或分散式協議。

第一批優先補強既有 vendor 頁的服務判準與案例回寫密度：

| 服務群                   | 主要頁面                                                                                                                                                          | 討論重點                                   |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| SQL baseline             | [PostgreSQL](/backend/01-database/vendors/postgresql/) / [MySQL](/backend/01-database/vendors/mysql/)                                                             | transaction、schema evolution、connection  |
| Managed SQL              | [Aurora](/backend/01-database/vendors/aurora/)                                                                                                                    | storage / compute 分離、failover、AWS 約束 |
| Embedded / local         | [SQLite](/backend/01-database/vendors/sqlite/)                                                                                                                    | 單機正式狀態、測試資料、低操作成本         |
| Document / KV            | [MongoDB](/backend/01-database/vendors/mongodb/) / [DynamoDB](/backend/01-database/vendors/dynamodb/)                                                             | access pattern、partition、資料形狀        |
| Global SQL / multi-model | [Spanner](/backend/01-database/vendors/spanner/) / [Cosmos DB](/backend/01-database/vendors/cosmosdb/) / [CockroachDB](/backend/01-database/vendors/cockroachdb/) | consistency、region、vendor lock-in        |

SQL baseline 段要把 PostgreSQL 與 MySQL 寫成比較基準。後續所有 managed SQL、distributed SQL 與 KV/document 討論，都應回到「這個 workload 為什麼離開或保留 SQL baseline」。

Managed SQL 段要保留平台責任轉移。Aurora 這類服務要同時看吞吐、storage layer、replica、failover、backup、engine compatibility 與雲端營運模型如何改變團隊責任。

Document / KV 段要先問資料形狀。DynamoDB、MongoDB 與 Cosmos DB 的差異，應從 access pattern、partition key、consistency、query model 與容量計費談起，再把 NoSQL 標籤放回分類整理。

Global SQL / multi-model 段要把 consistency 寫成產品成本。Spanner、CockroachDB 與 Cosmos DB 解決的是跨 region 的一致性與可用性取捨；文章要說明 latency、quorum、資料駐留、費用與 vendor 約束如何一起改變架構。

## 第二批：快取與事件服務

快取與事件服務討論的核心順序是先區分「副本保護」與「可靠工作交接」。Redis、Valkey、Memcached、Kafka、RabbitMQ、SQS、Pub/Sub、NATS 與 Redis Streams 都可能出現在高流量服務中，但它們承擔的資料生命週期不同。

快取頁要先回答副本語意。Redis / Valkey 適合 data structure rich cache、rate limit、leaderboard 與部分 coordination；Memcached 適合低語意、可重建、短生命週期快取；managed cache 則把 patch、failover 與 capacity 交給平台。

Queue 頁要先回答處理語意。Kafka 偏 event log、replay、partition 與 consumer group；RabbitMQ 偏 broker routing 與工作分派；SQS / Pub/Sub 偏 managed delivery；NATS 偏低延遲通訊與簡化操作；Redis Streams 適合既有 Redis 場景中的輕量 stream，但要清楚界定 durability 與治理邊界。

## 第三批：部署平台與操作服務

部署平台服務討論的核心順序是先從 service lifecycle 開始，再分到 workload、traffic、discovery、infra state 與 secret / config。Kubernetes、systemd、Docker、nginx、ELB、Envoy、Terraform 與 Consul 都能交付服務，但它們分屬不同能力層。

Workload 層要比較 Kubernetes、systemd 與 Docker。Kubernetes 適合多服務、多租戶、可觀測與 rollout 要求高的平台；systemd 適合單機或小型服務；Docker 提供 packaging 與 runtime 基礎，完整部署平台還需要 rollout、traffic、config 與觀測責任。

Traffic 層要比較 nginx、ELB、Envoy 與 Traefik。文章要從 health check、draining、idle timeout、TLS、routing rule 與 per-version traffic 訊號談起，讓讀者看懂 load balancer contract 如何影響 rollout 與事故回退。

Infra state 與 discovery 層要比較 Terraform 與 Consul。Terraform 承擔 infrastructure desired state，Consul 承擔 service registry / discovery 與部分 mesh 能力；兩者的失敗模式分別接到 change review、state drift、registry freshness 與 control plane 可用性。

## 第四批：效能與操作控制工具

效能工具服務討論的核心順序是先補 `09 vendors/`。09 主章與案例庫已經能支撐 workload model、saturation discovery、capacity planning、production validation 與 SLO coupling，下一步要把工具選型補成可引用入口。

壓測工具頁要用 workload model 當選型前提。k6、JMeter、Gatling、Locust 與 Vegeta 的差異，應從 protocol、scenario scripting、distributed load、CI integration、reporting 與團隊語言能力談起。

Production replay 與 profiling 工具頁要用風險邊界當選型前提。GoReplay、traffic mirroring、service mesh shadow、Datadog Continuous Profiler、Pyroscope 與 Parca 都能提供 production 近似訊號，但它們對資料遮罩、成本、採樣、效能開銷與事故觸發條件的要求不同。

## 第五批：資安控制服務

資安控制服務討論的核心順序是先從身份與憑證開始，再分到入口防護、供應鏈、偵測與資料保護。Okta、Auth0、Keycloak、AWS IAM、Vault、KMS、WAF、cert-manager、Snyk、Trivy、SIEM 與 DLP 服務都能改善安全控制，但它們分屬不同控制面。

Identity / IAM 頁要先回答「誰能做什麼」。人類身份、機器身份、role、policy、session、federation 與 least privilege 是選型基線；工具比較要回到身份擴散、例外權限與可稽核證據。

Secrets / KMS / PKI 頁要先回答「秘密與金鑰如何生命週期化」。Vault、Secrets Manager、KMS、cert-manager 與 SPIRE 的差異，應從 storage、lease、rotation、audit、delivery 與 workload identity 談起。

Edge / supply chain / detection 頁要先回答「控制在哪一個交接點生效」。WAF 保護入口，SCA / SBOM 保護 artifact，SIEM / detection 保護發現與交接，DLP 保護資料流；文章要說明它們如何接到 release gate、observability 與 incident response。

## 推進順序

下一輪寫作以最小可回寫批次推進。每批完成前先更新對應 vendor `_index.md` 的服務頁大綱與撰寫批次，再進入個別服務正文，避免服務頁散落成獨立產品百科。

1. 校正既有狀態：更新 `0.15`、`0.16`、`09 _index` 與已成形 vendor 清單的描述。
2. 補強 `01 Database vendors` 的頁面導覽與跨服務對照，讓 SQL baseline、managed SQL、KV/document 與 distributed SQL 的讀法明確。
3. 建立 `09 vendors/` 入口、第一批壓測工具頁、production traffic replay 頁、continuous profiling 頁與 capacity / cost analysis 頁，補上目前最明顯的結構缺口。（已完成 k6 / JMeter / Gatling / Locust / Vegeta / GoReplay / Service Mesh Mirroring / AWS VPC Traffic Mirroring / Datadog Continuous Profiler / Pyroscope / Parca / Akamas / Vantage / CloudHealth / AWS Cost Explorer）
4. 更新 `02 Cache`、`03 Queue`、`04 Observability`、`05 Deployment`、`06 Reliability` 與 `08 Incident Response` 的 vendor index，把不同服務的頁面大綱、欄位與批次先定義清楚。（已完成索引層大綱）
5. 補強 `02 Cache` 與 `03 Queue` 的服務頁，維持「副本語意」與「處理語意」的分流。
6. 新增 `07 Security` 的 vendor index 大綱，把 identity、IAM、secrets、KMS、WAF、PKI、supply chain、SIEM 與 DLP 服務群先列出。（已完成索引層大綱）
7. 補強 `05 Deployment`、`04 Observability`、`06 Reliability`、`07 Security` 與 `08 Incident Response` 的服務頁，把 workload、telemetry、verification、security control 與 incident workflow 分層。

## 完成判準

真實服務討論完成時，讀者應能從一個服務壓力走到具體服務取捨。看到「高峰售票」時，讀者能判斷 DynamoDB、Redis、queue、waiting room、load balancer 與 game day 各自承擔哪一段責任；看到「多租戶 SaaS 資料成長」時，讀者能判斷 PostgreSQL、MySQL sharding、Aurora、DynamoDB 或 Spanner 的機會成本。

每篇服務頁完成後要檢查三件事：第一，是否回扣分類共同認知；第二，是否引用至少一個案例或明確說明案例缺口；第三，是否提供下一步路由到主章、案例、artifact 或知識卡。
