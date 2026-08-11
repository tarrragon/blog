---
title: "錯誤格式之爭：status 的真實性決定誰讀得到錯誤、容器決定誰讀得到細節"
date: 2026-08-11
description: "選錯誤格式時各派的分歧與代價：錯誤內容跟 transport status 的關係、它讓哪些角色讀得到錯誤、以及演化條款與命名空間由誰提供"
weight: 31
tags: ["backend", "api-design", "error-model"]
---

錯誤格式的流派分歧看起來像欄位命名之爭，實際爭的是兩個獨立的決定。第一個是 **transport status 還說不說真話** —— 失敗時回不回真實的 4xx/5xx，這決定了「這裡出了錯」這件事有多少角色看得見：中介層的 retry 與快取、監控的錯誤率圖表、SDK 的例外轉換，全都只讀這一格。第二個是**錯誤細節住在哪個容器** —— 獨立 media type 的 body、跟成功回應共用的外殼、協定內建的 errors 集合、還是走 metadata 的選配層；這決定了「錯在哪、為什麼」有多少角色解得開。兩個決定常被綁在一起討論，而它們可以分開選：有真實 status 的 envelope 是完整選項，不是妥協。

本文處理這兩個決定與各派的取捨。錯誤該分幾類、格式欄位怎麼設計，見 [錯誤模型設計](/backend/11-api-design/error-model-design/)。

## 錯誤跟 transport status 的關係分歧

| 流派           | 錯誤細節的容器                    | status 還說不說真話   | 一手來源               |
| -------------- | --------------------------------- | --------------------- | ---------------------- |
| 補充派         | 獨立 media type 的 body           | 說                    | RFC 9457               |
| 外殼加真實狀態 | 成功與失敗共用的 envelope 欄位    | 說                    | 各團隊慣例、無單一規範 |
| 協定層外殼     | 協定自己定義的 result / error     | 不說、恆定為傳輸結果  | JSON-RPC 2.0           |
| 解耦派         | 協定回應結構內建的 errors 集合    | 不說、恆定為傳輸結果  | GraphQL 規範與官方教學 |
| 分層派         | 保證層加選配層、選配層走 metadata | 說（保證層即 status） | gRPC 官方 error guide  |

補充派的立場在 RFC 9457 裡是明文的：這份標準定義 `application/problem+json`，核心成員是 `type`（錯誤種類的 URI）、`title`、`status`、`detail`、`instance` 五個，而 problem details 的定位是補充 HTTP status code、而非取代（見 [11.C35](/backend/11-api-design/cases/error-rfc9457-problem-details/)）。這句話決定了整份格式的定位 —— 讀 status 的角色拿到粗分類、讀 body 的角色拿到細節，兩層對同一個錯誤說一致的話。

外殼派把成功與失敗塞進同一個形狀，常見形態是 `{ "success": ..., "data": ..., "error": ... }`。這一派要分兩種來看，而把它們混為一談是這場爭論裡最常見的誤讀。

**外殼加真實狀態**：包了外殼、status 照回 4xx/5xx。它的動機不只是 client 解析路徑單一，還有三項在真實平台上更硬的理由。其一是跨 transport 可移植：同一份酬載要走 HTTP、WebSocket、SSE、訊息佇列或批次檔案時，status code 在後四者根本不存在，而外殼是唯一活得下來的形狀。其二是強型別 SDK 的 codegen：一個泛型 `ApiResponse<T>` 的生成規則，比把 N 個 status 映射到 N 個例外型別便宜得多。其三是混合閘道：對外要把 REST、GraphQL、gRPC 三種錯誤模型收斂成一種時，外殼是那個收斂點。這一派沒有單一規範可引，屬於各團隊各自演化的慣例，因此本文對它的分析從結構性質推導。

**協定層外殼**：JSON-RPC 2.0 把外殼寫進規範 —— 回應是 `result` 或 `error` 二選一，error 物件有 `code`、`message` 與供應用自訂的 `data`，且 code 保留了一段給協定自己的錯誤。它 over HTTP 時慣例上一律回 200，status 因此恆定為「這個訊息送到了」。這一派證明外殼形態拿得到命名空間與演化位置 —— 那兩件事並非只有 RFC 9457 給得起（JSON-RPC 的選型條件見 [JSON-RPC 的適用條件](/backend/11-api-design/styles/rpc-revival/rpc-revival-jsonrpc-conditions/)）。

解耦派把錯誤從 transport 層完全移出。GraphQL 的回應結構內建 errors 集合（這一點出自 GraphQL 規範本身），transport 只表達「這個請求有沒有送達並被處理」。這個設計跟它的 nullable-by-default 是一體的：type system 中每個 field 預設 nullable，理由包含後端局部故障與細粒度授權（見 [11.C26](/backend/11-api-design/cases/graphql-versionless-evolution/)），局部失敗因此落在單一欄位而非整包回應，而說明失敗原因的位置就是 errors 集合（schema 側的完整展開見 [Schema 演進](/backend/11-api-design/styles/graphql/graphql-schema-evolution/)）。

分層派是同一張力在別的 transport 上的解。gRPC 的標準模型是失敗回一個 error status code 加一段選配的文字訊息；它另有一套 richer error model，讓 server 回傳結構化的錯誤細節，實作上把這些細節放在 trailing metadata —— 回應結尾附帶的一組鍵值對，中間節點不解析它（見 [11.C73](/backend/11-api-design/cases/errorchain-grpc-two-layer-model/)）。官方自列的風險裡有一條直接命中本文主題：proxies 與 loggers 看不到 trailing metadata 裡的錯誤細節。

## 解耦換到的是局部失敗的表達力

解耦派的收益具體而非抽象。單一 request 觸發多個 resolver、其中一個因授權或後端故障失敗時，補充派要在「整包失敗」與「假裝成功」之間二選一，而解耦派可以回傳部分資料加上對應的錯誤條目 —— 消費者拿到的是「這幾格有值、那一格為什麼沒有」。

同樣的收益在批次操作上也成立，而那是相鄰的另一個題目：一個 status 放不下多個獨立結果時，下放 body 與收窄語意是方向相反的兩條路（見 [Status 裝不下的東西](/backend/11-api-design/status-expressiveness-boundary/)）。那一題問的是 status 這一格裝不裝得下事實，本文問的是錯誤內容該住在哪個容器裡；兩者在「中介層讀不讀得到」這個後果上匯流。

## 中介層、監控與 SDK 從此讀不到錯誤

status 停止說真話之後，讀得懂「這裡出了錯」的角色從「整條鏈」收縮成「懂這個 schema 的 client」。這一節的代價以一個前提為條件：鏈上真的有讀 status 的中介層、以及以 status 為輸入的觀測。單一 first-party client、無 gateway、無 status 告警的內部服務，下面這幾筆帳大半不會發生 —— 判斷這一節適不適用自己，先數一下這條鏈上有幾個角色在讀 status。以下三類是最常被忽略的收縮對象，每一類都對應一項實際失去的能力；名單並不封閉，gateway 的計費與 SLO 計數、判 200 為通過的 synthetic check 與契約測試、provider 自己以 5xx 為條件的 log 告警規則都在同一份帳上（本段的收縮後果為機制推導，未見公開規範明文處理）。

中介層的自動行為建立在 status 上。retry 中介層看到 200 就當成功、快取層看到 200 就存起來、負載平衡器看到 200 就認定後端健康。錯誤住在 200 的 body 裡時，這三個行為全部依據錯誤的回應做出，而它們沒有任何機制發現這件事。

監控的錯誤率圖表同理。錯誤率是最常被拿來下決策的一個指標 —— 發不發告警、要不要 rollback、事故分級多高 —— 而它多半以 status 為輸入。解耦之後這條指標要重建在應用層埋點上，重建的成本是一次性的，忘記重建的代價則是事故當天圖表全綠。

SDK 與泛型 client 的例外轉換也依賴 status。HTTP client 函式庫普遍提供「4xx/5xx 拋例外」的開關，解耦之後這個開關失效，每個消費者都得自己寫檢查 errors 集合的程式碼，而漏寫的形態是靜默忽略。

gRPC 的分層設計正是為了在拿到表達力的同時保住一部分讀者：status code 是所有語言 client 都拿得到的最低契約，richer detail 是選配、中間節點對它是盲的。這條分界線可以直接搬到 HTTP 上使用 —— 決定哪些資訊必須讓整條鏈看見、哪些可以只給端到端。

這一整節的帳單只寄給讓 status 停止說真話的那幾派。外殼加真實狀態不在收件人之列 —— 它拿到跨 transport 可移植、codegen 便宜、閘道可收斂這三項，而 status 照回真實值，上面三類讀者一個都沒少。真正付這筆帳的是外殼配恆定 200 的做法，它跟協定層外殼與解耦派同構，差別在後兩者用它換到了明確的東西（協定可移植、局部失敗表達力），而恆定 200 的自訂外殼多半換不到 —— 它付這筆帳通常是因為第一版隨手決定了，而不是因為需要。

## 演化條款與命名空間是格式的隱藏成本

四派共同要回答的還有一題：格式本身怎麼演進。RFC 9457 的 spec 條款加上案例判讀對它的定位，給了一份現成答案 —— `type` 用 URI 而非字串 enum，把錯誤種類的命名空間外部化避免跨團隊撞名；「client MUST ignore unknown extensions」是向前相容的演化條款；IANA 建立了一份公用 problem type 的登記表，補上前一版標準（RFC 7807）留下的生態碎片化。

選了另外三派時，這兩件事變成自建責任。命名空間缺席的形態是跨服務的錯誤碼撞號，演化條款缺席的形態是每次新增欄位都無法確認既有消費者安不安全。判準是既有 API 有自訂格式且被大量依賴時，把這兩個設計補進自訂格式，比換格式務實。

## 借用結論而不帶前提

**解耦了，卻沒重建錯誤率指標**。GraphQL 的表達力收益在文章與會議簡報裡很好講，而它預設消費者與營運端都會補上應用層的錯誤觀測。檢查問法：現在讓 resolver 對所有請求回錯誤，值班的人幾分鐘內會不會收到告警。

**包了外殼，順手把 status 一律回 200**。外殼的三項真實收益（跨 transport、codegen、閘道收斂）沒有一項需要 status 說謊。檢查問法：把 status 改回真實值之後，哪些東西會壞。第一方 client 的答案通常是幾行 unwrap；generated client 要看的是型別生成規則這個單位，問的是 codegen 模板改不改得動；而外部消費者的程式碼看不到時，這個問題答不出來 —— 答不出來本身就是訊號，代表恆定 200 已經被外部依賴，此時的路徑是新版端點回真實 status、舊端點維持現狀。

**把 9457 當欄位清單抄**。這份標準的價值有很大一部分在兩個設計條款上，而它們不在欄位清單裡。檢查問法：現在往錯誤回應加一個新的 extension member，文件裡有沒有一句話讓既有消費者知道自己該忽略它。

**在保證層與選配層之間沒有明確分界**。gRPC 的兩層是刻意設計，而在 HTTP 上把細節塞進自訂 header 或非標準位置多半是隨手決定。檢查問法：目前錯誤回應裡的每個欄位，說得出它預期被誰讀嗎；說不出來的欄位要往三個方向之一收 —— 整條鏈都要看的升格進 status 或標準 body、只有端到端要看的明文標成選配層、沒有人要看的移除。

選型的第一問要把兩種收益分開，因為它們常被混談：需不需要**部分成功**（同一次請求裡有些結果成功、有些失敗，各自要說明），跟需不需要**結構化的錯誤細節**（失敗就是失敗，但要帶得動機器可判讀的原因與欄位定位）。分層派給的是後者 —— gRPC 的 richer error model 讓一個失敗的 call 帶著結構化細節回來，它並不讓一個 call 部分成功。第一問還有一個常被跳過的前置分支：部分成功的需求若只出現在批次端點上，補充派配 per-item 結果陣列就做得到，整體錯誤模型不必動（該路線的 status 側取捨見 [Status 裝不下的東西](/backend/11-api-design/status-expressiveness-boundary/)）。

第二問是營運端有沒有能力把錯誤觀測重建在應用層，第三問是格式的演化條款與命名空間打算自建還是沿用現成。

要部分成功、且營運端補得起應用層觀測，走解耦。只要結構化細節、不要部分成功，走分層派：整條鏈的 status 保持真實，細節放選配層。酬載要跨多種 transport、或要餵 codegen、或閘道要收斂多種錯誤模型，走外殼加真實狀態 —— 這三個約束是架構級的，不是偏好。兩種收益都不特別需要，補充派讓整條鏈維持一致，而它同時是演化條款與命名空間最現成的一派。

有一類情境會壓過上面全部：中介層本身是稽核證據來源時，選配層不能承載需要留證的內容。分層派「proxies 與 loggers 看不到 trailing metadata」在一般平台是取捨，在受稽核的鏈上是失格條件 —— 錯誤內容要可重現、可歸檔，就得住在整條鏈都讀得到的地方。

## 下一步路由

- 錯誤分類與格式欄位的設計判準：[11.4 錯誤模型設計](/backend/11-api-design/error-model-design/)
- status 這一格裝不下事實時的兩條路線：[Status 裝不下的東西](/backend/11-api-design/status-expressiveness-boundary/)
- 錯誤在多層服務間傳播時的保證層與選配層、以及 provider 該暴露多少細節的安全邊界：[錯誤傳播與信任邊界](/backend/11-api-design/error-propagation-trust-boundary/) 的「暴露多少」段
- 消費者拿到錯誤後的回報與升級判讀：[錯誤回報的回饋迴路](/backend/11-api-design/error-feedback-loop/)
- GraphQL 解耦設計的 schema 側代價：[Schema 演進](/backend/11-api-design/styles/graphql/graphql-schema-evolution/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
