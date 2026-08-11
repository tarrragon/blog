---
title: "錯誤格式之爭：錯誤是 HTTP 的一等公民還是應用層酬載"
date: 2026-08-11
description: "選錯誤格式時各派的分歧與代價：錯誤內容跟 transport status 是什麼關係、哪些角色因此讀得到錯誤、演化條款由誰提供"
weight: 31
tags: ["backend", "api-design", "error-model"]
---

錯誤格式的流派分歧看起來像欄位命名之爭，實際爭的是錯誤資訊跟 transport status 的關係：錯誤是 HTTP status 的補充說明、是跟成功回應共用同一個外殼的一個欄位、是跟 transport 徹底解耦的協定內建結構、還是拆成整條鏈都讀得到的保證層與只有端到端讀得到的選配層。這些關係決定了同一個錯誤有多少角色讀得到 —— 消費者的分支邏輯、中介層的 retry 與快取、監控的錯誤率圖表、SDK 的例外轉換，各自能讀到的層次不同。錯誤的分類判準與格式欄位設計主寫在 [11.4 錯誤模型設計](/backend/11-api-design/error-model-design/)，本文掛在該章之下，攤開該章保留的解耦議題。

## 錯誤跟 transport status 的關係分歧

| 流派     | 錯誤內容的位置                    | 跟 status 的關係      | 一手錨點                     |
| -------- | --------------------------------- | --------------------- | ---------------------------- |
| 補充派   | 獨立 media type 的 body           | 補充、status 維持真實 | RFC 9457（C35）              |
| 統一外殼 | 成功與失敗共用的 envelope 欄位    | 並存、status 常被弱化 | 業界廣泛存在（無專屬 case）  |
| 解耦派   | 協定回應結構內建的 errors 集合    | 解耦、status 表達傳輸 | GraphQL 官方設計（C26 脈絡） |
| 分層派   | 保證層加選配層、選配層走 metadata | 分層、status 為保證層 | gRPC 官方 error guide（C73） |

補充派的立場在 RFC 9457 裡是明文的：problem details 補充 HTTP status code、而非取代（見 [11.C35](/backend/11-api-design/cases/error-rfc9457-problem-details/)）。這句話決定了整份格式的定位 —— 讀 status 的角色拿到粗分類、讀 body 的角色拿到細節，兩層對同一個錯誤說一致的話。

統一外殼派把成功與失敗塞進同一個形狀，常見形態是 `{ "success": ..., "data": ..., "error": ... }`。這一派沒有權威 spec 可以引，屬於各團隊各自演化出來的慣例，因此本文對它的分析從結構性質推導、而非從一手來源引述。動機通常是 client 端的解析路徑單一：SDK 只要解一種形狀，成功與失敗走同一個 unwrap。

解耦派把錯誤從 transport 層完全移出。GraphQL 的回應結構內建 errors 集合（這一點出自 GraphQL spec 本身、非本站案例庫涵蓋），transport 只表達「這個請求有沒有送達並被處理」。這個設計跟它的 nullable-by-default 是一體的：type system 中每個 field 預設 nullable，理由包含後端局部故障與細粒度授權（見 [11.C26](/backend/11-api-design/cases/graphql-versionless-evolution/)），局部失敗因此落在單一欄位而非整包回應，而說明失敗原因的位置就是 errors 集合（schema 側的完整展開見 [Schema 演進](/backend/11-api-design/styles/graphql/graphql-schema-evolution/)）。

分層派是同一張力在別的 transport 上的解。gRPC 的標準模型是失敗回一個 error status code 加 optional string message，richer error model 讓 server 回傳結構化細節、實作上走 trailing metadata（見 [11.C73](/backend/11-api-design/cases/errorchain-grpc-two-layer-model/)）。官方自列的風險裡有一條直接命中本文主題：proxies 與 loggers 看不到 trailing metadata 裡的 error detail。

## 解耦換到的是局部失敗的表達力

解耦派的收益具體而非抽象。單一 request 觸發多個 resolver、其中一個因授權或後端故障失敗時，補充派要在「整包失敗」與「假裝成功」之間二選一，而解耦派可以回傳部分資料加上對應的錯誤條目 —— 消費者拿到的是「這幾格有值、那一格為什麼沒有」。

同樣的收益在批次操作上也成立，那條路線在本站另有專篇：一個 status 放不下多個獨立結果時，下放 body 與收窄語意是方向相反的兩條路（見 [Status 裝不下的東西](/backend/11-api-design/status-expressiveness-boundary/)）。錯誤格式之爭與那篇的分工是：那篇問 status 這一格裝不裝得下事實，本文問錯誤內容該住在哪個容器裡。兩者在「中介層讀不讀得到」這個後果上匯流。

## 解耦付出的是錯誤的讀者集合

錯誤資訊離開 transport 層之後，讀得懂它的角色從「整條鏈」收縮成「懂這個 schema 的 client」。以下三類是最常被忽略的收縮對象，每一類都對應一項實際失去的能力；名單並不封閉，gateway 的計費與 SLO 計數、判 200 為通過的 synthetic check 與契約測試、provider 自己以 5xx 為條件的 log 告警規則都在同一份帳上（本段的收縮後果從機制推導、非引自案例）。

中介層的自動行為建立在 status 上。retry 中介層看到 200 就當成功、快取層看到 200 就存起來、負載平衡器看到 200 就認定後端健康。錯誤住在 200 的 body 裡時，這三個行為全部依據錯誤的回應做出，而它們沒有任何機制發現這件事。

監控的錯誤率圖表同理。錯誤率是最常被拿來下決策的一個指標 —— 發不發告警、要不要 rollback、事故分級多高 —— 而它多半以 status 為輸入。解耦之後這條指標要重建在應用層埋點上，重建的成本是一次性的，忘記重建的代價則是事故當天圖表全綠。

SDK 與泛型 client 的例外轉換也依賴 status。HTTP client 函式庫普遍提供「4xx/5xx 拋例外」的開關，解耦之後這個開關失效，每個消費者都得自己寫檢查 errors 集合的程式碼，而漏寫的形態是靜默忽略。

gRPC 的分層設計正是為了在拿到表達力的同時保住一部分讀者：status code 是所有語言 client 都拿得到的最低契約，richer detail 是選配、中間節點對它是盲的（C73 判讀）。這條分界線可以直接搬到 HTTP 上使用 —— 決定哪些資訊必須讓整條鏈看見、哪些可以只給端到端。

統一外殼派的代價跟解耦派同構，而它的動機並不包含局部失敗的表達力。它換到的是 client 端的單一解析路徑，而那份收益用真實 status 也拿得到 —— 付一樣的帳、換到的收益既少一項又可以不付帳取得，這是統一外殼在四派裡最脆弱的位置。這一派的常見自救正是「envelope 照包、status 照回真實值」，此時它退化成補充派的一個變體，代價也隨之消失。

## 演化條款與命名空間是格式的隱藏成本

四派共同要回答的還有一題：格式本身怎麼演進。RFC 9457 的 spec 條款加上案例判讀對它的定位，給了一份現成答案 —— `type` 用 URI 而非字串 enum，把錯誤種類的命名空間外部化避免跨團隊撞名；「client MUST ignore unknown extensions」是向前相容的演化條款；IANA common problem types registry 補上 RFC 7807 的生態碎片化（C35）。

選了另外三派時，這兩件事變成自建責任。命名空間缺席的形態是跨服務的錯誤碼撞號，演化條款缺席的形態是每次新增欄位都無法確認既有消費者安不安全。判準已在 11.4 給出：既有 API 有自訂格式且被大量依賴時，把這兩個設計補進自訂格式，比換格式務實。

## 借用結論而不帶前提

**採解耦而沒有重建錯誤率指標**。GraphQL 的表達力收益在文章與會議簡報裡很好講，而它預設消費者與營運端都會補上應用層的錯誤觀測。檢查問法：現在讓 resolver 對所有請求回錯誤，值班的人幾分鐘內會不會收到告警。

**採統一外殼而把 status 一律回 200**。統一外殼的動機是 client 解析路徑單一，而真實 status 一樣給得起這份收益。檢查問法：把 status 改回真實值之後，client 的解析程式碼要改幾行；答案落在數行以內時，付出整條鏈的可讀性換這幾行並不划算，答案遠大於此時要查的是 client 為什麼把解析邏輯綁死在單一形狀上。

**採 RFC 9457 而只抄五個欄位**。9457 的價值有很大一部分在兩個設計條款上，而它們不在欄位清單裡。檢查問法：現在往錯誤回應加一個新的 extension member，文件裡有沒有一句話讓既有消費者知道自己該忽略它。

**在保證層與選配層之間沒有明確分界**。gRPC 的兩層是刻意設計，而在 HTTP 上把細節塞進自訂 header 或非標準位置多半是隨手決定。檢查問法：目前錯誤回應裡的每個欄位，說得出它預期被誰讀嗎；說不出來的欄位要往三個方向之一收 —— 整條鏈都要看的升格進 status 或標準 body、只有端到端要看的明文標成選配層、沒有人要看的移除。

選型的第一問要把兩種收益分開，因為它們常被混談：需不需要**部分成功**（同一次請求裡有些結果成功、有些失敗，各自要說明），跟需不需要**結構化的錯誤細節**（失敗就是失敗，但要帶得動機器可判讀的原因與欄位定位）。分層派給的是後者 —— gRPC 的 richer error model 讓一個失敗的 call 帶著結構化細節回來，它並不讓一個 call 部分成功。第二問是營運端有沒有能力把錯誤觀測重建在應用層，第三問是格式的演化條款與命名空間打算自建還是沿用現成。

三問的落點因此是：要部分成功、且營運端補得起應用層觀測，走解耦；只要結構化細節、不要部分成功，走分層派，整條鏈的 status 保持真實而細節放選配層；兩種都不特別需要，補充派讓整條鏈維持一致，而它同時是演化條款與命名空間最現成的一派 —— 這是預設值，選離它要說得出理由。

## 下一步路由

- 錯誤分類與格式欄位的設計判準：[11.4 錯誤模型設計](/backend/11-api-design/error-model-design/)
- status 這一格裝不下事實時的兩條路線：[Status 裝不下的東西](/backend/11-api-design/status-expressiveness-boundary/)
- 錯誤在多層服務間傳播時的保證層與選配層、以及 provider 該暴露多少細節的安全邊界：[錯誤傳播與信任邊界](/backend/11-api-design/error-propagation-trust-boundary/) 的「暴露多少」段
- 消費者拿到錯誤後的回報與升級判讀：[錯誤回報的回饋迴路](/backend/11-api-design/error-feedback-loop/)
- GraphQL 解耦設計的 schema 側代價：[Schema 演進](/backend/11-api-design/styles/graphql/graphql-schema-evolution/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
