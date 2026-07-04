---
title: "模組十一案例庫：API 設計與對外契約"
date: 2026-07-03
description: "API 風格流派、版本與相容、介面語意、規範治理的已驗證公開案例集；含反例與覆蓋缺口標明"
weight: 99
tags: ["backend", "api-design", "case-study"]
---

本案例庫收模組十一（API 設計與對外契約）的寫作素材：77 個經來源驗證的公開案例、按主題分組。每個案例是薄殼形態（觀察 / 判讀 / 對應大綱 / 引用源）、stage 1 audit 後依需要升級為 rich case。所有 source URL 於採集時（2026-07）經實際取回驗證可訪且內容對應；二手來源與 IETF draft 狀態在各檔內標明。

## REST 與 hypermedia 流派（C1-C9）

| 編號 | 案例                                                                                           | 主議題                     | 類型         |
| ---- | ---------------------------------------------------------------------------------------------- | -------------------------- | ------------ |
| C1   | [Fielding 論文第 5 章](/backend/11-api-design/cases/rest-fielding-dissertation-ch5/)           | REST 定義基準、約束推導    | anchor       |
| C2   | [Fielding hypertext-driven](/backend/11-api-design/cases/rest-fielding-hypertext-driven/)      | 語意學之爭引爆點           | anchor       |
| C3   | [Richardson 成熟度模型](/backend/11-api-design/cases/rest-fowler-richardson-maturity-model/)   | 分級階梯與其 caveat        | anchor       |
| C4   | [Gross：REST 的反義詞](/backend/11-api-design/cases/rest-gross-opposite-of-rest/)              | 語意漂移史、復興派論證     | anchor       |
| C5   | [htmx HATEOAS essay](/backend/11-api-design/cases/rest-htmx-hateoas-html-necessity/)           | 透支帳戶範例、操作型判別法 | anchor       |
| C6   | [HAL spec](/backend/11-api-design/cases/rest-kelly-hal-spec/)                                  | JSON hypermedia 標準化過期 | 邊緣         |
| C7   | [Siren spec](/backend/11-api-design/cases/rest-swiber-siren-adoption/)                         | 表達力與採用曲線脫鉤       | 邊緣         |
| C8   | [Morris：pragmatic 無 HATEOAS](/backend/11-api-design/cases/rest-morris-pragmatic-no-hateoas/) | 收益假設逐條拆解           | 反例（對照） |
| C9   | [twobithistory 史觀](/backend/11-api-design/cases/rest-twobithistory-misappropriation/)        | 被挪用的論文、第三方定調   | 邊緣（二手） |

## 版本策略與 deprecation（C10-C17）

| 編號 | 案例                                                                                                  | 主議題                        | 類型   |
| ---- | ----------------------------------------------------------------------------------------------------- | ----------------------------- | ------ |
| C10  | [Stripe 日期滾動版本](/backend/11-api-design/cases/versioning-stripe-rolling-date-versions/)          | version change module、轉換層 | anchor |
| C11  | [Stripe 具名 major release](/backend/11-api-design/cases/versioning-stripe-named-major-releases/)     | 策略演進切片、相容變更清單    | anchor |
| C12  | [GitHub calendar versioning](/backend/11-api-design/cases/versioning-github-calendar-versioning/)     | header 選版、24 個月支援承諾  | anchor |
| C13  | [GitHub brownout](/backend/11-api-design/cases/versioning-github-password-auth-brownout/)             | deprecation 執行機制          | anchor |
| C14  | [Fielding no-versioning](/backend/11-api-design/cases/versioning-fielding-no-versioning/)             | 流派理論錨點                  | anchor |
| C15  | [RFC 8594 Sunset header](/backend/11-api-design/cases/versioning-sunset-header-rfc8594/)              | 退場宣告機器可讀層            | 邊緣   |
| C16  | [Slack 四族 API 收斂](/backend/11-api-design/cases/versioning-slack-conversations-api-sunset/)        | 分階段執行、in-band warning   | anchor |
| C17  | [Facebook Graph v1.0 退場](/backend/11-api-design/cases/versioning-facebook-graph-v1-forced-upgrade/) | 靜默語意切換                  | 反例   |

## GraphQL 進退（C18-C27）

| 編號 | 案例                                                                                            | 主議題                     | 類型         |
| ---- | ----------------------------------------------------------------------------------------------- | -------------------------- | ------------ |
| C18  | [GitHub 採用動機](/backend/11-api-design/cases/graphql-github-adoption/)                        | 可量化的 over-fetching 痛  | anchor       |
| C19  | [GitHub point system](/backend/11-api-design/cases/graphql-github-cost-rate-limiting/)          | 成本計點限流               | anchor       |
| C20  | [GitHub 雙軌穩態](/backend/11-api-design/cases/graphql-github-rest-parallel/)                   | 共存而非取代               | anchor       |
| C21  | [Shopify all-in](/backend/11-api-design/cases/graphql-shopify-all-in/)                          | 平台強制遷移               | anchor       |
| C22  | [Bessey 撤退清單](/backend/11-api-design/cases/graphql-bessey-retreat/)                         | 執行期與安全面代價         | 反例         |
| C23  | [Echobind 撤到 tRPC](/backend/11-api-design/cases/graphql-echobind-trpc-retreat/)               | 單團隊 schema 開銷、量化帳 | 反例（跨組） |
| C24  | [DataLoader 譜系](/backend/11-api-design/cases/graphql-dataloader-n-plus-one/)                  | N+1 變基礎設施             | anchor       |
| C25  | [HackerOne introspection](/backend/11-api-design/cases/graphql-introspection-auth-bypass/)      | 攻擊面偵察實證             | 邊緣         |
| C26  | [GraphQL versionless](/backend/11-api-design/cases/graphql-versionless-evolution/)              | no-versioning 的紀律轉嫁   | anchor       |
| C27  | [WunderGraph persisted ops](/backend/11-api-design/cases/graphql-wundergraph-not-for-internet/) | 第三條路、vendor 立場      | 邊緣偏反例   |

## gRPC 與 RPC 復興（C28-C34）

| 編號 | 案例                                                                                              | 主議題                    | 類型        |
| ---- | ------------------------------------------------------------------------------------------------- | ------------------------- | ----------- |
| C28  | [protobuf field number 紀律](/backend/11-api-design/cases/grpc-protobuf-field-number-discipline/) | 相容性是編碼格式性質      | anchor      |
| C29  | [Buf breaking detection](/backend/11-api-design/cases/grpc-buf-breaking-detection/)               | 四級規則、CI gate         | anchor      |
| C30  | [Buf Connect 批評](/backend/11-api-design/cases/grpc-buf-connect-critique/)                       | 部署邊界、trailers        | anchor      |
| C31  | [Dropbox Courier](/backend/11-api-design/cases/grpc-dropbox-courier/)                             | 百萬 RPS 遷移、框架層集中 | anchor      |
| C32  | [gRPC: The Bad Parts](/backend/11-api-design/cases/grpc-kmcd-bad-parts/)                          | debug 可及性判準          | 反例 / 邊緣 |
| C33  | [tRPC 設計哲學](/backend/11-api-design/cases/rpc-trpc-design-philosophy/)                         | 型別系統當契約、TS 鎖定   | anchor      |
| C34  | [JSON-RPC 重生（LSP / MCP）](/backend/11-api-design/cases/rpc-jsonrpc-lsp-mcp-revival/)           | 最小夠用訊息層            | anchor      |

## 介面語意：錯誤 / 分頁 / 冪等 / 限流 / 長時操作（C35-C45）

| 編號 | 案例                                                                                          | 主議題                         | 類型   |
| ---- | --------------------------------------------------------------------------------------------- | ------------------------------ | ------ |
| C35  | [RFC 9457 problem+json](/backend/11-api-design/cases/error-rfc9457-problem-details/)          | 錯誤格式標準、演化條款         | anchor |
| C36  | [Stripe 錯誤物件](/backend/11-api-design/cases/error-stripe-error-object/)                    | 三層正交欄位                   | anchor |
| C37  | [Slack cursor 遷移](/backend/11-api-design/cases/pagination-slack-cursor-migration/)          | opaque cursor、表示權在 server | anchor |
| C38  | [Stripe 冪等設計哲學](/backend/11-api-design/cases/idempotency-stripe-design-blog/)           | 三種失敗點、client 協作        | anchor |
| C39  | [Stripe 冪等契約條款](/backend/11-api-design/cases/idempotency-stripe-api-contract/)          | 24h、500 也重放                | anchor |
| C40  | [IETF Idempotency-Key draft](/backend/11-api-design/cases/idempotency-ietf-key-header-draft/) | 標準化停滯（expired）          | 邊緣   |
| C41  | [PayPal-Request-Id](/backend/11-api-design/cases/idempotency-paypal-request-id/)              | 同語意不同契約                 | 邊緣   |
| C42  | [IETF RateLimit headers](/backend/11-api-design/cases/ratelimit-ietf-header-fields/)          | 政策 / 狀態分離、informational | anchor |
| C43  | [GitHub 雙層限流](/backend/11-api-design/cases/ratelimit-github-primary-secondary/)           | primary / secondary、x- 前綴   | anchor |
| C44  | [Google AIP-151](/backend/11-api-design/cases/longrun-google-aip151/)                         | Operation resource             | anchor |
| C45  | [Twilio 計費事故](/backend/11-api-design/cases/idempotency-twilio-billing-postmortem/)        | 內部 retry 缺冪等閘門          | 反例   |

## 規範治理與標準化（C46-C54）

| 編號 | 案例                                                                                                    | 主議題                 | 類型   |
| ---- | ------------------------------------------------------------------------------------------------------- | ---------------------- | ------ |
| C46  | [Google AIP 治理](/backend/11-api-design/cases/governance-google-aip-model/)                            | 提案制、狀態機         | anchor |
| C47  | [Zalando API-first](/backend/11-api-design/cases/governance-zalando-api-first/)                         | Guild 制四件套         | anchor |
| C48  | [Microsoft 分軌治理](/backend/11-api-design/cases/governance-microsoft-rest-guidelines/)                | 規範沿組織邊界分化     | anchor |
| C49  | [Spectral 與 Zally](/backend/11-api-design/cases/governance-linting-spectral-zally/)                    | linting 進 CI          | anchor |
| C50  | [JSON:API](/backend/11-api-design/cases/standards-jsonapi-antibikeshedding/)                            | 停止 bikeshedding      | anchor |
| C51  | [OData 退場](/backend/11-api-design/cases/standards-odata-decline/)                                     | ISO 認證救不了生態     | 反例   |
| C52  | [OpenAPI Initiative](/backend/11-api-design/cases/standards-openapi-initiative-evolution/)              | vendor spec 轉軌基金會 | anchor |
| C53  | [AsyncAPI 補位](/backend/11-api-design/cases/standards-asyncapi-complement/)                            | 相容換採用             | anchor |
| C54  | [White House API Standards](/backend/11-api-design/cases/governance-whitehouse-api-standards-archived/) | 規範制定後棄置         | 反例   |

## Realtime：server 推 client 的對外承諾（C55-C63）

| 編號 | 案例                                                                                    | 主議題                           | 類型           |
| ---- | --------------------------------------------------------------------------------------- | -------------------------------- | -------------- |
| C55  | [WHATWG SSE spec](/backend/11-api-design/cases/sse-whatwg-spec-reconnection/)           | 內建重連、Last-Event-ID 補送     | anchor（spec） |
| C56  | [RFC 6455 WebSocket](/backend/11-api-design/cases/websocket-rfc6455-transport/)         | 雙向 transport、不內建保證       | anchor（spec） |
| C57  | [Slack Socket Mode](/backend/11-api-design/cases/websocket-slack-socket-mode/)          | WebSocket 上自建 ack / retry     | anchor         |
| C58  | [RFC 6202 long-polling](/backend/11-api-design/cases/longpolling-rfc6202-mechanics/)    | 機制代價、fallback 定位          | anchor（spec） |
| C59  | [Socket.IO negotiation](/backend/11-api-design/cases/longpolling-socketio-negotiation/) | transport fallback、相容性下限   | anchor         |
| C60  | [Stripe webhooks](/backend/11-api-design/cases/webhook-stripe-delivery-contract/)       | at-least-once、冪等、no-ordering | anchor         |
| C61  | [GitHub webhooks](/backend/11-api-design/cases/webhook-github-no-retry/)                | 不自動重試的反向承諾             | 反例（對照）   |
| C62  | [Slack Events API](/backend/11-api-design/cases/webhook-slack-events-retry/)            | 3 秒 ack、固定三次重試           | anchor         |
| C63  | [Shopify webhooks](/backend/11-api-design/cases/webhook-shopify-ordering-dedup/)        | ordering 不保證、去重 header     | anchor（佐證） |

## Status/Error 雙向契約（C64-C77）

| 編號 | 案例                                                                                           | 主議題                              | 類型           |
| ---- | ---------------------------------------------------------------------------------------------- | ----------------------------------- | -------------- |
| C64  | [RFC 4918 207 Multi-Status](/backend/11-api-design/cases/status-207-multistatus-rfc4918/)      | status line 降格為「請讀 body」     | anchor（spec） |
| C65  | [Google AIP 部分成功立場](/backend/11-api-design/cases/status-google-aip-partial-success/)     | 同步必原子、非同步 opt-in 部分成功  | anchor         |
| C66  | [RFC 9110 202 Accepted](/backend/11-api-design/cases/status-202-noncommittal-rfc9110/)         | intentionally noncommittal          | anchor（spec） |
| C67  | [RFC 9110 502/504](/backend/11-api-design/cases/status-502-504-gateway-ambiguity/)             | gateway 觀察 vs 上游執行狀態        | anchor（spec） |
| C68  | [Brooker backoff + jitter](/backend/11-api-design/cases/retry-brooker-backoff-jitter/)         | N²、三種 jitter 公式實測            | anchor         |
| C69  | [SRE Book cascading failures](/backend/11-api-design/cases/retry-sre-book-cascading-failures/) | retry 放大、budget、跨層疊乘        | anchor         |
| C70  | [AWS DynamoDB 2015 事故](/backend/11-api-design/cases/retry-dynamodb-2015-storm/)              | 內部 retry 風暴、55% 錯誤率         | 反例           |
| C71  | [Slack 2021-01-04 事故](/backend/11-api-design/cases/retry-slack-2021-recovery/)               | 復原期 retry + circuit breaking     | anchor（對照） |
| C72  | [AWS retry 指南](/backend/11-api-design/cases/retry-aws-guidance-budget/)                      | retry storm 官方定義、分層限制      | anchor         |
| C73  | [gRPC 兩層錯誤模型](/backend/11-api-design/cases/errorchain-grpc-two-layer-model/)             | 保證層 vs 選配層、中間節點盲區      | anchor         |
| C74  | [gRPC code 產生者歧義](/backend/11-api-design/cases/errorchain-grpc-code-producer-ambiguity/)  | 收到的 code 不一定來自 server       | anchor         |
| C75  | [AIP-193 錯誤內容規範](/backend/11-api-design/cases/errorchain-aip193-error-content/)          | 三層受眾、不假設內部實作            | anchor         |
| C76  | [W3C Trace Context](/backend/11-api-design/cases/trace-w3c-trace-context/)                     | 傳播義務、security boundary restart | anchor（spec） |
| C77  | [OWASP error handling](/backend/11-api-design/cases/errorchain-owasp-error-handling/)          | 錯誤訊息是偵察面、少暴露            | anchor（對照） |

## 案例覆蓋缺口（待補）

下列大綱範圍在本案例庫中公開案例偏弱或缺、撰寫正文時要明示「以下分析依官方文件 / standard / 通用模式推導、非 case-driven」、或先補採集：

- **11.1 API 作為服務邊界的責任、11.2 風格選型總覽**：沒有專屬 case、內容從全庫案例合成推導 — 寫作時依 fact vs derive 紀律標明「本章合成、非 case 原文」。
- **11.3 資源建模**：來源偏論證型（C1、C5）、缺企業資源建模實作的一手案例。
- **gRPC 退回 REST 的實名一手案例**：搜尋僅得 content-farm 來源、已拒收；styles/grpc/ 的「退場」敘事以 C32 的批評視角承擔、更硬的退回敘事標為缺口。
- **offset 分頁的獨立公開事故**：未找到可驗證一手事故文、失效模式由 C37 文內的一手描述承接。
- **企業內部治理失敗的公開檢討**：治理反例僅公部門（C54）、企業把治理失敗寫成 blog 的公開素材稀薄。
- **Twitter API v1.1 強制遷移（2012-2013）**：原始公告連結已死、只剩二手轉述、不收。

## 二手來源與狀態標注清單

- C9（twobithistory 史觀）、C17 的損壞影響描述（Amazon 轉述）、C51 的退場分析（Ben Morris）為二手來源、引用時標明性質。
- C40（Idempotency-Key draft）狀態 expired、C42（RateLimit headers draft）狀態 active v11 — 兩者引用都必須帶狀態、不可稱 RFC。
- C14（Fielding 訪談）刊載於 InfoQ、內容為本人一手陳述、引用標「InfoQ 訪談」。
- C27（WunderGraph）、C30（Buf）為利益相關 vendor 立場、批評點需與獨立來源（C22 / C25 / C32）互證後引用。
- Status/Error 雙向契約批（C64-C77）於 2026-07 採集。RFC 9110 引文因 WebFetch 視窗截斷、以 rfc-editor 官方 .txt 取回逐字核對（同源同權威）；C72 的 Builders' Library 為 JS 渲染無法逐字驗證、引文以 REL05-BP03 為錨、Builders' Library 內容標意譯；C67 的 retry 歧義判讀、C75 的跨服務轉譯責任為推導、正文引用須標明。C70 postmortem 未逐字出現「retry storm」、官方定義在 C72。
- Realtime 批（C55-C63）於 2026-07 採集、每個 source URL 經 WebFetch 實際取回驗證。C55 / C56 的 MDN 頁為開發者視角佐證、規範錨點以 WHATWG SSE spec（C55）與 RFC 6455（C56）為準；C57 / C59 / C60-C63 為 vendor 官方 docs、承諾為各 vendor 特定值、跨版本可能變、引用要帶 vendor 名。C58（RFC 6202）為 2011 Informational RFC、對照對象是 HTTP streaming 而非 WebSocket。
