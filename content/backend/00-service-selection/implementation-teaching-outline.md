---
title: "0.15 後端實作教學大綱"
date: 2026-05-08
description: "規劃後端各模組從觀念網路補完到服務路徑實作示範的寫作順序"
weight: 15
tags: ["backend", "implementation", "outline", "service-path"]
---

後端實作教學的核心責任是把模組觀念網路落到具體服務路徑。這一系列以概念、案例、交接路由與知識卡四層作為前置檢查，再依各分類的服務壓力決定實作正文順序。

## 系列定位

實作教學分成兩層。第一層是觀念網路補完，負責確認某個模組的主要概念是否已經能互相引用、能接到其他模組、能支援案例判讀。第二層才是服務路徑示範，負責用一條具體 user journey 展開訊號、風險、選型差異與 artifact。

這個順序很重要。若 01 database、02 cache、03 queue、05 deployment 直接進入實作，就會變成「migration 要做什麼」「Redis 要設什麼」「Kubernetes 要配什麼」的操作清單；先補觀念網路，才能讓正文回答「為什麼這個操作在這條服務路徑上成立」。

## 完整性判準

模組進入實作教學前，需要先通過五個判準。這些判準是閱讀時的完整性檢查；每個模組要用自己的服務壓力回答。

| 判準         | 具體訊號                                             | 沒通過時的風險             |
| ------------ | ---------------------------------------------------- | -------------------------- |
| 主概念成熟   | 章節能說明責任、訊號、失敗代價與下一步路由           | 實作文章會退化成工具設定   |
| 跨模組連接   | 能接到 04 觀測、06 驗證、07 資安或 08 事故流程       | 讀者不知道實作結果要交給誰 |
| 案例支撐     | 案例能回寫特定章節，並支撐觀念補強                   | 案例停留在故事層           |
| 知識卡缺口   | 需要的 mechanism 已有卡片，或明確列為待補概念        | 文章會在正文中臨時發明術語 |
| 實作入口清楚 | 能挑出一條服務路徑，並知道它產出哪些 evidence / gate | 實作順序會變成模組名稱排序 |

04、06、07、08 的 artifact backbone 實作示範已落地。01 已完成首篇服務路徑實作，02、03、05 也已完成觀念網路補完與多輪審查，下一步是把剩餘三個分類的服務路徑實作補齊並對齊 artifact 欄位基線。

## 模組完整性總表

完整性總表的責任是決定下一輪寫作先補哪一層。現階段 04/06/07/08 已完成首篇 artifact backbone，01 已完成首篇服務路徑實作，02/03/05 已完成觀念網路補完；下一批工作集中在三條服務路徑實作。

| 模組             | 現況判讀                       | 下一步重點                                   |
| ---------------- | ------------------------------ | -------------------------------------------- |
| 01 Database      | 首篇服務路徑實作已完成         | 擴充 migration 類案例回寫與 gate 對照        |
| 02 Cache / Redis | 觀念網路完成，待補服務路徑實作 | 以 stampede rollback 寫完整實作流程          |
| 03 Message Queue | 觀念網路完成，待補服務路徑實作 | 以 retry/replay handoff 寫完整實作流程       |
| 04 Observability | 實作示範已完成                 | 擴充跨案例 evidence package 回寫密度         |
| 05 Deployment    | 觀念網路完成，待補服務路徑實作 | 以 rollout + drain + rollback 寫完整實作流程 |
| 06 Reliability   | 實作示範已完成                 | 擴充 provider 依賴類 gate 的多案例對照       |
| 07 Security      | 實作示範已完成                 | 擴充 credential rotation 的多情境與回退策略  |
| 08 Incident      | 實作示範已完成                 | 擴充 control-plane 事故的 write-back 關閉力  |

這張表的判斷結論是：下一輪直接寫 02、03、05 的服務路徑實作，並引用 01 與 04/06/07/08 已落地的 artifact backbone。

服務實例層級的正文細綱已拆到 [0.16 後端服務路徑實作細綱](/backend/00-service-selection/service-path-implementation-outlines/)。0.15 保留系列順序與 backlog 判讀，0.16 負責把每個分類的服務實例、前置概念、artifact 交接、案例回寫與不適用邊界拆到後續正文撰寫可直接接手的粒度。

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

實作示範建議從 `Cache migration and stampede rollback` 開始。這篇以商品詳情或價格快取為服務路徑，產出 cache evidence package、origin protection gate、warmup plan 與 rollback trigger。

## 03 Message Queue 補完方向

訊息佇列模組的實作前提是先把「非同步工作如何被投遞、處理與恢復」講清楚。Queue 代表 request 外副作用的責任轉移，由 broker、consumer、retry、DLQ、replay 與 idempotency 共同承擔。

觀念網路應拆成三層語意。Delivery semantics 負責 ack、nack、redelivery、DLQ、retry budget 與 broker 保證；processing semantics 負責 idempotency、side effect、ordering、partition 與 downstream capacity；recovery semantics 負責 replay、checkpoint、offset ownership、poison message 與 reconciliation。這三層要分開寫，否則讀者會把「訊息有送到」誤解成「業務結果正確」。

跨模組路由要直接接到資料、觀測、可靠性與事故。Outbox 與 transaction 要回到 01；consumer lag、DLQ、retry count、duplicate side effect 要回到 04；idempotency、replay rehearsal、DLQ drain drill 要回到 06；pause consumer、開 replay、分流下游故障與補償決策要回到 08；事件 payload 含 PII 時則要接到 07 的 audit 與資料保護。

延伸知識卡方向先補：processing semantics、recovery semantics、replay window、consumer pause、event schema compatibility、DLQ drain、poison-message quarantine。已有的 [delivery semantics](/backend/knowledge-cards/delivery-semantics/)、[consumer lag](/backend/knowledge-cards/consumer-lag/)、[poison message](/backend/knowledge-cards/poison-message/)、[retry budget](/backend/knowledge-cards/retry-budget/) 與 [offset](/backend/knowledge-cards/offset/) 是第一批錨點。

實作示範建議從 `Queue consumer retry and replay handoff` 開始。這篇以 `order_created` consumer 為服務路徑，產出 idempotency evidence、DLQ handling、replay runbook 與 incident decision route。

## 05 Deployment Platform 補完方向

部署平台模組的實作前提是先把「服務如何和平台交換生命週期訊號」講清楚。部署是一組 runtime、readiness、traffic、config、secret、resource 與 rollback 條件的連續切換。

觀念網路應以 platform contract 為主線。Runtime contract 說明 image、entrypoint、runtime config、resource limit 與啟動行為。Lifecycle contract 說明 startup、[readiness](/backend/knowledge-cards/readiness/)、liveness、shutdown 與 [draining](/backend/knowledge-cards/draining/)。Traffic contract 說明 load balancer、idle timeout、sticky session、connection draining 與 request routing。Rollout contract 說明 rolling update、canary、rollback、config rollout 與 environment protection。Control-plane contract 說明 service discovery、registry、secret delivery 與 [management plane](/backend/knowledge-cards/management-plane/) 風險。

跨模組路由要讓部署平台成為 04、06、07、08 的共同落地層。它需要 04 的 per-version error rate、latency、drain completion 與 rollback effect；需要 06 的 release gate、rollback rehearsal、environment parity 與 rule rollout safety gate；需要 07 的 secret、entrypoint、artifact trust 與管理面暴露判讀；需要 08 的 rollback decision、customer impact、freeze 同批 deploy 與 incident write-back。

延伸知識卡方向先補：startup probe、drain completion、rollout batch、rollback window、config freeze、environment protection、deployment contract。已有的 [config rollout](/backend/knowledge-cards/config-rollout/)、[rollback strategy](/backend/knowledge-cards/rollback-strategy/) 與 [request routing](/backend/knowledge-cards/request-routing/) 可作為第一批引用節點。

實作示範建議從 `Deployment rollout with drain and rollback` 開始。這篇以 checkout service rollout 為服務路徑，產出 rollout plan、canary evidence、drain signal、rollback condition 與 incident decision route。

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

實作 backlog 的責任是保留後續正文順序。每篇正文都應先寫服務路徑，再寫訊號、風險、選型差異與 artifact；工具指令只在概念成立後出現。

| 分類                          | 實作文章題目                                                                             | 服務路徑                                 | 前置觀念補完狀態 |
| ----------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------- | ---------------- |
| 01 Database / Storage         | [Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/) | 訂單資料表欄位演進                       | 已完成首篇示範   |
| 02 Cache / Redis              | Cache migration and stampede rollback                                                    | 商品詳情或價格快取                       | 待寫服務路徑實作 |
| 03 Message Queue              | Queue consumer retry and replay handoff                                                  | 訂單事件 consumer                        | 待寫服務路徑實作 |
| 04 Observability              | Checkout API evidence package                                                            | checkout 同步 API                        | 已完成首篇示範   |
| 05 Deployment Platform        | Deployment rollout with drain and rollback                                               | checkout service rollout                 | 待寫服務路徑實作 |
| 06 Reliability                | Release gate for provider dependency change                                              | payment provider timeout/fallback        | 已完成首篇示範   |
| 07 Security / Data Protection | Credential rotation with scoped evidence                                                 | webhook secret / API credential rotation | 已完成首篇示範   |
| 08 Incident Workflow          | Control plane decision log and write-back                                                | rule/config rollout incident             | 已完成首篇示範   |

這份 backlog 的順序應以依賴關係安排。01 與 04/06/07/08 的首篇示範已完成，下一批主軸是回到 02/03/05 寫具體服務路徑，並直接引用既有 artifact 欄位基線。各服務實例的段落責任、案例路由與不適用邊界，依 [0.16 後端服務路徑實作細綱](/backend/00-service-selection/service-path-implementation-outlines/) 執行。

## 寫作順序

下一輪寫作的核心順序改為「以既有 artifact backbone 驅動服務實作」。這樣後續正文可直接沿同一組 evidence/gate/decision 欄位寫作，不需要再重建交接語言。正文開寫前先讀 0.16，避免把四個分類寫成共用模板。

1. 01 `Schema Migration Rollout 證據` 的完整實作示範已完成，引用 4.22 / 6.25 / 8.23。
2. 接著寫 02 `Cache migration and stampede rollback`，對齊同一組欄位與停損條件。
3. 再寫 03 `Queue consumer retry and replay handoff`，把 replay 決策接到 decision log。
4. 最後寫 05 `Deployment rollout with drain and rollback`，把切流、gate 與 write-back 串成閉環。
5. 每篇完成後回寫對應 `_index.md` 的實作入口與案例路由。

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
