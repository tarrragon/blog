---
title: "Backend 服務實務指南"
date: 2026-04-22
description: "整理資料庫、快取、訊息佇列、觀測、部署、可靠性驗證與資安等後端服務能力"
weight: 34
---

Backend 教材的核心目標是整理「應該被 application interface 隔離」的外部服務能力。語言教材負責各自的語法、標準庫、並發或非同步模型、測試方法與 interface / protocol 邊界；Backend 教材負責資料庫、快取、訊息佇列、觀測平台、部署平台、系統可靠性與資安資料保護。

這個切分讓不同語言的學習保持清楚：Go、Python 或其他後端語言可以各自說明如何定義抽象邊界、處理取消與逾時、回傳錯誤、寫 fake 或 contract test；Backend 章節則說明 SQLite、PostgreSQL、Redis、RabbitMQ、broker、migration、metrics、tracing、Kubernetes、identity、permission、[TLS / mTLS](knowledge-cards/tls-mtls/)、[WAF](knowledge-cards/waf/)、[Secret Management](knowledge-cards/secret-management/)、[Audit Log](knowledge-cards/audit-log/) 等具體技術如何運作。

Backend 是多個後端語言系列共用的實作層。未來若新增 frontend、data engineering、machine learning、mobile 或其他非後端主題，也可以用同樣方式把共用實作知識抽成獨立資料夾，讓特定語言教材保留在語言本身的能力邊界。

## 教材邊界

| 類型       | 放在語言教材                                                                                    | 放在 Backend 教材                                                                                              |
| ---------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 資料存取   | repository port、interface / protocol、context / cancellation、error、contract test             | SQLite、PostgreSQL、transaction、schema migration、index、isolation level                                      |
| 快取       | cache port、TTL 概念、資料複製邊界、失效策略的程式邊界                                          | Redis 資料型別、eviction、distributed lock、cache aside、pub/sub                                               |
| 訊息傳遞   | channel / queue abstraction、backpressure、publisher port、processor、idempotency interface     | RabbitMQ、NATS、Kafka、Redis Streams、ack/nack、dead-letter queue、consumer group                              |
| 可觀測性   | 標準 logger、runtime 訊號、diagnostics endpoint、trace context 邊界、錯誤分類欄位               | log aggregation、Prometheus、OpenTelemetry、trace、dashboard、alert                                            |
| 部署平台   | graceful shutdown、health/readiness、signal handling、resource limit、failover hook 的程式設計  | Kubernetes、systemd、load balancer、container image、service discovery                                         |
| 可靠性驗證 | unit test、table-driven / parameterized test、race / async test、integration test、故障路徑測試 | CI pipeline、load test、fuzz campaign、chaos testing、環境治理                                                 |
| 資安保護   | middleware、policy interface、error mapping、redaction helper、security test                    | identity、[authorization](knowledge-cards/authorization/)、[TLS / mTLS](knowledge-cards/tls-mtls/)、[WAF](knowledge-cards/waf/)、[Secret Management](knowledge-cards/secret-management/)、[Audit Log](knowledge-cards/audit-log/)、[data masking](knowledge-cards/data-masking/) |

## 教學模組

### [前置知識卡片](knowledge-cards/)

用原子化卡片整理 source of truth、transaction、migration、CDC、backfill、cutover、timeout、backoff、jitter、retry storm、load shedding、bulkhead、fallback、TTL、cache warmup、singleflight、broker、consumer lag、prefetch、redelivery、partition、offset、idempotency、outbox、backpressure、log schema、metrics、trace、SLO、error budget、authorization、BOLA、mass assignment、data masking、[Secret Management](knowledge-cards/secret-management/)、[TLS / mTLS](knowledge-cards/tls-mtls/)、[Audit Log](knowledge-cards/audit-log/) 與 [Website Certificate Lifecycle](knowledge-cards/website-certificate-lifecycle/) 等後端 domain knowhow。這些卡片負責補足服務選型文章中的先備知識，讓章節可以專注在需求判讀與服務取捨。

### [模組零：後端需求分析與服務選型](00-service-selection/)

整理後端需求分類、流量形狀、資料量、失敗代價、成本模型、錯誤定位、觀測訊號、備援切換與服務能力地圖，再從需求類型判斷資料庫、快取、訊息佇列、觀測平台與部署平台的選型方向。

### [模組一：資料庫與持久化](01-database/)

整理 relational database、embedded database、transaction、migration、repository adapter 與資料一致性。

### [模組二：快取與 Redis](02-cache-redis/)

整理 cache aside、TTL、eviction、Redis data structure、distributed lock、pub/sub 與快取一致性。

### [模組三：訊息佇列與事件傳遞](03-message-queue/)

整理 durable queue、broker、ack/nack、retry、dead-letter queue、outbox、idempotency 與 consumer 設計。

### [模組四：可觀測性平台](04-observability/)

整理 structured log aggregation、metrics、tracing、dashboard、alert 與操作診斷流程。

### [模組五：部署平台與網路入口](05-deployment-platform/)

整理 Kubernetes、systemd、load balancer、container、service discovery、rolling update 與平台合約。

### [模組六：可靠性驗證流程](06-reliability/)

整理 CI、load test、fuzz、chaos testing、測試環境與回歸驗證策略。

### [模組七：資安與資料保護](07-security-data-protection/)

整理權限分級、伺服器防護、資料遮罩、傳輸保護、密鑰管理、稽核追蹤與資料匯出安全。

### [模組八：事故處理與復盤](08-incident-response/)

整理事故分級、指揮流程、止血回復、通訊節奏、復盤閉環與演練機制。

## 與語言教材的關係

Backend 教材提供跨語言的服務概念與操作語意。語言教材可以回連 Backend，說明特定語言如何實作 repository port、publisher port、cache interface、middleware、async worker 或 observability boundary；Backend 章節本身應保持獨立，讓 Go、Python、Node.js、Java、C#、PHP、Rust 或其他後端語言都能使用同一套服務判斷。

Backend 章節討論具體服務時，應加入跨語言適配評估。這個評估讓讀者從 runtime、語言生態與抽象邊界理解服務使用方式，並取代特定語言教材作為前置依賴。

1. 這個服務需要語言端提供哪些抽象邊界，例如 interface、protocol、adapter、middleware、worker 或 client wrapper。
2. 哪些 runtime 特性會影響服務使用方式，例如 thread model、event loop、async/await、goroutine、process model、GC、connection pool 或 cancellation。
3. 哪些語言特性適合這個服務，例如明確 context 傳遞、型別化錯誤、成熟 ORM、生態套件、背景 worker 框架或 observability SDK。
4. 哪些語言特性會形成風險，例如隱式全域狀態、阻塞 I/O 混入 event loop、連線池生命週期不清楚、例外處理邊界模糊或套件抽象過厚。
5. 語言教材若需要示範實作，應由語言教材回連 Backend；Backend 則保持跨語言概念完整。

這個方向讓 Backend 保持可重用：它先說明服務如何選型、如何使用、如何操作、如何承擔成本；各語言系列再各自說明如何接上這些服務。

## 與案例的關係

Backend 案例應從服務需求出發。高併發、長連線、事件處理、資料庫、雲端基礎設施、資安與可觀測性都可以用跨語言案例說明；案例的責任是提供需求情境，服務章節的責任是說明後端能力本身。

## 前置知識卡片規範

Backend 文章中的高密度術語應優先抽成前置知識卡片。Source of truth、transaction boundary、schema migration、timeout、deadline、exponential backoff、jitter、retry storm、thundering herd、transient failure、partial failure、cascading failure、load shedding、token bucket、dependency isolation、bulkhead、fallback、fail fast、retry budget、TTL、eviction、broker、consumer lag、dead-letter queue、replay runbook、重複投遞、idempotency、outbox、backpressure、rate limit、log schema、metrics、trace context、SLO、authorization、data masking、secret management、[TLS / mTLS](knowledge-cards/tls-mtls/)、[website certificate lifecycle](knowledge-cards/website-certificate-lifecycle/)、[certificate rotation and renewal](knowledge-cards/certificate-rotation-renewal/)、[certificate revocation](knowledge-cards/certificate-revocation/)、audit log、降級、停機、readiness 與 graceful shutdown 都是 domain knowhow；它們需要說明系統責任、產品後果、操作訊號與排障方式。

每張卡片應維持一個概念，並至少包含概念位置、可觀察訊號、接近真實網路服務的例子與設計責任。卡片內容要能獨立閱讀；定義只是一個入口，完整卡片要讓讀者理解這個概念在事故、擴容、部署或資料修復時會如何影響決策。

## 暫定章節來源

目前 Backend 目錄先承接多個後端語言都會遇到的外部實作議題：

- 資料庫 transaction、schema migration、isolation level
- durable queue、outbox、idempotency store
- Redis、distributed cache、presence store
- metrics、tracing、log aggregation、OpenTelemetry
- Kubernetes、systemd、load balancer、container runtime
- CI、load test、fuzz、chaos testing
- identity、[authorization](knowledge-cards/authorization/)、[data masking](knowledge-cards/data-masking/)、[TLS / mTLS](knowledge-cards/tls-mtls/)、[website certificate lifecycle](knowledge-cards/website-certificate-lifecycle/)、[Secret Management](knowledge-cards/secret-management/)、[Audit Log](knowledge-cards/audit-log/)
- incident severity、command model、escalation policy、rollback strategy、post-incident review

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

每篇討論具體服務實體的章節，例如 PostgreSQL、Redis、RabbitMQ、Kafka、Prometheus、OpenTelemetry、Kubernetes、[WAF](knowledge-cards/waf/)、[Secret Management](knowledge-cards/secret-management/) 或 [IAM](knowledge-cards/iam/)，都必須包含「成本權衡與機會成本」段落。這個段落至少回答：

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
4. 強型別語言如何表達 schema、錯誤分類與 contract test。
5. 動態語言如何用 protocol、typing、fixture、runtime validation 或 framework convention 保護邊界。
6. 語言生態的 ORM、broker client、observability SDK、security middleware 是否成熟，是否會隱藏重要操作語意。

---

_文件版本：v0.1.0_
_最後更新：2026-04-22_
_系列狀態：分類索引建立中_
