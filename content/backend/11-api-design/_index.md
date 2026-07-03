---
title: "模組十一：API 設計與對外契約"
date: 2026-07-03
description: "整理 API 風格選型、資源建模、錯誤模型、版本與相容策略、冪等與對外流量語意的設計判準；主流做法與各流派的深度論證分層收錄"
weight: 11
tags: ["backend", "api-design", "contract"]
---

API 設計的核心目標是管理對外承諾的成本結構。服務內部的實作可以隨時重構、對外語意一旦被消費者依賴、每次變更都要付出遷移協調的代價；API 設計把「哪些介面行為要承諾、承諾到什麼程度、承諾怎麼分期演進」變成可推導的決策。本模組的判別問題是「這個議題出錯時、修正代價是否落在外部消費者身上」——代價落在外部的進本模組、代價收在服務內部的留在各服務模組。

## 讀者定位

本模組同時服務兩種深度的讀者。尚未建立 API 設計判準的讀者走主章：每章原則先行、用中性判準說明爭論在爭什麼、自己的情境該看哪些訊號。已熟悉主流做法的讀者直接進流派層：API 設計是長期存在爭論的領域、主流業界做法之外、hypermedia、型別共享 RPC、統一格式標準等流派持續被推廣或重新發明；流派層讓每個流派用自己的語言陳述論證、含該流派的失敗案例與適用邊界、判準層維持中性。

## 跟其他模組的責任分工

本模組收「決策還沒變成 code 之前」的設計推導；契約的驗證手段、gateway 的執行機制、事件 schema 的操作分別已有承接模組。

| 議題                               | 留原模組                         | 進模組十一           |
| ---------------------------------- | -------------------------------- | -------------------- |
| contract 怎麼驗證（pact、CI gate） | 06 留（contract test）           | —                    |
| contract 該承諾什麼、怎麼演進      | —                                | 版本策略、相容紀律章 |
| gateway 的路由、auth、限流實作     | 05 留（限流實作章屬 05 backlog） | —                    |
| 限流的對外語意與錯誤承諾           | —                                | 對外流量語意章       |
| event schema registry 操作         | 03 留                            | —                    |
| 同步 API 與 event 的風格選型       | —                                | 風格選型章           |
| retry / replay 的內部處理與驗證    | 03 留（處理）、06 留（驗證）     | —                    |
| idempotency key 的對外介面設計     | —                                | API 層冪等章         |
| 資料表結構與 schema migration      | 01 留                            | —                    |
| API 資源建模與資料形狀的交接       | —                                | 資源建模章           |

## 模組結構

主章承擔判準層：原則先行、每章結尾附「爭論地圖」段路由到流派層與爭論深度文章。`styles/` 承擔流派層、對應其他模組的 `vendors/` 慣例：每個流派一個目錄、深度文章用該流派自己的詞彙 steelman。單一爭議需要跨流派攤開時、寫成獨立的爭論深度文章、掛在對應主章之下。

## 章節規劃

主章（判準層）已全部完成；流派層與爭論深度文章是 backlog、完成後逐篇補站內連結。案例支撐欄的 C 編號對應 [案例庫](/backend/11-api-design/cases/)；標「合成」的章節沒有專屬 case、內容從全庫推導、寫作時依 fact vs derive 紀律標明。案例編號慣例：章節內文首次引用寫 `[11.C<n>]` 連結、同章後續與索引表可用 `C<n>` 裸編號。

### 主章（判準層）

| 章節                                                                  | 主題                   | 核心問題                                                                                                         | 案例支撐                |
| --------------------------------------------------------------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------- | ----------------------- |
| [11.1](/backend/11-api-design/api-boundary-responsibility/)           | API 作為服務邊界的責任 | 承諾的成本結構：改內部便宜、改對外語意昂貴；違約模式與成本分配                                                   | 合成（全庫）            |
| [11.2](/backend/11-api-design/api-style-selection/)                   | 風格選型總覽           | 消費者形狀、演進成本、操作可及性的判準軸；各風格深度收在 `styles/`                                               | 合成（C18-C34 為主）    |
| [11.3](/backend/11-api-design/resource-modeling-operation-semantics/) | 資源建模與操作語意     | 資源導向與動作導向的取捨、HTTP method / status 的承諾意義、跨資源操作                                            | C1、C3、C5（偏論證型）  |
| [11.4](/backend/11-api-design/error-model-design/)                    | 錯誤模型設計           | 可重試與終態的分類、錯誤碼 taxonomy、錯誤格式的演進空間                                                          | C35、C36、C45           |
| [11.5](/backend/11-api-design/versioning-and-deprecation/)            | 版本策略與 deprecation | 版本是承諾的分期方式；deprecation 生命週期與 sunset 量測                                                         | C10-C16、C26            |
| [11.6](/backend/11-api-design/backward-compatibility-discipline/)     | 向後相容的變更紀律     | 什麼算 breaking（欄位、預設值、錯誤碼、時序）、變更審查 gate                                                     | C11、C13、C26、C28、C29 |
| [11.7](/backend/11-api-design/collection-interface-design/)           | 集合介面設計           | 分頁與批次的部分失敗語意、長時操作的非同步模式                                                                   | C37、C44                |
| [11.8](/backend/11-api-design/api-idempotency-design/)                | API 層冪等設計         | idempotency key 的對外語意：誰生成、存多久、衝突怎麼回                                                           | C38-C41、C45            |
| [11.9](/backend/11-api-design/external-traffic-semantics/)            | 對外流量語意           | rate limit / quota 作為契約：429 / Retry-After 的承諾、承諾邊界                                                  | C19、C42、C43           |
| [11.10](/backend/11-api-design/api-governance/)                       | API 規範治理           | style guide 與 design review 作為組織能力：提案制 / Guild 制 / 分軌制三型比較、linting 進 CI、治理缺席的失敗模式 | C46-C54                 |

### 流派層（`styles/`）

| 目錄                                                          | 文章候選                                                                 | 深度重點                                                                 | 案例支撐         |
| ------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ---------------- |
| [styles/rest/](/backend/11-api-design/styles/rest/)（已完成） | REST 語意學之爭、hypermedia 與 HATEOAS 復興、Richardson 成熟度的實用讀法 | Fielding 原義與業界 pragmatic JSON-over-HTTP 的落差、HAL / Siren 到 htmx | C1-C9            |
| `styles/graphql/`                                             | schema 演進、執行成本與安全、公開 API 的 GraphQL 進退                    | 同一技術在 GitHub、Shopify 與撤退團隊的三種結局、各自的情境差異          | C18-C27          |
| `styles/grpc/`                                                | proto 演進紀律、streaming 語意與部署邊界、內部 RPC 的選型位置            | field number 紀律、buf breaking check、瀏覽器邊界的妥協                  | C28-C32          |
| `styles/rpc-revival/`                                         | tRPC 與型別共享、JSON-RPC 的重生場景                                     | tRPC 的 monorepo 前提與語言耦合代價；JSON-RPC 在 LSP 與 MCP 的存活場景   | C23、C33、C34    |
| `styles/standards/`                                           | JSON:API 與 OData 的標準化嘗試、OpenAPI 與 AsyncAPI 生態                 | 「統一 response 格式」的標準每隔一段時間重來一次、每次留下部分遺產的原因 | C50-C53          |
| `styles/realtime/`                                            | WebSocket / SSE / long-polling / webhook 的對外承諾差異                  | 同是 server 推 client、各機制的失敗模式與重連語意差異                    | 缺、寫作前補採集 |

### 爭論深度文章

| 掛在 | 爭議                   | 交鋒各方                                                              | 案例支撐           |
| ---- | ---------------------- | --------------------------------------------------------------------- | ------------------ |
| 11.5 | 版本策略流派之爭       | URI 版本、header、Stripe date-based、Fielding 的 no-versioning 派     | C10、C12、C14、C26 |
| 11.4 | 錯誤格式之爭           | RFC 9457 problem+json、envelope 包裝、GraphQL 的 200-with-errors 慣例 | C35、C36           |
| 11.7 | 分頁之爭               | offset、cursor、keyset；cursor 不透明性算承諾還是逃生門               | C37                |
| 11.8 | idempotency key 標準化 | IETF draft 與 Stripe / PayPal 各自實作的語意差異                      | C39-C41            |

## 交付節奏

主章先行、流派層分批。第一批交付全部主章、讓判準層完整成立、各章「爭論地圖」段先以文字描述流派層 backlog；第二批起按批次 cadence 補流派層、每批選一個 `styles/` 目錄寫完；爭論深度文章跟對應主章同批寫、讓主章的路由段有實際落點。`styles/realtime/` 的案例庫尚未採集、該批開工前先補一輪採集。

## 案例庫

[模組十一案例庫](/backend/11-api-design/cases/) 已完成 stage 0 採集：54 個經來源驗證的公開案例、按主題分六組（REST 流派 / 版本策略 / GraphQL 進退 / gRPC 與 RPC 復興 / 介面語意 / 治理標準化）、含 8 個反例。來源分兩類：主流做法的一手 guidelines 與演進紀錄（Stripe、GitHub、Google AIP、Zalando、Microsoft）、流派自己的一手論證（Fielding dissertation 與 blog、htmx essays、tRPC 官方文件、LSP 與 MCP spec）— steelman 的前提是讀過該流派自己怎麼說、批評者的轉述只能當對照。覆蓋缺口（realtime 主題、gRPC 退回一手案例、企業治理失敗檢討等）在案例庫索引的「案例覆蓋缺口」段明示、對應章節寫作時改走 standard-driven 或通用工程知識補強。

## 知識卡候選

配套的 [前置知識卡片](/backend/knowledge-cards/) 候選：idempotency-key（對外語意、跟 processing-semantics 拆卡）、pagination-cursor、deprecation-lifecycle、rate-limit-contract。既有的 [API Contract](/backend/knowledge-cards/api-contract/)、[API Gateway](/backend/knowledge-cards/api-gateway/)、[Webhook](/backend/knowledge-cards/webhook/) 卡在主章完成後回補指向本模組的推導層連結。
