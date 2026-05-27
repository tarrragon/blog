# 後端實作教學大綱

> **Status**: backend 教材 author-facing outline — 規劃各模組從觀念網路補完到服務路徑實作示範的寫作順序。原為 `content/backend/00-service-selection/implementation-teaching-outline.md`（weight 0.15）、屬寫作 SoP、不是讀者面內容、2026-05-27 移到 `.codex/outlines/backend/`。
>
> **適用對象**：寫 backend 系列章節的 author / Codex / Claude agent。寫稿前讀本檔對齊三層教學順序（分類通用認知 → 服務路徑示範 → 實體服務討論）。

後端實作教學的核心責任是先把分類層的共同認知補完整，再把模組觀念網路落到具體服務路徑。這一系列以概念、案例、交接路由與知識卡四層作為前置檢查，先讓讀者理解資料庫、快取、佇列與部署平台各自承擔的服務責任，再進入 MySQL、PostgreSQL、Redis、Kafka、Kubernetes 或其他實體服務的討論。

## 系列定位

實作教學分成三層。第一層是分類通用認知，負責回答這一類 backend 能力承擔什麼責任、有哪些失敗代價、哪些術語是共同語言。第二層是服務路徑示範，負責用一條具體 user journey 展開訊號、風險、選型差異與 artifact。第三層才是實體服務或 App 討論，例如 MySQL / MSSQL / PostgreSQL、Redis / Valkey、Kafka / RabbitMQ、Kubernetes / ELB 等具體選型與操作差異。

這個順序很重要。若 01 database、02 cache、03 queue、05 deployment 直接進入實體服務，就會變成「MySQL 要怎麼設」「Redis command 怎麼用」「Kafka topic 怎麼開」「Kubernetes YAML 怎麼寫」的操作清單；先補分類通用認知，才能讓後續正文回答「為什麼這個工具能力在這條服務責任上成立」。

## 完整性判準

模組進入實作教學前，需要先通過五個判準。這些判準是閱讀時的完整性檢查；每個模組要用自己的服務壓力回答。

| 判準         | 具體訊號                                             | 沒通過時的風險             |
| ------------ | ---------------------------------------------------- | -------------------------- |
| 主概念成熟   | 章節能說明責任、訊號、失敗代價與下一步路由           | 實作文章會退化成工具設定   |
| 跨模組連接   | 能接到 04 觀測、06 驗證、07 資安或 08 事故流程       | 讀者不知道實作結果要交給誰 |
| 案例支撐     | 案例能回寫特定章節，並支撐觀念補強                   | 案例停留在故事層           |
| 知識卡缺口   | 需要的 mechanism 已有卡片，或明確列為待補概念        | 文章會在正文中臨時發明術語 |
| 實作入口清楚 | 能挑出一條服務路徑，並知道它產出哪些 evidence / gate | 實作順序會變成模組名稱排序 |

04、06、07、08 的 artifact backbone 實作示範已落地。01、02、03、05 都已有首篇服務路徑示範，也已補上進入實體服務或 App 討論前需要的第一批共同觀念正文。共同認知文章已補上實體服務討論承接點，下一步是整理後續實體服務文章的切入順序。

## 模組完整性總表

完整性總表的責任是決定下一輪寫作先補哪一層。現階段 01/02/03/05 已有首篇服務路徑示範，也已補第一批分類通用認知，讓後續實體服務討論有共同語言。

| 模組             | 現況判讀                         | 下一步重點                                  |
| ---------------- | -------------------------------- | ------------------------------------------- |
| 01 Database      | 共同認知、承接點與首篇示範已完成 | 規劃 MySQL / PostgreSQL / MSSQL 等實體服務  |
| 02 Cache / Redis | 共同認知、承接點與首篇示範已完成 | 規劃 Redis / Valkey / Memcached 等實體服務  |
| 03 Message Queue | 共同認知、承接點與首篇示範已完成 | 規劃 Kafka / RabbitMQ / SQS / NATS 等服務   |
| 04 Observability | 實作示範已完成                   | 擴充跨案例 evidence package 回寫密度        |
| 05 Deployment    | 共同認知、承接點與首篇示範已完成 | 規劃 Kubernetes / ELB / systemd 等服務      |
| 06 Reliability   | 實作示範已完成                   | 擴充 provider 依賴類 gate 的多案例對照      |
| 07 Security      | 實作示範已完成                   | 擴充 credential rotation 的多情境與回退策略 |
| 08 Incident      | 實作示範已完成                   | 擴充 control-plane 事故的 write-back 關閉力 |

這張表的判斷結論是：下一輪可以規劃實體服務或 App 層。服務路徑示範文章作為案例承接點，共同觀念正文提供分類基線。

服務路徑層級的正文細綱已拆到 [0.16 後端服務路徑實作細綱](/backend/00-service-selection/service-path-implementation-outlines/)。0.15 保留系列順序與 backlog 判讀，0.16 負責把每個分類的服務路徑、前置概念、artifact 交接、案例回寫與不適用邊界拆到後續正文撰寫可直接接手的粒度；真實服務層的後續順序則交給 [0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/)。

## 分類缺口盤點

分類缺口盤點的責任是把「能力地圖」改成「學習路線」。Backend 目前已經有完整的服務能力分類，但教學設計要進一步回答讀者如何從一個 checkout 系統問題，依序理解正式狀態、暫存副本、非同步交接、訊號證據、部署生命週期、可靠性驗證、控制面風險、事故協作與容量成本。

| 學習分類         | 現況判讀                             | 主要教學缺口                                       | 大綱動作                                                        | Checkout episode |
| ---------------- | ------------------------------------ | -------------------------------------------------- | --------------------------------------------------------------- | ---------------- |
| 00 選型入口      | 已有服務分類與總體教學設計           | 需要把讀者入口固定成 learning journey              | 以本頁作為分類 backlog，0.17 作為服務層 backlog                 | E0               |
| 01 Database      | 主章、共同認知與首篇路徑已完成       | 實體服務順序需要回扣正式狀態與 migration           | 先排 SQL baseline，再排 embedded、document / KV、global SQL     | E1               |
| 02 Cache         | 主章、共同認知與 stampede 路徑已完成 | 服務頁要先分清副本語意與回源保護                   | 先排 Redis / Valkey，再排 Memcached、DragonflyDB、managed cache | E2               |
| 03 Queue         | 主章、共同認知與 replay 路徑已完成   | 服務頁要分開 delivery、processing、recovery        | 先排 broker baseline，再排 managed delivery、event log、stream  | E3               |
| 04 Observability | artifact backbone 已完成             | 服務頁需要回到 signal quality 與 evidence package  | 服務頁先排 telemetry baseline，再排 SaaS / cloud provider       | E1-E7            |
| 05 Deployment    | 主章、共同認知與 rollout 路徑已完成  | 服務頁需要分開 workload、traffic、infra state      | 先排 workload runtime，再排 traffic、config、infra state        | E4               |
| 06 Reliability   | artifact backbone 已完成             | 工具頁需要分開 release gate、load test、chaos、SLO | 先排 gate / CI，再排 load、fault injection、SLO governance      | E5               |
| 07 Security      | 主章與大量控制服務頁已成形           | 缺口在群組順序與控制面路由                         | 以 identity、secret、edge、supply chain、detection 分組         | E6               |
| 08 Incident      | 主章與協作工具頁已成形               | deep article 密度低於服務頁密度                    | 先排 paging，再排 incident command、status、postmortem          | E4 / E6          |
| 09 Performance   | 主章、case 與 vendor 入口已成形      | 需要把工具選型接回容量與成本決策                   | 先排 workload / load test，再排 replay、profiling、FinOps       | E7               |

這份缺口表的判斷結論是：下一輪先調整章節順序與服務頁路由，再進入正文撰寫。已完成首篇服務路徑示範的分類，可以直接把真實服務頁排成教學序列；artifact backbone 成熟的分類，則優先補服務頁與案例回寫的密度。

## 章節順序調整原則

章節順序調整的責任是讓讀者沿著服務責任逐步擴張，而非沿著工具名稱跳讀。每一批新章節都先回答「這個服務責任在 checkout journey 的哪一段出現」，再決定要補分類共同認知、服務路徑示範、真實服務頁或案例回寫。

1. 先補正式狀態與副本責任：01 Database 與 02 Cache 先建立 source of truth、freshness、origin protection 與資料修復語言。
2. 再補跨程序交接：03 Message Queue 接在資料與快取之後，讓讀者理解同步請求外的副作用如何投遞、處理與恢復。
3. 接著補訊號與部署交接：04 Observability 與 05 Deployment 把變更、流量、readiness、drain 與 rollback 變成可檢查 artifact。
4. 再補驗證與控制面：06 Reliability 與 07 Security 用 release gate、experiment、identity、secret 與供應鏈控制，保護前面已建立的服務責任。
5. 最後補協作、容量與成本：08 Incident 與 09 Performance 把事故決策、容量預測、效能退化與成本曲線回寫到前面分類。

章節順序可以依讀者入口調整，但每條路線都要保留這個依賴關係。若某篇服務頁需要先談 Kubernetes、Kafka 或 Redis，也要在開頭把它接回正式狀態、副本、交接、訊號或控制面中的一個責任。

## 01 Database / Storage 補完方向

資料庫模組的實作前提是先把「正式狀態如何演進」講清楚。資料庫集中承擔服務的 [source of truth](/backend/knowledge-cards/source-of-truth/)、交易邊界、查詢邊界、migration 風險與資料修復責任。

觀念網路應沿五條線展開。第一條是 state ownership，說明哪些資料由資料庫正式承擔，哪些只是 cache、index 或 event log 的派生狀態。第二條是 query boundary，說明交易查詢、列表查詢、報表查詢與對帳查詢的責任差異。第三條是 transaction boundary，連到 [isolation level](/backend/knowledge-cards/isolation-level/)、deadlock、retry 與 idempotency。第四條是 migration safety，連到 [schema migration](/backend/knowledge-cards/schema-migration/)、[Expand / Contract](/backend/knowledge-cards/expand-contract/)、[backfill](/backend/knowledge-cards/backfill/) 與 [dual write](/backend/knowledge-cards/dual-write/)。第五條是 reconciliation，說明資料錯誤發生後如何驗證、修復、回寫與稽核。

跨模組路由要特別補四個方向。資料變更需要 04 的 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 保存 validation query、row count、slow query 與 replication lag；需要 06 的 [Migration Safety](/backend/06-reliability/migration-safety/) 與 [Release Gate](/backend/06-reliability/release-gate/) 決定何時放行；需要 07 的資料保護與 audit 邊界；需要 08 的 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/) 保留 pause、rollback、fail-forward 的判斷。

延伸知識卡方向先列為候選，不在正文中臨時創造術語：migration validation、read compatibility、cutover window、reconciliation、data repair runbook、fail-forward migration。已有卡片則優先引用，不重複定義。

首篇實作示範已完成： [Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/)。這篇以訂單資料表付款狀態欄位演進為服務路徑，產出 migration plan、validation query、rollback condition 與 incident decision route。

## 02 Cache / Redis 補完方向

快取模組的實作前提是先把「暫存副本如何保護正式狀態」講清楚。Redis 或 cache 的核心是資料新鮮度、回源壓力、容量淘汰、一致性風險與控制面擴散的取捨。

觀念網路應沿六條線展開。第一條是 cache copy vs source of truth，讓讀者知道 cache value 何時只是可重建副本，何時已經被誤用成正式狀態。第二條是 freshness window，說明 stale data 在產品上能接受多久。第三條是 invalidation，連到 [cache invalidation](/backend/knowledge-cards/cache-invalidation/)、TTL、versioned key 與 event-driven invalidation。第四條是 origin protection，連到 [hot key](/backend/knowledge-cards/hot-key/)、[cache stampede](/backend/knowledge-cards/cache-stampede/)、[thundering herd](/backend/knowledge-cards/thundering-herd/) 與 [cache warmup](/backend/knowledge-cards/cache-warmup/)。第五條是 data shape，說明 string、hash、set、sorted set、stream 的服務語意。第六條是 cache migration，說明序列化格式、key schema、TTL 策略與回退條件。

跨模組路由要讓快取從「效能技巧」回到服務可靠性。它連到 01 的 source of truth 與 query pressure，連到 04 的 hit rate、origin QPS、stale read、eviction 與 latency evidence，連到 06 的 warmup rehearsal、origin protection threshold 與 experiment stop condition，連到 08 的 cache stampede incident、降級決策與 write-back。

延伸知識卡方向先補：freshness window、origin protection、request coalescing、negative cache、cache key versioning、cache serialization migration。已有的 [stale data](/backend/knowledge-cards/stale-data/)、[cache prefetching](/backend/knowledge-cards/cache-prefetching/) 與 [cache hit rate](/backend/knowledge-cards/cache-hit-rate/) 可作為第一批引用節點。

服務路徑示範已完成於 [2.9 Cache Migration 與 Stampede Rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/)。這篇以商品詳情或價格快取為服務路徑，產出 cache evidence package、origin protection gate、warmup plan 與 rollback trigger。

## 03 Message Queue 補完方向

訊息佇列模組的實作前提是先把「非同步工作如何被投遞、處理與恢復」講清楚。Queue 代表 request 外副作用的責任轉移，由 broker、consumer、retry、DLQ、replay 與 idempotency 共同承擔。

觀念網路應拆成三層語意。Delivery semantics 負責 ack、nack、redelivery、DLQ、retry budget 與 broker 保證；processing semantics 負責 idempotency、side effect、ordering、partition 與 downstream capacity；recovery semantics 負責 replay、checkpoint、offset ownership、poison message 與 reconciliation。這三層要分開寫，否則讀者會把「訊息有送到」誤解成「業務結果正確」。

跨模組路由要直接接到資料、觀測、可靠性與事故。Outbox 與 transaction 要回到 01；consumer lag、DLQ、retry count、duplicate side effect 要回到 04；idempotency、replay rehearsal、DLQ drain drill 要回到 06；pause consumer、開 replay、分流下游故障與補償決策要回到 08；事件 payload 含 PII 時則要接到 07 的 audit 與資料保護。

延伸知識卡方向先補：processing semantics、recovery semantics、replay window、consumer pause、event schema compatibility、DLQ drain、poison-message quarantine。已有的 [delivery semantics](/backend/knowledge-cards/delivery-semantics/)、[consumer lag](/backend/knowledge-cards/consumer-lag/)、[poison message](/backend/knowledge-cards/poison-message/)、[retry budget](/backend/knowledge-cards/retry-budget/) 與 [offset](/backend/knowledge-cards/offset/) 是第一批錨點。

服務路徑示範已完成於 [3.8 Queue Consumer Retry 與 Replay Handoff](/backend/03-message-queue/queue-consumer-retry-replay-handoff/)。這篇以 `order_created` consumer 為服務路徑，產出 idempotency evidence、DLQ handling、replay runbook 與 incident decision route。

## 05 Deployment Platform 補完方向

部署平台模組的實作前提是先把「服務如何和平台交換生命週期訊號」講清楚。部署是一組 runtime、readiness、traffic、config、secret、resource 與 rollback 條件的連續切換。

觀念網路應以 platform contract 為主線。Runtime contract 說明 image、entrypoint、runtime config、resource limit 與啟動行為。Lifecycle contract 說明 startup、[readiness](/backend/knowledge-cards/readiness/)、liveness、shutdown 與 [draining](/backend/knowledge-cards/draining/)。Traffic contract 說明 load balancer、idle timeout、sticky session、connection draining 與 request routing。Rollout contract 說明 rolling update、canary、rollback、config rollout 與 environment protection。Control-plane contract 說明 service discovery、registry、secret delivery 與 [management plane](/backend/knowledge-cards/management-plane/) 風險。

跨模組路由要讓部署平台成為 04、06、07、08 的共同落地層。它需要 04 的 per-version error rate、latency、drain completion 與 rollback effect；需要 06 的 release gate、rollback rehearsal、environment parity 與 rule rollout safety gate；需要 07 的 secret、entrypoint、artifact trust 與管理面暴露判讀；需要 08 的 rollback decision、customer impact、freeze 同批 deploy 與 incident write-back。

延伸知識卡方向先補：startup probe、drain completion、rollout batch、rollback window、config freeze、environment protection、deployment contract。已有的 [config rollout](/backend/knowledge-cards/config-rollout/)、[rollback strategy](/backend/knowledge-cards/rollback-strategy/) 與 [request routing](/backend/knowledge-cards/request-routing/) 可作為第一批引用節點。

服務路徑示範已完成於 [5.8 Deployment Rollout with Drain and Rollback](/backend/05-deployment-platform/deployment-rollout-drain-rollback/)。這篇以 checkout service rollout 為服務路徑，產出 rollout plan、canary evidence、drain signal、rollback condition 與 incident decision route。

## 04 / 06 / 07 / 08 實作入口

04、06、07、08 的共同狀態是概念層與首篇 artifact backbone 都已完成。它們現在作為 01、02、03、05 服務路徑正文的共同交接基線。

| 模組 | 第一篇完整示範                              | 服務路徑                 | 主要產出                                           |
| ---- | ------------------------------------------- | ------------------------ | -------------------------------------------------- |
| 04   | Checkout API evidence package               | 同步 API + 外部 payment  | dashboard、saved query、trace sample、gap note     |
| 06   | Release gate for provider dependency change | payment timeout/fallback | readiness result、experiment evidence、gate        |
| 07   | Credential rotation with scoped evidence    | webhook secret rotation  | scope map、audit evidence、rollback window         |
| 08   | Control plane decision log and write-back   | rule/config rollout      | intake、decision log、impact note、write-back item |

這四篇要互相引用，並各自保留服務語境。Checkout API 的觀測證據、payment provider 的 release gate、credential rotation 的 scope map、control plane 的 decision log，各自承擔不同業務風險。

## 全分類實作 Backlog

實作 backlog 的責任是保留後續正文順序。每篇正文都應先寫分類責任與服務壓力，再寫訊號、風險、選型差異與 artifact；工具指令只在概念成立後出現。

## 進入實體服務前的共同認知清單

共同認知清單的責任是阻止文章太早跳進個別服務設定。MySQL、PostgreSQL、MSSQL、Redis、Kafka、RabbitMQ、Kubernetes、ELB 這些服務之間有重要差異，但讀者先需要理解該分類本身的責任邊界，後續才能判斷各服務能力差異。

| 分類                   | 已補共同正文                               | 要回答的共同問題                                                          |
| ---------------------- | ------------------------------------------ | ------------------------------------------------------------------------- |
| 01 Database / Storage  | State Ownership and Query Boundary         | 哪些資料是正式狀態，交易查詢、列表查詢、報表查詢與對帳查詢如何分責任      |
| 01 Database / Storage  | Reconciliation and Data Repair             | 資料錯誤發生後如何驗證、修復、稽核與回寫事故證據                          |
| 02 Cache / Redis       | Cache Copy Boundary and Freshness          | 快取何時只是可重建副本，何時會影響交易、權限或配額正確性                  |
| 02 Cache / Redis       | Cache Data Shape and Access Pattern        | string、hash、set、sorted set、stream 或多層 cache 如何反映服務語意       |
| 03 Message Queue       | Processing and Recovery Semantics          | 投遞成功、處理成功與恢復成功為何是三個不同判斷                            |
| 03 Message Queue       | Event Contract and Replay Boundary         | event schema、idempotency key、replay window 與補償如何先於 broker 選型   |
| 05 Deployment Platform | Platform Lifecycle Contract                | runtime、startup、readiness、liveness、shutdown 與 drain 如何組成平台合約 |
| 05 Deployment Platform | Traffic, Config and Control Plane Boundary | 流量、設定、secret、service discovery 與管理面如何分責任與回退            |

這份清單完成後，才進入實體服務或 App 層。實體服務文章的責任是比較 PostgreSQL / MySQL / MSSQL、Redis / Valkey、Kafka / RabbitMQ / SQS、Kubernetes / systemd / ELB 的具體能力差異；共同認知文章的責任是先定義分類語言。

| 分類                          | 實作文章題目                                                                             | 服務路徑                                 | 前置觀念補完狀態 |
| ----------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------- | ---------------- |
| 01 Database / Storage         | [Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/) | 訂單資料表欄位演進                       | 已完成首篇示範   |
| 02 Cache / Redis              | Cache migration and stampede rollback                                                    | 商品詳情或價格快取                       | 已完成（2.9）    |
| 03 Message Queue              | Queue consumer retry and replay handoff                                                  | 訂單事件 consumer                        | 已完成（3.8）    |
| 04 Observability              | Checkout API evidence package                                                            | checkout 同步 API                        | 已完成首篇示範   |
| 05 Deployment Platform        | Deployment rollout with drain and rollback                                               | checkout service rollout                 | 已完成（5.8）    |
| 06 Reliability                | Release gate for provider dependency change                                              | payment provider timeout/fallback        | 已完成首篇示範   |
| 07 Security / Data Protection | Credential rotation with scoped evidence                                                 | webhook secret / API credential rotation | 已完成首篇示範   |
| 08 Incident Workflow          | Control plane decision log and write-back                                                | rule/config rollout incident             | 已完成首篇示範   |

這份 backlog 的順序應以依賴關係安排。01/02/03/05 的首篇服務路徑示範與分類通用認知已完成，下一批主軸可以進入實體服務或 App 討論。服務路徑示範的段落責任、案例路由與不適用邊界，依 [0.16 後端服務路徑實作細綱](/backend/00-service-selection/service-path-implementation-outlines/) 執行；真實服務介紹、同類服務取捨與 vendor / tool 導覽，依 [0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/) 執行。

## 後續寫作順序

後續寫作的核心順序是「規劃實體服務文章，並回扣分類共同認知」。這樣後續討論 MySQL、PostgreSQL、Redis、Kafka 或 Kubernetes 時，正文能先回到分類責任，再比較具體工具能力。實體服務正文開寫前先讀本頁的共同認知清單，避免把服務路徑示範誤判成分類完整。

1. 先規劃 01 的 relational database / document database / storage 類實體服務文章。
2. 再規劃 02 的 Redis / Valkey / Memcached / CDN / local cache 類文章。
3. 接著規劃 03 的 Kafka / RabbitMQ / SQS / NATS / Redis Streams 類文章。
4. 最後規劃 05 的 Kubernetes / systemd / load balancer / service mesh / secret manager 類文章。
5. 每篇實體服務文章都要回扣對應共同認知，不直接從工具設定起手；具體批次與完成判準見 [0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/)。

## 完成判準

完成判準的核心是讀者能從一個服務問題走到觀念、案例、artifact 與下一步路由，理解工具名稱背後的服務責任。

| 判準           | 具體訊號                                                 |
| -------------- | -------------------------------------------------------- |
| 觀念網路成立   | 每個薄弱模組都有主概念、跨模組引用與待補知識卡方向       |
| 服務路徑清楚   | 每篇實作文章都有明確 user journey、依賴、訊號與失敗代價  |
| 選型差異成立   | 每篇能說明何時簡單方案足夠，何時需要切換服務能力         |
| artifact 可用  | 文章產出的 evidence、handoff、decision log 可被演練填寫  |
| 案例能回寫     | 案例教訓能回寫到 01/02/03/05 的主概念，也能接到 04/06/08 |
| 沒有模板化失真 | 章節依服務壓力寫作，不用共用欄位覆蓋不同情境             |

## Artifact 欄位對齊基線

跨章節對齊時，欄位名稱以 04/06/08 的主章作為單一基線，避免各模組自創同義欄位導致交接落差。

- Evidence package（對齊 4.20）：`Source`、`Time range`、`Query link`、`Owner`、`Data quality`、`Confidence`、`Known gap`。
- Release gate（對齊 6.8）：`Gate decision`、`Checks`、`Stop condition`、`Rollback window`、`Owner`。
- Incident decision log（對齊 8.19）：`Timestamp`、`Decision`、`Context`、`Evidence`、`Owner`、`Expected effect`、`Rollback condition`。

各分類正文可以用自己的敘事語言，但交付 artifact 時，欄位名稱與責任要回到這組基線。
