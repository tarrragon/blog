---
title: "模組十一：API 設計與對外契約"
date: 2026-07-03
description: "整理 API 風格選型、資源建模、錯誤模型、版本與相容策略、冪等與對外流量語意的設計判準；主流做法與各流派的深度論證分層收錄"
weight: 11
tags: ["backend", "api-design", "contract"]
---

API 設計的核心目標是管理對外承諾的成本結構。服務內部的實作可以隨時重構、對外語意一旦被消費者依賴、每次變更都要付出遷移協調的代價；API 設計把「哪些介面行為要承諾、承諾到什麼程度、承諾怎麼分期演進」變成可推導的決策。本模組的判別問題是「這個議題出錯時、修正代價是否落在外部消費者身上」——代價落在外部的進本模組、代價收在服務內部的留在各服務模組。

## 讀者定位

本模組同時服務兩種深度的讀者。尚未建立 API 設計判準的讀者走主章：每章原則先行、用中性判準說明各風格的取捨、自己的情境該看哪些訊號。已熟悉主流做法的讀者直接進流派層：主流業界做法之外、hypermedia、型別共享 RPC、統一格式標準等風格各有適用場景；流派層給每個風格的適用邊界、失敗案例與使用觀念、主章判準層維持中性。

## 跟其他模組的責任分工

本模組收「決策還沒變成 code 之前」的設計推導；契約的驗證手段、gateway 的執行機制、事件 schema 的操作分別已有承接模組。

| 議題                                                                        | 留原模組                         | 進模組十一           |
| --------------------------------------------------------------------------- | -------------------------------- | -------------------- |
| contract 怎麼驗證（pact、CI gate）                                          | 06 留（contract test）           | —                    |
| contract 該承諾什麼、怎麼演進                                               | —                                | 版本策略、相容紀律章 |
| gateway 的路由、auth、限流實作                                              | 05 留（限流實作章屬 05 backlog） | —                    |
| 限流的對外語意與錯誤承諾                                                    | —                                | 對外流量語意章       |
| event schema registry 操作                                                  | 03 留                            | —                    |
| 同步 API 與 event 的風格選型                                                | —                                | 風格選型章           |
| retry / replay 的內部處理與驗證                                             | 03 留（處理）、06 留（驗證）     | —                    |
| [idempotency key](/backend/knowledge-cards/idempotency-key/) 的對外介面設計 | —                                | API 層冪等章         |
| 資料表結構與 schema migration                                               | 01 留                            | —                    |
| API 資源建模與資料形狀的交接                                                | —                                | 資源建模章           |
| 埋點機制、cardinality 控制與保留階梯                                        | 04 留                            | —                    |
| 契約決策要答的消費者問題與觀測維度                                          | —                                | 消費者用量觀測章     |

## 模組結構

主章承擔判準層：原則先行、每章結尾附「爭論地圖」段路由到流派層與爭論深度文章。`styles/` 承擔流派層、對應其他模組的 `vendors/` 慣例：每個流派一個目錄、深度文章給該風格的適用邊界、失敗案例與使用觀念。單一議題需要跨流派攤開時、寫成獨立的爭論深度文章、掛在對應主章之下。

## 章節規劃

主章（判準層、11.1-11.11）與六個 styles/ 流派批（rest、graphql、grpc、rpc-revival、standards、realtime）全數完成、11.11 的四篇深度文章與四篇爭論深度文章均已交付、站內連結已逐篇回填。案例支撐欄的 C 編號對應 [案例庫](/backend/11-api-design/cases/)；標「合成」的章節沒有專屬 case、內容從全庫推導、寫作時依 fact vs derive 紀律標明。案例編號慣例：章節內文首次引用寫 `[11.C<n>]` 連結、同章後續與索引表可用 `C<n>` 裸編號。

### 主章（判準層）

| 章節                                                                  | 主題                    | 核心問題                                                                                                         | 案例支撐                     |
| --------------------------------------------------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| [11.1](/backend/11-api-design/api-boundary-responsibility/)           | API 作為服務邊界的責任  | 承諾的成本結構：改內部便宜、改對外語意昂貴；違約模式與成本分配                                                   | 合成（全庫）                 |
| [11.2](/backend/11-api-design/api-style-selection/)                   | 風格選型總覽            | 消費者形狀、演進成本、操作可及性的判準軸；各風格深度收在 `styles/`                                               | 合成（C18-C34 為主）         |
| [11.3](/backend/11-api-design/resource-modeling-operation-semantics/) | 資源建模與操作語意      | 資源導向與動作導向的取捨、HTTP method / status 的承諾意義、跨資源操作                                            | C1、C3、C5（偏論證型）       |
| [11.4](/backend/11-api-design/error-model-design/)                    | 錯誤模型設計            | 可重試與終態的分類、錯誤碼 taxonomy、錯誤格式的演進空間                                                          | C35、C36、C45                |
| [11.5](/backend/11-api-design/versioning-and-deprecation/)            | 版本策略與 deprecation  | 版本是承諾的分期方式；[deprecation 生命週期](/backend/knowledge-cards/deprecation-lifecycle/)與 sunset 量測      | C10-C16、C26                 |
| [11.6](/backend/11-api-design/backward-compatibility-discipline/)     | 向後相容的變更紀律      | 什麼算 breaking（欄位、預設值、錯誤碼、時序）、變更審查 gate                                                     | C11、C13、C26、C28、C29      |
| [11.7](/backend/11-api-design/collection-interface-design/)           | 集合介面設計            | 分頁與批次的部分失敗語意、長時操作的非同步模式                                                                   | C37、C44                     |
| [11.8](/backend/11-api-design/api-idempotency-design/)                | API 層冪等設計          | idempotency key 的對外語意：誰生成、存多久、衝突怎麼回                                                           | C38-C41、C45                 |
| [11.9](/backend/11-api-design/external-traffic-semantics/)            | 對外流量語意            | rate limit / quota 作為[契約](/backend/knowledge-cards/rate-limit-contract/)：429 / Retry-After 的承諾、承諾邊界 | C19、C42、C43                |
| [11.10](/backend/11-api-design/api-governance/)                       | API 規範治理            | style guide 與 design review 作為組織能力：提案制 / Guild 制 / 分軌制三型比較、linting 進 CI、治理缺席的失敗模式 | C46-C54                      |
| [11.11](/backend/11-api-design/error-bidirectional-contract/)         | Status 與錯誤的雙向契約 | provider 與 consumer 對彼此的期望、成本外部化的判讀；四篇深度文章攤開表達力邊界、重試決策、傳播信任、回饋迴路    | C64-C77                      |
| [11.12](/backend/11-api-design/consumer-usage-observability/)         | API 消費者用量觀測      | 契約決策要能執行、前提是答得出誰在用什麼；身分維度、欄位級可答性與 cardinality 分層                              | 合成（四篇爭論文推導）       |
| [11.13](/backend/11-api-design/existing-api-retrofit/)                | 既有 API 的改造路徑     | 契約已上線、消費者改不動、觀測未建時怎麼落地；已暴露性質的三類收法與動工順序                                     | 合成（四篇爭論文的個案實跑） |

### 流派層（`styles/`）

| 目錄                                                                        | 文章候選                                                                      | 深度重點                                                                      | 案例支撐      |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------- |
| [styles/rest/](/backend/11-api-design/styles/rest/)（已完成）               | REST 這個歧義詞的選型用法、hypermedia 的適用邊界、Richardson 成熟度的實用讀法 | 把 REST 在 review 裡說死、hypermedia 落在哪個 consumer 形狀、成熟度當定位工具 | C1-C8、C14    |
| [styles/graphql/](/backend/11-api-design/styles/graphql/)（已完成）         | schema 演進、執行成本與安全、公開 API 的 GraphQL 進退                         | 同一技術在 GitHub、Shopify 與撤退團隊的不同結局、各自的情境差異               | C18-C27       |
| [styles/grpc/](/backend/11-api-design/styles/grpc/)（已完成）               | proto 演進紀律、streaming 與部署邊界、內部 RPC 的選型位置                     | field number 紀律、buf breaking check、瀏覽器邊界的妥協                       | C28-C32       |
| [styles/rpc-revival/](/backend/11-api-design/styles/rpc-revival/)（已完成） | tRPC 型別共享、JSON-RPC 的適用條件                                            | tRPC 的 monorepo 前提與語言耦合代價；JSON-RPC 在 LSP 與 MCP 的適用條件        | C23、C33、C34 |
| [styles/standards/](/backend/11-api-design/styles/standards/)（已完成）     | 採現成格式標準還是自建規範、描述格式的選型                                    | 採標準 vs 自建的組織成本、標準存活由生態預測、描述格式邊界即治理邊界          | C50-C53       |
| [styles/realtime/](/backend/11-api-design/styles/realtime/)（已完成）       | server 推 client 四機制的對外承諾差異                                         | 重連誰負責、訊息會不會漏、投遞保不保證；持久連線推送 vs webhook               | C55-C63       |

### 爭論深度文章（已完成）

各篇的結構是三拍：把流派攤開到「各自的成立前提」這一層、列出借用結論而不帶前提的失效形態、最後交出一道有方向的選型判定序。主章維持中性判準，爭議的完整交鋒收在這裡。

| 掛在 | 文章                                                                                         | 交鋒各方                                                                                               | 案例支撐                     |
| ---- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ---------------------------- |
| 11.4 | [錯誤格式之爭](/backend/11-api-design/error-format-debate/)                                  | RFC 9457、外殼配真實 status、JSON-RPC 的協定層外殼、GraphQL 的 200-with-errors、gRPC 的分層            | C35、C26、C73（含推導）      |
| 11.5 | [版本策略流派之爭](/backend/11-api-design/versioning-strategy-debate/)                       | URI 版本、header、date-based、no-versioning 派（另及 media type 與 query 變體）                        | C10、C12、C14、C17、C26、C27 |
| 11.7 | [分頁之爭](/backend/11-api-design/pagination-debate/)                                        | offset、[cursor](/backend/knowledge-cards/pagination-cursor/)、keyset；cursor 不透明性算承諾還是逃生門 | C37（含推導）                |
| 11.8 | [Idempotency key 標準化之爭](/backend/11-api-design/idempotency-key-standardization-debate/) | IETF draft 與 Stripe / PayPal 各自實作的語意差異                                                       | C39-C41                      |

案例支撐欄標「含推導」的兩篇要特別說明取材方式。錯誤格式之爭把外殼派拆成兩種：協定層外殼有 JSON-RPC 2.0 這份規範可引，而各團隊自訂的 `{success, data, error}` 外殼沒有單一規範、該部分的分析從結構性質推導。分頁之爭的 offset 失效模式在案例庫是明示缺口（獨立公開事故未找到可驗證一手文、由 C37 文內的一手描述承接）、而 cursor 條款清單同樣是從機制與消費者使用形態推導。兩篇都在正文標明推導邊界、不把推導寫成引用。

### 11.11 深度文章（已完成）

| 文章                                                                           | 主題                                             | 案例支撐                    |
| ------------------------------------------------------------------------------ | ------------------------------------------------ | --------------------------- |
| [Status 裝不下的東西](/backend/11-api-design/status-expressiveness-boundary/)  | 部分成功兩路線、202 延遲失敗、502/504 歧義       | C64-C67、C44                |
| [接收方的重試決策](/backend/11-api-design/consumer-retry-decision/)            | status 加冪等合判、retry 風暴、預算與斷路閘門    | C67-C72                     |
| [錯誤傳播與信任邊界](/backend/11-api-design/error-propagation-trust-boundary/) | 保證層選配層、產生者歧義、轉譯責任、暴露對撞     | C73-C75、C77                |
| [錯誤回報的回饋迴路](/backend/11-api-design/error-feedback-loop/)              | request-id 與 trace 契約、呈現回報分工、升級判讀 | C76、C35-C36、C61、C75、C77 |

## 交付節奏

主章先行、流派層分批。第一批交付全部主章、讓判準層完整成立、各章「爭論地圖」段先以文字描述流派層 backlog；第二批起按批次 cadence 補流派層、每批選一個 `styles/` 目錄寫完；爭論深度文章跟對應主章同批寫、讓主章的路由段有實際落點。

## Backlog

格式見 [Backlog 段格式規範](/posts/backlog-format-spec/)。

| 項目                                                                                                | 類型 | 前置條件                 | 規模 |
| --------------------------------------------------------------------------------------------------- | ---- | ------------------------ | ---- |
| 兩篇推導型爭論文章的素材替換（envelope 派的一手來源、offset 失效的獨立公開事故）                    | 案例 | 該形態的公開一手來源出現 | 小   |
| 主章「契約條款的送達」：文件 / SDK 預設值 / schema 與 type / sandbox 四層，哪些條款可編碼而不靠人讀 | 主章 | 無                       | 中   |

### 目前缺口與後續批次

主章（11.1-11.11、含 11.11 四篇深度文章）、六個流派批與四篇爭論深度文章全數完成、各主章的路由落點已補實。模組的內容層進入穩定維護狀態，表中第一列屬素材回補、第二列是四篇爭論文章的共同前提缺口；四項缺口裡的用量觀測、棕地改造與消費者形態已分別補成 11.12、11.13 與兩張知識卡。

第二列是三輪審查的共同前提盤點產出，性質跟前兩列不同：它們在單篇視角下都不落空——四篇各自給了自己那一角、讀者當下走得下去——所以逐篇審查看不到它們，是把四篇並排才浮現的。登記時要標明各篇的哪一角屬於它，否則下一輪會被逐篇修回各篇裡、缺口再度消失。

四項裡的**用量觀測**優先序最高、同時是另外三項的前置，已寫成 [11.12](/backend/11-api-design/consumer-usage-observability/)：四篇的檢查問法全部掛在它上面，缺了它，四篇提供的可操作判準同時退化成問了也答不出來的問題。剩下的一項如下。

**條款的送達**：四篇都把「寫進文件」當終點動作，而沒有一篇問消費者實際讀不讀得到、讀不讀。分頁篇自己描述的失效形態（某次無關的部署後壞掉、雙方都說不出誰違約）跟「條款寫了但沒人讀」的觀察結果完全相同。要處理的是送達分層：哪些條款只能靠人讀文件、哪些可以編進 SDK 預設值、type 定義、OpenAPI 欄位或 sandbox 行為，讓消費者不讀也不會踩。

**既有 API 的改造路徑**已寫成 [11.13](/backend/11-api-design/existing-api-retrofit/)：四篇的判定序都是綠地版，而個案實跑顯示三個真實 API 裡有兩個半的讀者站在棕地位置。該章同時承接四篇合起來缺的動工順序（觀測 → 止血 → 錯誤格式 → 分頁 → 版本）。

**消費者形態與可協調度**已建成兩張卡（[API Consumer Shape](/backend/knowledge-cards/api-consumer-shape/) 與 [Consumer Coordinability](/backend/knowledge-cards/consumer-coordinability/)）：「消費者」在四篇裡指四種行為完全不同的對象，而「可協調」原本全站無一處定義。

前兩列的性質要跟以上四列分開讀。錯誤格式之爭的 envelope 派與分頁之爭的 offset 失效模式目前由推導承接、且正文已標明推導邊界，因此它們現在是可讀的內容而非空白；找到一手來源時要做的是把推導換成引用、順帶檢查推導的結論有沒有被來源推翻。案例庫索引的「案例覆蓋缺口」段記著 offset 那一項的搜尋結果、避免重複投入同一次搜尋。

模組外的關聯缺口、記錄備查：05 部署平台模組缺 gateway 限流實作章、[11.9](/backend/11-api-design/external-traffic-semantics/) 的執行面交接目前落在該模組首頁（已在責任分工表標 backlog）。

## 案例庫

[模組十一案例庫](/backend/11-api-design/cases/) 已完成 stage 0 採集：77 個經來源驗證的公開案例、按主題分八組（REST 流派 / 版本策略 / GraphQL 進退 / gRPC 與 RPC 復興 / 介面語意 / 治理標準化 / Realtime 推送承諾 / Status-Error 雙向契約）、含反例。來源分兩類：主流做法的一手 guidelines 與演進紀錄（Stripe、GitHub、Google AIP、Zalando、Microsoft）、流派自己的一手論證（Fielding dissertation 與 blog、htmx essays、tRPC 官方文件、LSP 與 MCP spec、WHATWG 與 IETF spec）— steelman 的前提是讀過該流派自己怎麼說、批評者的轉述只能當對照。覆蓋缺口（gRPC 退回一手案例、企業治理失敗檢討等）在案例庫索引的「案例覆蓋缺口」段明示、對應章節寫作時改走 standard-driven 或通用工程知識補強。

## 知識卡

配套的 [前置知識卡片](/backend/knowledge-cards/) 四張已建卡：[Idempotency Key](/backend/knowledge-cards/idempotency-key/)（對外契約語意、跟既有 idempotency 卡分工）、[Pagination Cursor](/backend/knowledge-cards/pagination-cursor/)、[Deprecation Lifecycle](/backend/knowledge-cards/deprecation-lifecycle/)、[Rate Limit Contract](/backend/knowledge-cards/rate-limit-contract/)。既有的 [API Contract](/backend/knowledge-cards/api-contract/)、[API Gateway](/backend/knowledge-cards/api-gateway/)、[Webhook](/backend/knowledge-cards/webhook/) 卡在主章完成後回補指向本模組的推導層連結。
