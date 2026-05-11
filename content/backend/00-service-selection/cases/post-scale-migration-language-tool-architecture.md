---
title: "營運後技術轉換：語言、工具與架構何時該換"
date: 2026-05-07
description: "服務營運一段時間後，如何判讀何時該轉語言、工具或架構，並用案例說明轉換動機。"
weight: 4
tags: ["backend", "service-selection", "case-study", "migration"]
---

這個案例的核心責任是把「營運後轉換」變成可判讀決策，而不是技術潮流追逐。服務在成長期常會遇到早期選型與現況負載不再匹配，此時轉換的重點是風險收斂與效率改善，而不是語言偏好。

## 大量真實案例與轉換原因

| 案例                                                | 轉換類型              | 為什麼轉換                                                                             |
| --------------------------------------------------- | --------------------- | -------------------------------------------------------------------------------------- |
| Slack：PHP 逐步遷移到 Hack                          | 語言/型別系統         | 以漸進式靜態型別提升重構安全與開發效率，降低 runtime 才暴露型別錯誤的成本。            |
| Discord：Read States 服務 Go 重寫為 Rust            | 語言/執行模型         | Go 服務在特定負載下出現 GC 造成的週期性延遲尖峰，Rust 以無 GC 記憶體模型降低延遲抖動。 |
| Dropbox：Python 2 轉 Python 3                       | 語言/runtime 生命週期 | Python 2 EOL 與型別工具鏈演進壓力，驅動全面升級並降低長期維護風險。                    |
| Dropbox：內部 RPC 轉向 gRPC（Courier）              | 工具/協定標準化       | 多語言服務擴張後，需要統一傳輸契約、提高跨團隊可維護性與可觀測性。                     |
| GitLab：單一資料庫拆成 Main/CI 資料庫               | 資料層架構            | 單庫承載產品與 CI 工作負載，容量與干擾風險上升，需以職責拆分換取穩定性。               |
| Notion：Postgres 單庫轉分片                         | 資料層架構            | 寫入與資料量成長造成熱點與容量壓力，以分片提升可擴展性與故障隔離。                     |
| Shopify：Rails 後端引入 Vitess 水平擴充             | 資料層工具            | MySQL 垂直擴充成本上升，需在不中斷服務前提下取得分片與路由能力。                       |
| Shopify：Ruby 導入 Sorbet 靜態型別                  | 工具/語言治理         | 大型程式碼庫重構與跨團隊協作風險高，需要型別訊號降低變更不確定性。                     |
| Figma：服務遷移至 Kubernetes                        | 平台/部署工具         | 手工或半自動部署流程難以支撐規模成長，需要統一調度、回滾與資源治理能力。               |
| Cloudflare：邊緣系統由 C/NGINX 模組逐步改寫 Rust    | 語言/安全性           | 記憶體安全與可維護性需求提升，在高效能路徑引入 Rust 降低記憶體錯誤風險。               |
| Slack：關鍵服務從單體拓撲遷移到 Cell-based 架構     | 架構/隔離策略         | 以降低爆炸半徑與提高冗餘為目標，將重大故障影響限制在局部 cell。                        |
| Uber：大規模微服務治理轉向 Domain-oriented 邊界重整 | 架構/組織對齊         | 服務數量擴張後依賴複雜度暴增，需要把技術邊界與業務邊界對齊以降低協作與故障傳染成本。   |
| Meta：MySQL 大規模場景導入 MyRocks                  | 儲存引擎/成本優化     | 寫入放大與儲存成本壓力上升，透過新儲存引擎換取空間效率與寫入效能。                     |

## 案例分組判讀

### 語言與型別系統轉換

語言轉換常見於「延遲抖動不可接受」或「重構風險不可接受」兩類壓力。前者多是 runtime/記憶體模型問題，後者多是大型程式碼庫可維護性問題。

- 代表案例：Slack PHP -> Hack、Discord Go -> Rust、Dropbox Python 2 -> Python 3、Cloudflare C/NGINX -> Rust
- 主要動機：降低 tail latency、提升記憶體安全、對抗 runtime EOL、引入更強型別訊號

### 資料層與儲存架構轉換

資料層轉換通常不是為了追新技術，而是單體資料庫在容量、隔離與可恢復性上出現結構性瓶頸。

- 代表案例：GitLab Main/CI split、Notion Postgres sharding、Shopify Vitess、Meta MyRocks
- 主要動機：解耦不同負載、降低熱點、取得水平擴充、降低儲存成本

### 平台與部署工具轉換

平台轉換通常發生在部署頻率提升後，原本的人工作業或弱自動化無法承擔發布風險。

- 代表案例：Figma 遷移 Kubernetes、Dropbox RPC 標準化到 gRPC
- 主要動機：統一部署控制面、縮短發布/回滾時間、提升跨語言協作效率

### 架構邊界重整

架構重整通常是「故障會跨邊界放大」或「團隊邊界與系統邊界失配」時的修正動作。

- 代表案例：Slack cellular architecture、Uber domain-oriented microservice governance
- 主要動機：縮小 blast radius、讓服務責任與組織責任對齊、降低跨團隊耦合

## 三倍擴充案例池（42）

這份案例池的核心責任是提供「可直接回寫實作」的案例母體，而不是只做公司清單。下面分成兩層：外部官方遷移案例（偏選型與轉換動機）與站內已整理案例（偏實作、驗證、事故教訓）。

### A. 外部官方遷移案例（20）

| 案例                                   | 轉換主題                 | 實作討論入口                                                        |
| -------------------------------------- | ------------------------ | ------------------------------------------------------------------- |
| Slack PHP -> Hack                      | 漸進型別化與大型重構安全 | [1.6](/backend/01-database/database-migration-playbook/)            |
| Discord Go -> Rust                     | 延遲長尾與 GC 抖動治理   | [6.11](/backend/06-reliability/migration-safety/)                   |
| Dropbox Python 2 -> 3                  | runtime EOL 與生態升級   | [6.8](/backend/06-reliability/release-gate/)                        |
| Dropbox RPC -> gRPC                    | 協定標準化與跨語言維運   | [0.4](/backend/00-service-selection/operations-platform-selection/) |
| GitLab Main/CI DB split                | 單庫拆分與負載隔離       | [1.6](/backend/01-database/database-migration-playbook/)            |
| Notion Postgres sharding               | 熱點與容量壓力分片       | [0.5](/backend/00-service-selection/traffic-data-scale/)            |
| Shopify MySQL -> Vitess                | 水平擴充與線上遷移       | [1.6](/backend/01-database/database-migration-playbook/)            |
| Shopify Ruby + Sorbet                  | 動態語言型別治理         | [6.10](/backend/06-reliability/contract-testing/)                   |
| Figma -> Kubernetes                    | 部署控制面平台化         | [0.4](/backend/00-service-selection/operations-platform-selection/) |
| Cloudflare C/NGINX -> Rust             | 記憶體安全與效能路徑重寫 | [0.6](/backend/00-service-selection/cost-risk-tradeoffs/)           |
| Slack monolith topology -> cellular    | blast radius 局部化      | [0.7](/backend/00-service-selection/failure-observability-design/)  |
| Uber domain-oriented microservices     | 服務邊界與組織對齊       | [0.1](/backend/00-service-selection/service-capability-map/)        |
| Meta MySQL -> MyRocks                  | 儲存成本與寫入效率       | [0.2](/backend/00-service-selection/state-storage-selection/)       |
| Pinterest HBase -> TiDB                | 零停機儲存遷移           | [6.11](/backend/06-reliability/migration-safety/)                   |
| Pinterest 新 wide-column DB（RocksDB） | 資料層能力換血           | [0.2](/backend/00-service-selection/state-storage-selection/)       |
| Meta MySQL Raft deploy                 | failover 工具化          | [6.7](/backend/06-reliability/dr-rollback-rehearsal/)               |
| Shopify MySQL upgrade program          | 大規模升級治理           | [6.8](/backend/06-reliability/release-gate/)                        |
| GitLab major PostgreSQL upgrade        | 主版本升級與回退窗       | [6.11](/backend/06-reliability/migration-safety/)                   |
| AWS shuffle sharding adoption          | 多租戶隔離重整           | [6.14](/backend/06-reliability/dependency-reliability-budget/)      |
| Cloudflare observability stack內建化   | 觀測平台內生化           | [4.18](/backend/04-observability/observability-operating-model/)    |

### B. 站內可回寫實作案例池（22）

| 案例                                                                                                                              | 轉換主題                  | 實作討論入口                                                                                    |
| --------------------------------------------------------------------------------------------------------------------------------- | ------------------------- | ----------------------------------------------------------------------------------------------- |
| [Stripe：Idempotency 與零停機遷移](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/)                 | 交易安全 + migration 並行 | [6.11](/backend/06-reliability/migration-safety/)                                               |
| [Pinterest：快取可靠性與容量驚奇治理](/backend/06-reliability/cases/pinterest/cache-reliability-and-capacity-surprises/)          | 快取策略與容量重整        | [6.9](/backend/06-reliability/capacity-cost/)                                                   |
| [Amazon：Shuffle Sharding 與 Cell 邊界](/backend/06-reliability/cases/amazon/shuffle-sharding-and-cell-boundary/)                 | cell/shard 重整           | [0.7](/backend/00-service-selection/failure-observability-design/)                              |
| [Meta：Region Failover 與可靠性邊界](/backend/06-reliability/cases/meta/region-failover-and-reliability-boundaries/)              | 區域切換能力演進          | [6.7](/backend/06-reliability/dr-rollback-rehearsal/)                                           |
| [Shopify：BFCM 容量治理與 Game Day](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)                            | 高峰前治理轉換            | [6.6](/backend/06-reliability/load-testing/)                                                    |
| [Google：Error Budget 發布門檻](/backend/06-reliability/cases/google/error-budget-policy-and-release-gating/)                     | 從速度導向轉為預算導向    | [6.2](/backend/06-reliability/slo-error-budget/)                                                |
| [Microsoft：變更治理與可靠性門檻](/backend/06-reliability/cases/microsoft/change-management-and-reliability-governance/)          | 變更流程平台化            | [6.8](/backend/06-reliability/release-gate/)                                                    |
| [Spotify：平台工程與可靠性契約](/backend/06-reliability/cases/spotify/platform-engineering-and-reliability-contracts/)            | 團隊自助平台化            | [0.4](/backend/00-service-selection/operations-platform-selection/)                             |
| [LinkedIn：Capacity Headroom 與 On-call 分層](/backend/06-reliability/cases/linkedin/capacity-headroom-and-oncall-tiering/)       | 容量與值班模型重整        | [6.9](/backend/06-reliability/capacity-cost/)                                                   |
| [Netflix：Steady State、Chaos 與 FIT](/backend/06-reliability/cases/netflix/steady-state-chaos-and-fit/)                          | 驗證方法轉換              | [6.5](/backend/06-reliability/chaos-testing/)                                                   |
| [Honeycomb：Burn Rate 驅動操作](/backend/06-reliability/cases/honeycomb/burn-rate-driven-reliability-operations/)                 | 告警治理轉換              | [4.13](/backend/04-observability/sli-slo-signal/)                                               |
| [GitHub 2018 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/)             | 跨區 DB 拓撲決策轉換      | [1.6](/backend/01-database/database-migration-playbook/)                                        |
| [Reddit 2023 Kubernetes 升級事故](/backend/08-incident-response/cases/reddit/2023-kubernetes-upgrade-incident/)                   | 平台升級失敗模式          | [5.2](/backend/05-deployment-platform/kubernetes-deployment/)                                   |
| [Discord 2022 Gateway 容量事件](/backend/08-incident-response/cases/discord/2022-gateway-capacity-event/)                         | 容量與連線模型調整        | [0.5](/backend/00-service-selection/traffic-data-scale/)                                        |
| [Cloudflare 2019 Regex CPU Outage](/backend/08-incident-response/cases/cloudflare/2019-regex-cpu-outage/)                         | 規則系統推送模型調整      | [8.13](/backend/08-incident-response/incident-workflow-automation-boundary/)                    |
| [Cloudflare 2023 Control Plane Token Incident](/backend/08-incident-response/cases/cloudflare/2023-control-plane-token-incident/) | 控制面信任邊界重整        | [7.12](/backend/07-security-data-protection/security-control-handoff-to-delivery-and-incident/) |
| [Fastly 2021 全域 Edge 配置事故](/backend/08-incident-response/cases/fastly/2021-june-global-edge-config-triggered-outage/)       | 配置發布流程轉換          | [6.8](/backend/06-reliability/release-gate/)                                                    |
| [AWS S3 2017 US-EAST-1 事件](/backend/08-incident-response/cases/aws-s3/2017-us-east-1-service-disruption/)                       | 控制面操作模型重整        | [8.3](/backend/08-incident-response/containment-recovery-strategy/)                             |
| [Atlassian 2022 多租戶刪除事故](/backend/08-incident-response/cases/atlassian/2022-april-multi-tenant-deletion-outage/)           | tenant 安全邊界重整       | [0.6](/backend/00-service-selection/cost-risk-tradeoffs/)                                       |
| [Azure AD 2021 身分控制面事件](/backend/08-incident-response/cases/azure-ad/2021-identity-control-plane-disruption/)              | 身分服務依賴治理          | [8.20](/backend/08-incident-response/customer-impact-assessment/)                               |
| [GCP 2019 多服務網路擁塞事件](/backend/08-incident-response/cases/gcp/2019-us-network-congestion-multi-service-incident/)         | 區域網路依賴重整          | [6.14](/backend/06-reliability/dependency-reliability-budget/)                                  |
| [Heroku 2021 Routing 控制事件](/backend/08-incident-response/cases/heroku/2021-routing-control-event/)                            | 路由控制面恢復策略        | [8.3](/backend/08-incident-response/containment-recovery-strategy/)                             |

這兩層合計 42 個案例。使用方式是先在 A 層找轉換動機，再到 B 層找可操作證據與失敗模式，最後回寫到 `01/04/06/08` 的正文。

## 跨分類覆蓋與缺口

這一段的核心責任是避免案例池被資料庫議題主導。選型與轉換在實務上會同時涉及快取、訊息傳遞、觀測、部署、安全與事故治理，因此案例覆蓋要跨分類配置。

| 分類                          | 目前案例密度 | 代表案例入口                                                                                                                      | 目前缺口與補查方向                                                               |
| ----------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 01 Database / Storage         | 高           | [1.7 Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/)                                  | 已有遷移流程與 rollout evidence；下一步補更多 vendor 轉換對照                    |
| 02 Cache / Redis              | 中低         | [Pinterest：快取可靠性與容量驚奇治理](/backend/06-reliability/cases/pinterest/cache-reliability-and-capacity-surprises/)          | 補「快取策略轉換」案例（cache-aside -> write-through、multi-layer cache）        |
| 03 Message Queue              | 中低         | [Amazon：Shuffle Sharding 與 Cell 邊界](/backend/06-reliability/cases/amazon/shuffle-sharding-and-cell-boundary/)                 | 補「自管 broker -> managed queue」與「語義轉換（at-least-once / exactly-once）」 |
| 04 Observability              | 中           | [Honeycomb：Burn Rate 驅動操作](/backend/06-reliability/cases/honeycomb/burn-rate-driven-reliability-operations/)                 | 補「監控平台遷移」與「OpenTelemetry 導入遷移」案例                               |
| 05 Deployment Platform        | 中           | [Reddit：2023 Kubernetes 升級事故](/backend/08-incident-response/cases/reddit/2023-kubernetes-upgrade-incident/)                  | 補「自建部署 -> Kubernetes/GitOps」轉換案例                                      |
| 06 Reliability                | 高           | [Stripe：Idempotency 與零停機遷移](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/)                 | 持續補不同產業的 rollout/rollback 對照                                           |
| 07 Security / Data Protection | 中低         | [Cloudflare 2023 Control Plane Token Incident](/backend/08-incident-response/cases/cloudflare/2023-control-plane-token-incident/) | 補「憑證、金鑰、身分邊界治理轉換」案例                                           |
| 08 Incident Response          | 高           | [GitHub 2018 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/)             | 補「轉換期間事故」專題，建立遷移失敗模式索引                                     |

## 覆蓋門檻與缺口追蹤

這份追蹤表的核心責任是把「案例夠不夠」變成可量化判斷，而不是主觀感覺。

| 分類                          | 最低門檻（篇） | 目前已收錄（篇） | 缺口（篇） | 狀態 | 下一步                           |
| ----------------------------- | -------------- | ---------------- | ---------- | ---- | -------------------------------- |
| 01 Database / Storage         | 12             | 12               | 0          | 達標 | 補 vendor 轉換對照深度           |
| 02 Cache / Redis              | 10             | 10               | 0          | 達標 | 進入案例深度擴寫與反例補充       |
| 03 Message Queue              | 10             | 10               | 0          | 達標 | 進入案例深度擴寫與反例補充       |
| 04 Observability              | 10             | 10               | 0          | 達標 | 進入案例深度擴寫與反例補充       |
| 05 Deployment Platform        | 10             | 10               | 0          | 達標 | 進入案例深度擴寫與反例補充       |
| 06 Reliability                | 10             | 12               | 0          | 達標 | 補產業多樣性與 rollback 成本對照 |
| 07 Security / Data Protection | 10             | 10               | 0          | 達標 | 進入案例深度擴寫與反例補充       |
| 08 Incident Response          | 10             | 12               | 0          | 達標 | 補「轉換期間事故」專題索引       |

## 下一輪優先順序

門檻已達標，下一輪優先順序改為：

1. 每分類補「失敗反例」與「轉換失敗回退案例」
2. 每分類補「同議題不同規模企業」對照
3. 把案例回寫到章節正文中的判讀訊號與 tripwire 欄位

## 回退失敗專題索引

這個索引的核心責任是讓讀者在「已經出錯」時，能快速找到對應回退失敗模式，而不是從頭重讀選型章節。

| 分類                          | 回退失敗專題                                                                                                     |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| 02 Cache / Redis              | [2.C9 反例：快取切換失敗](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)              |
| 03 Message Queue              | [3.C9 反例：語義切換失敗](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)             |
| 04 Observability              | [4.C9 反例：OTel 訊號漂移](/backend/04-observability/cases/failure-otel-migration-signal-drift/)                 |
| 05 Deployment Platform        | [5.C9 反例：切流未先 drain](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)       |
| 07 Security / Data Protection | [7.C9 反例：憑證輪替失敗](/backend/07-security-data-protection/cases/failure-credential-rotation-without-scope/) |

## 回退判讀寫法

回退判讀的核心責任是把失敗條件寫回該分類自己的業務語境。快取看的是回源壓力與資料新鮮度；queue 看的是語義、lag 與重播；observability 看的是訊號語意漂移；deployment 看的是切流、draining 與連線生命週期；security 看的是身份、憑證作用域與控制面擴散。

這些判讀不能抽成同一份模板。每次寫案例時，先回答該分類自己的問題：哪個業務路徑受影響、哪個訊號最早失真、哪個回退動作會降低傷害、哪份證據能證明回退有效。

## 下一輪補查清單（非 DB 優先）

下一輪補查會優先補目前中低密度分類，目標是讓每一類至少有 8 到 12 個可回寫案例。

1. Cache：快取策略遷移與失效治理（multi-layer、eviction、warmup）
2. Queue：broker/語義轉換與 replay 風險控制
3. Observability：監控平台遷移與資料品質治理
4. Deployment：部署平台轉換與灰度/回滾策略
5. Security：控制面信任邊界與憑證機制轉換

## 第二批外部案例補充（非 DB 類）

這一批的核心責任是把中低密度分類補到可用水位，讓 `02/03/04/05/07` 都有可引用的真實轉換案例，而不是只有資料庫案例可用。

| 分類                   | 案例                                                   | 轉換焦點                               | 回寫入口                                                                                 |
| ---------------------- | ------------------------------------------------------ | -------------------------------------- | ---------------------------------------------------------------------------------------- |
| Cache                  | Meta：Cache made consistent                            | cache invalidation 一致性治理升級      | [2.1](/backend/02-cache-redis/cache-aside/)                                              |
| Cache                  | Meta：mcrouter at scale                                | 單機快取轉成跨區路由層                 | [2.4](/backend/02-cache-redis/high-concurrency-access/)                                  |
| Cache                  | Meta：CacheLib + Kangaroo                              | DRAM-only 快取轉向 flash-friendly 架構 | [2.5](/backend/02-cache-redis/ttl-eviction/)                                             |
| Cache                  | Shopify：Marshal -> MessagePack cache migration        | 快取序列化格式遷移與雙軌相容           | [2.1](/backend/02-cache-redis/cache-aside/)                                              |
| Cache                  | Shopify：Shop App write-through cache                  | read-heavy 路徑轉 write-through        | [2.1](/backend/02-cache-redis/cache-aside/)                                              |
| Queue                  | Meta：FOQS disaster-ready migration                    | 區域佇列轉全域架構且零停機             | [3.3](/backend/03-message-queue/durable-queue/)                                          |
| Queue                  | LinkedIn：Running Kafka at Scale                       | 單叢集使用模式轉 tiered cluster        | [3.1](/backend/03-message-queue/broker-basics/)                                          |
| Queue                  | LinkedIn：TopicGC                                      | Kafka topic 治理從手動轉自動回收       | [3.2](/backend/03-message-queue/consumer-design/)                                        |
| Queue                  | VMware Tanzu CloudHealth：Kafka -> Amazon MSK          | 自管 broker 轉 managed streaming       | [3.1](/backend/03-message-queue/broker-basics/)                                          |
| Queue                  | Slack：Scaling job queue                               | 背景工作通道轉 Kafka + Redis 組合      | [3.4](/backend/03-message-queue/outbox-pattern/)                                         |
| Observability          | AWS：X-Ray SDK/Daemon -> OpenTelemetry migration       | vendor SDK 轉 OTel 標準化              | [4.21](/backend/04-observability/telemetry-pipeline/)                                    |
| Observability          | Google Cloud：OTLP support in Cloud Trace (2025)       | 專有 ingest 轉 OTLP 標準入口           | [4.21](/backend/04-observability/telemetry-pipeline/)                                    |
| Observability          | AWS：ADOT 建立集中觀測平台                             | 多代理轉單一 OTel pipeline             | [4.18](/backend/04-observability/observability-operating-model/)                         |
| Observability          | AWS：EKS + ADOT + X-Ray/CloudWatch                     | 既有監控拆散轉標準化管線               | [4.7](/backend/04-observability/tracing-context/)                                        |
| Observability          | Honeycomb：Burn rate operations                        | 告警規則轉 error budget 驅動治理       | [4.13](/backend/04-observability/sli-slo-signal/)                                        |
| Deployment             | Tradeshift：self-hosted K8s -> EKS (zero downtime)     | 自管控制面轉 managed control plane     | [5.2](/backend/05-deployment-platform/kubernetes-deployment/)                            |
| Deployment             | Condé Nast：K8s platform modernization on EKS          | 多團隊異質集群轉統一平台               | [5.2](/backend/05-deployment-platform/kubernetes-deployment/)                            |
| Deployment             | Orbitera：AWS -> GKE migration                         | 基礎平台重置與容器編排轉換             | [5.2](/backend/05-deployment-platform/kubernetes-deployment/)                            |
| Deployment             | Mobileye：workloads -> EKS                             | 資源調度模式轉 managed K8s             | [5.2](/backend/05-deployment-platform/kubernetes-deployment/)                            |
| Deployment             | Miro：microservices/K8s -> EKS managed                 | 自維運平台轉 managed service 組合      | [5.2](/backend/05-deployment-platform/kubernetes-deployment/)                            |
| Security/Control Plane | Cloudflare：2026 route leak incident                   | 路由政策自動化治理重整                 | [7.16](/backend/07-security-data-protection/security-governance-exception-and-tripwire/) |
| Security/Control Plane | Cloudflare：2026 BYOIP BGP withdrawal                  | 控制面變更保護與回退策略               | [8.3](/backend/08-incident-response/containment-recovery-strategy/)                      |
| Security/Control Plane | Cloudflare：2023 control-plane token incident          | token 管理邊界與供應鏈信任調整         | [7.11](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)  |
| Security/Control Plane | Azure AD：2021 identity control-plane disruption       | 身分控制面故障隔離與恢復路由           | [8.8](/backend/08-incident-response/security-vs-operational-incident/)                   |
| Security/Control Plane | Microsoft 365：2023 suite-wide authentication incident | 身分服務相依邊界重整                   | [8.20](/backend/08-incident-response/customer-impact-assessment/)                        |

## 第二批補查來源

- Meta：Cache consistency / mcrouter / CacheLib / Kangaroo / FOQS / MyRocks migration
- LinkedIn Engineering：Kafka at scale / TopicGC
- AWS：CloudHealth Kafka -> MSK、X-Ray -> OTel migration、ADOT/EKS 實務、EKS 遷移案例
- Google Cloud：OTLP in Cloud Trace、Orbitera -> GKE
- Shopify Engineering：cache serialization migration、write-through cache
- Cloudflare Post-mortem：2023/2026 control-plane 與路由事件

## 判讀訊號

| 訊號                   | 判讀重點                    | 對應章節                                                            |
| ---------------------- | --------------------------- | ------------------------------------------------------------------- |
| 延遲分布長尾惡化       | 是平均值問題還是尖峰問題    | [0.5](/backend/00-service-selection/traffic-data-scale/)            |
| 重構風險持續升高       | 型別/契約是否不足以支撐變更 | [0.6](/backend/00-service-selection/cost-risk-tradeoffs/)           |
| 故障常跨服務放大       | 架構邊界是否缺乏隔離能力    | [0.7](/backend/00-service-selection/failure-observability-design/)  |
| 發布節奏被品質問題拖慢 | 問題在語言、工具鏈或架構層  | [0.4](/backend/00-service-selection/operations-platform-selection/) |

## 轉換決策資料要求

| 資料面向     | 最低需要的證據                                     | 若缺失會發生什麼事               |
| ------------ | -------------------------------------------------- | -------------------------------- |
| 成本面       | 現況維運成本與轉換成本（人力、基礎設施、機會成本） | 轉換中途停擺或 ROI 判斷失真      |
| 風險面       | 故障型態、爆炸半徑、回退時間                       | 上線後故障放大但無法快速止血     |
| 性能面       | P50/P95/P99、吞吐、尖峰流量下的行為                | 只優化平均值，長尾問題仍存在     |
| 組織面       | 團隊技能分布、訓練成本、維運責任邊界               | 工具換了但組織無法承接           |
| 生命週期面   | 依賴版本 EOL、供應商策略、平台相容性               | 被動升級，且在最差時機被迫遷移   |
| 遷移可行性面 | 雙寫/雙跑策略、灰度範圍、指標切換門檻、回滾條件    | 遷移無法分段驗證，風險一次性爆發 |

## 轉換前要先回答的三個問題

1. 現有問題是「局部優化可解」還是「結構性不匹配」？
2. 轉換後的收益是性能、可靠性、開發效率哪一項，如何量化？
3. 遷移期間如何維持雙軌可運行與回退能力？

如果三個問題答不清楚，通常代表先做局部治理比全面轉換更穩定。

## 常見誤區

把「技術新舊」當成轉換理由，容易忽略遷移期成本。可靠做法是先界定症狀與邊界，再決定要換語言、換工具，或只換架構切分方式。

## 下一步路由

若問題在執行時特性（延遲抖動、記憶體模型），先回 [0.2](/backend/00-service-selection/state-storage-selection/) 與 [0.5](/backend/00-service-selection/traffic-data-scale/)。若是資料庫轉換已進入執行階段，直接進 [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/)；需要把 production migration 寫成 evidence、gate 與 decision log，接 [1.7 Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/)；需要放行與回滾治理時，接 [6.11 Migration Safety](/backend/06-reliability/migration-safety/)；若要看事故層教訓，接 [GitHub 2018 Oct21 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/)。

## 引用源

- [Hacklang at Slack: A Better PHP](https://slack.engineering/hacklang-at-slack-a-better-php/)：Slack 說明 PHP 到 Hack 的遷移動機與型別收益。
- [How Big Technical Changes Happen at Slack](https://slack.engineering/how-big-technical-changes-happen-at-slack/)：Slack 逐步遷移與組織推進方式。
- [Why Discord is switching from Go to Rust](https://discord.com/blog/why-discord-is-switching-from-go-to-rust)：Discord 說明 Go→Rust 的延遲與 GC 觀察。
- [Slack’s Migration to a Cellular Architecture](https://slack.engineering/slacks-migration-to-a-cellular-architecture/)：Slack 從單體拓撲轉到 cell 架構的原因。
- [The Long-Awaited Python 3 Upgrade at Dropbox](https://dropbox.tech/application/the-long-awaited-python-3-upgrade-at-dropbox)：Dropbox 的 Python 2 -> 3 遷移動機與推進方式。
- [Rewriting the heart of our sync engine](https://dropbox.tech/infrastructure/rewriting-the-heart-of-our-sync-engine)：Dropbox 在核心效能路徑重寫的轉換決策脈絡。
- [Courier: Driving the first years of gRPC](https://dropbox.tech/infrastructure/courier-driving-the-first-years-of-grpc)：Dropbox 內部 RPC 到 gRPC 的演進背景。
- [Splitting database into Main and CI](https://about.gitlab.com/blog/2022/06/02/splitting-database-into-main-and-ci/)：GitLab 的資料庫職責拆分案例。
- [Sharding Postgres at Notion](https://www.notion.com/blog/sharding-postgres-at-notion)：Notion 分片遷移與容量壓力背景。
- [Horizontally scaling the Rails backend of Shop App with Vitess](https://shopify.engineering/blogs/engineering/horizontally-scaling-the-rails-backend-of-shop-app-with-vitess)：Shopify 導入 Vitess 的原因與方式。
- [How Shopify Is Adopting Sorbet](https://shopify.engineering/adopting-sorbet)：Shopify 在大型 Ruby 程式碼庫導入型別系統。
- [Migrating Figma to Kubernetes](https://www.figma.com/blog/migrating-figma-to-kubernetes/)：Figma 的平台遷移原因與收益。
- [A Rust regex engine in NGINX](https://blog.cloudflare.com/rust-nginx-module/)：Cloudflare 在高效能路徑導入 Rust 的案例。
- [Domain-Oriented Microservice Architecture](https://www.uber.com/en-GB/blog/microservice-architecture/)：Uber 在規模化後重整服務邊界。
- [MyRocks: A space- and write-optimized MySQL database](https://engineering.fb.com/2016/08/31/core-infra/myrocks-a-space-and-write-optimized-mysql-database/)：Meta 導入 MyRocks 的成本與效能動機。
