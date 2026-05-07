---
title: "營運後技術轉換：語言、工具與架構何時該換"
date: 2026-05-07
description: "服務營運一段時間後，如何判讀何時該轉語言、工具或架構，並用案例說明轉換動機。"
weight: 4
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

若問題在執行時特性（延遲抖動、記憶體模型），先回 [0.2](/backend/00-service-selection/state-storage-selection/) 與 [0.5](/backend/00-service-selection/traffic-data-scale/)。若是資料庫轉換已進入執行階段，直接進 [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/)；需要放行與回滾治理時，接 [6.11 Migration Safety](/backend/06-reliability/migration-safety/)；若要看事故層教訓，接 [GitHub 2018 Oct21 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/)。

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
