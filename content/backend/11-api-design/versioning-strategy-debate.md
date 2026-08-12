---
title: "版本策略流派之爭：識別碼是入口、預設行為才是成本的分水嶺"
date: 2026-08-11
description: "選版本方案時各派的前提與代價：版本識別什麼、變更成本由誰吸收、借用某派結論而不帶其前提會壞在哪"
weight: 32
tags: ["backend", "api-design", "versioning"]
---

版本策略的流派分歧集中在一個問題上：`v2`、`2022-11-28`、`Stripe-Version` 這類識別碼指向什麼。指向資源身分、指向內容協商、指向消費者自己的屬性，各是一派；主張這個識別碼可以整個拿掉的 [no-versioning](/backend/knowledge-cards/no-versioning/) 派另成一派。

真正決定誰付遷移成本的，是**消費者不動作時被解讀成什麼** —— 沉默算「維持舊約」還是算「同意跟上」。識別碼形式是這個變數最常見的代理，因為它多半連帶決定了預設行為；兩者可以拆開，URI 版本配上服務端轉換層，成本結構就長得像 date pin，date pin 配上逐日期凍結部署，就長得像 URI 版本。讀者的入口是識別碼（那是他看得見的東西），要盯住的是預設行為。前三派分的是這筆成本的收款人與付款時點；第四派要先過一道前提閘門，閘門不通時它不在選項集裡，而非成本較高。

本文攤開各派的前提、成本結構與失效條件。少數幾個大客戶加一條長尾的混合形態（中型 SaaS 最常見的形狀）也適用，做法是兩邊分開處理：大客戶的遷移由合約與客戶成功團隊協調，版本機制服務的是那條聯絡不到也協調不動的長尾，而兩邊的支援窗口可以不同。單一消費者佔絕大多數流量、且握有合約級槓桿時例外——那種情境下遷移成本由談判決定，版本機制只是執行工具。版本方案選定之後怎麼落地、舊版怎麼退場，是另一個題目，收在 [版本策略與 deprecation](/backend/11-api-design/versioning-and-deprecation/)。

## 識別碼指向什麼

| 流派        | 識別碼形式                         | 版本指向           | 消費者跟上的動作         | 本文引用的一手案例              |
| ----------- | ---------------------------------- | ------------------ | ------------------------ | ------------------------------- |
| URI 版本    | `/v1/orders`                       | 資源身分           | 改呼叫路徑、整包遷移     | 業界廣泛存在、本文未引單一來源  |
| header 版本 | `X-GitHub-Api-Version: 2022-11-28` | 內容協商           | 改一個 header 值         | GitHub 2022 年公告              |
| 日期 pin    | 帳號 pin 首次呼叫日、header 可覆寫 | 消費者的屬性       | 維持現狀即維持舊語意     | Stripe 工程部落格與文件         |
| 不做版本    | 無識別碼                           | 執行期習得的控制項 | 依 server 當下的控制項走 | Fielding 訪談、GraphQL 官方文件 |

識別碼指向什麼，決定了「誰在什麼時點被迫動作」。版本進資源身分時，切版是消費者的一次性工程：路徑變了、SDK 換了、整組端點一起翻新，而服務端在遷移完成前得長期並行兩套實作。版本進內容協商時，同一個資源身分下可以並存多個語意切片，粒度細到單一 breaking change，消費者的切換成本降到改一個 header 值 —— GitHub 2022 年為 REST API 引入 calendar versioning 時選的正是這條（見 [11.C12](/backend/11-api-design/cases/versioning-github-calendar-versioning/)）。

版本指向消費者屬性時，動作的預設值反了過來。Stripe 讓帳號在首次呼叫時自動 pin 住當時版本，消費者維持現狀就繼續拿到熟悉的語意，升級是主動選擇而非被動應付（見 [11.C10](/backend/11-api-design/cases/versioning-stripe-rolling-date-versions/)）。這個反轉是 date-based pin 的核心價值：消費者的沉默被解讀成「維持舊約」，而在 URI 版本下，消費者的沉默會在舊版下線那天變成故障。

表中四派是最常見的四種形態，另有兩種真實存在的變體值得知道。**media type 版本**（`Accept: application/vnd.example+json;version=2`）走的是 HTTP 標準的內容協商，因此有正規的 `Vary` 快取語意；表中的 header 版本用的是自訂 header，CDN 對它預設是盲的 —— 兩者常被歸成一類，而在快取層的行為並不同。**query parameter 版本**（`?api-version=2023-01-01`）把識別碼放進 URI 卻能逐 endpoint 版本化，它直接說明了「版本進 URI 就等於整包遷移」並非必然。

不做版本時，消費者每次呼叫都在跟當下的 server 對話，穩定性由服務端的自我約束提供。REST 這個架構風格的提出者 Roy Fielding 把這件事推到最遠：對 `/v1/` 式介面版本化的建議是「DON'T」，版本化逼 client 要嘛跟著重佈署、要嘛讓舊版成為「permanent lead weight」，而「Versioning interface names only manages change for the API owner's sake」（InfoQ 訪談、2014，見 [11.C14](/backend/11-api-design/cases/versioning-fielding-no-versioning/)）。

## 成本的收款人換了、總額還在

URI 版本把帳單開給消費者與服務端的維運面：消費者付一次性的大遷移，服務端付雙版本並行期間的重複維護與行為漂移風險。這筆錢的好處是不需要事前投資 —— 第一版上線時只要在路徑裡放一個 `v1`，成本要到第一次 breaking change 才發生。

它換到的三件事在設計層看不見、在營運層很硬。**版本邊界就是部署邊界**：`/v1` 可以凍結、獨立部署、獨立擴縮、獨立 rollback，舊版是一份不再變動的程式碼；轉換層路線的舊版則是活的，每次部署都可能動到轉換鏈裡的任何一環，而爆炸半徑是全體 pin 住舊版的帳號。**URI 就是 cache key**：邊緣快取天然按版本分流，不需要 `Vary`；自訂 header 版本要 CDN 支援對該 header 做 `Vary`，而綁帳號的 date pin 基本上放棄邊緣快取。**分版的可觀測性是免費的**：path prefix 讓 per-version 的 metrics、log 與配額直接成立，header 版本要另外埋，而漏埋是靜默的。三項合起來，URI 版本在「大量匿名讀取、CDN 前置」的平台上未必是次優解。

日期 pin 把帳單開給服務端的基礎設施投資。Stripe 內部用 version change module 封裝每個 breaking change，response 依時間反向流過模組鏈、轉換成該帳號 pin 住版本的形狀；截至 2017 年累積約 100 個 backwards-incompatible 升級，仍維持與 2011 年以來每一版相容（C10）。這是把相容性從路由層搬進轉換層的做法，案例本身的判讀說得很直接：版本策略是基礎設施投資，而非命名慣例。代價相應清楚 —— 每個 breaking change 都要寫出一個可執行的轉換模組，轉換鏈的長度隨時間單調成長，且測試矩陣跟著長。

header 版本介於兩者之間：服務端仍要為每個宣告過的版本維持行為，但版本切片是顯式的、有限的，而非像日期 pin 那樣連續。GitHub 選這條的同時給了承諾結構 —— 新版釋出後舊版至少支援 24 個月，公告明講理由是「不能也不期待 integrator 隨我們調整 API 而不斷更新整合」（C12）。

不做版本的帳單開給紀律。GraphQL 官方教學把 versionless 講成 common practice，明文的機制是兩件事：新能力透過新 type 或既有 type 的新 field 加入、type system 中每個 field 預設 nullable（見 [11.C26](/backend/11-api-design/cases/graphql-versionless-evolution/)）。案例判讀把它歸納成三個紀律：只加不改、舊欄位以 deprecation 標注而非移除、欄位保持 nullable 預設；並把成本結構點明——版本管理的工作換了位置，沒有消失。nullable-by-default 尤其值得單獨理解 —— 它讓後端局部故障與細粒度授權拒絕落在單一欄位上，而非炸掉整個 response，代價是每個消費者都得在每個欄位上處理空值。

## 不做版本的成立前提是消費者能在執行期習得控制項

Fielding 立場的力道來自它的完整形式：hypermedia as the engine of application state 是 REST 的約束而非選配，控制項應在執行期動態習得（C14）。這句話的操作意義是——client 當下能做哪些操作，由伺服器在回應裡附的連結告訴它，而不是寫死在 client 的程式碼裡。在這個前提下，服務端改變可用操作時，client 讀到的是新的控制項集合，行為跟著變 —— 版本號確實多餘。

前提在多數 JSON-over-HTTP API 並不成立，這正是實務路線與學院立場分歧的根源（C14 判讀）。硬編碼路徑與欄位名的 client 拿不到「執行期習得」這個能力，服務端一改就斷。判斷自家 client 落在哪一邊有個直接的問法：把某個端點的 URL 換掉、只在既有回應裡加一個指向新位置的控制項，現有 client 會跟著走嗎。

GraphQL 的 versionless 是這個方向的工程化實例，且把前提換成了較弱的版本：client 不需要動態習得控制項，只需要顯式宣告自己要哪些欄位，服務端據此判斷加欄位是否安全。代價是 versionless 依賴的那三個紀律，而紀律的執行落在組織而非機制上。GraphQL 工具商 WunderGraph 的批評正指這一點 —— versioning 的組織問題 GraphQL 沒解（見 [11.C27](/backend/11-api-design/cases/graphql-wundergraph-not-for-internet/)；該公司販售的正是 GraphQL 的替代方案、立場需納入判斷，此處引用的是其論證而非量化事實）。schema 保持相容，跟「還在用三年前那批欄位的內部團隊什麼時候能被停止支援」是兩個問題，後者不隨 versionless 消失。

## 支援窗口是各派共同要回答的那一題

各派決定的是「版本這件事長什麼樣」，而消費者實際感受到的是另一件事：舊語意什麼時候真的停止供應。這一題各派都躲不掉，且答案的明文程度比流派選擇更能預測退場當天的災情。

GitHub 的 24 個月是把它寫成契約的形態（C12，限 REST API、GraphQL 與 webhooks 除外）：支援窗口從隱性期待變成 SLA 式明文，消費者可以據此排遷移計畫。Facebook Graph API v1.0 的退場是同一題答錯的形態 —— 給了一年遷移期，到期後未遷移的請求被靜默改以 v2.0 語意處理，而 v2.0 移除了 friends 資料等大範圍權限（見 [11.C17](/backend/11-api-design/cases/versioning-facebook-graph-v1-forced-upgrade/)，反例；損壞影響的描述來自二手轉述）。靜默切換的危險在於 client 拿到的是形狀不同的資料而非明確錯誤，故障因此發生在業務邏輯深處、而非認證層。

不做版本的一派同樣要回答這題，而它在兩個支派下的形式不同（以下為機制推導，未見公開規範明文處理）。GraphQL 這一支的形式是 deprecation 標注掛了多久才真的移除：標注本身不帶時限，時限由各服務自己承諾 —— 這正是 WunderGraph 說的組織問題落地的位置。純 hypermedia 那一支連標注都沒有，問題移到控制項與表徵上：某個 link relation 停止出現之後，還在依賴它的 client 有多久的適應期、media type 的相容承諾維持到哪一版。兩支都要給答案，只是答案掛在不同的表面上。

## 借用結論而不帶前提

各派的結論都可以在網路上單獨讀到，而失效多半發生在結論被搬走、前提留在原地時。

**採 date pin 而沒有轉換層投資**。日期版本的吸引力在消費者體驗，而支撐它的是服務端的 version change module 鏈。只做 pin 而沒有轉換層時，服務端實際上是在為每個 pin 住的日期維護一份獨立行為，測試矩陣的成長速度跟 URI 版本相同、可見性卻更差。檢查問法：新增一個 breaking change 時，寫的是一個可執行的轉換模組，還是在既有程式碼裡多加一個日期分支。

**採 no-versioning 而 client 是硬編碼的**。Fielding 的 DON'T 帶著 hypermedia 前提，拆開之後剩下的是「不提供版本識別、也不承諾相容」。這個組合下服務端每次變更都在賭沒有 client 依賴到被動的部分，而賭輸的證據要等消費者回報才出現。檢查問法是前述的控制項測試：換掉某個端點的 URL、只在既有回應裡留下指向新位置的控制項，現有 client 跟得上嗎。

**採 versionless 而缺 add-only 紀律與量測**。GraphQL 的三個紀律裡，只加不改跟 deprecation 標注靠 review 執行，而「舊欄位還有誰在用」靠量測回答。缺了量測時 deprecation 標注會無限期累積，schema 變成一份沒有人敢動的欄位墓園 —— 表面上沒有版本，實際上每個舊欄位都是一個永久支援的版本。檢查問法：任選一個標了 deprecated 的欄位，能不能在五分鐘內說出上週有幾個消費者呼叫它。

## 判定序的順序不能顛倒

選型是一道有方向的判定序，因為前面的問題會把後面的選項整組排除。每一問都要指定答案的產物形態——一個數字、一項程式碼事實、或一份既存文件；答案不是判斷本身，這樣走完之後才有東西可以複驗與重跑（這條原則的完整說明見 [11.1 的產物形態段](/backend/11-api-design/api-boundary-responsibility/)）。

**第一問：消費者改得動嗎、多快改得動**。這是四派分野最粗的一刀，而它常被跳過，因為多數討論預設消費者是外部的。三格：

- **可原子更新**（消費者全在同一個 repo 或同一個發布單位、能一次改完；四種消費者形態的分野見 [API Consumer Shape](/backend/knowledge-cards/api-consumer-shape/)）。版本識別碼在這裡是純成本 —— 不做版本，改用相容性檢查擋在 CI 上，破壞相容的變更在合併前就被攔下。內部服務多半落在這格，而它常被誤判成「消費者少所以選 URI 版本」。產物是一份消費者清單加各自的發布方式。
- **可協調**（消費者在組織外，而通知發得出去、也等得到他們改）。四派都在選項集裡，往下走。
- **改不動**（不可更新韌體的裝置、已停止維護的整合、經轉售通路而聯絡不到終端）。任何遷移計畫的完成率都會停在某個數字以下，因此舊語意的預設是永久供應。這一格讓 URI 版本的凍結部署最划算 —— 凍結一份不再變動的程式碼，比讓它活在轉換鏈裡便宜得多。判定序在這裡結束。

**第二問：不做版本的前提成不成立**。三種前提任一成立即可，而它們要求的東西不同：client 能在執行期習得控制項（hypermedia）、client 顯式宣告要哪些欄位（GraphQL 式）、或變更純粹是加法且由服務端吸收（ingest 型 API 的 tolerant reader 加 add-only，寬容度由服務端單方面提供、消費者不必有任何能力）。

前提成立之後還有一道進場條件，而它是既存事實而非自評：**現在說不說得出上週有幾個消費者呼叫某個 deprecated 欄位**。說不出來時 no-versioning 的三份紀律沒有執行依據，等同前提不成立，往下走（這層能力的建法見 [11.12 API 消費者用量觀測](/backend/11-api-design/consumer-usage-observability/)）。

**第三問：消費者的集中度**。數量之外要看分佈，而「協調得動」這件事本身有四項查得到的成立條件（見 [Consumer Coordinability](/backend/knowledge-cards/consumer-coordinability/)）。單一客戶佔九成流量時，協調得動的是那九成，永遠協調不動的是那條長尾，而退場當天的事故全發生在長尾上。判準因此不是「多少個」而是「協調不動的那部分佔多少」，產物是近三十天流量的 per-consumer 佔比排序與前十名之外的尾部合計。尾部佔比高時，大客戶走合約協調、長尾走版本機制，而兩邊的支援窗口可以不同——長尾那半實質上是第一問的第三格。

**第四問：組織能不能負擔並持續維護一層轉換**。能，date-based pin 最省消費者的力，消費者的沉默被解讀成維持舊約；不能，落點是 header 版本 —— 它讓版本切片顯式且有限、切換成本仍只是改一個 header 值，而服務端付的是為每個宣告過的版本維持行為，不必寫出時間軸上的轉換鏈。

三問的輸入都是決策當下的性質，而它們會過期。「消費者少而可協調」在十年後多半已經不成立——團隊換過幾輪、當初的整合被 vendor 進別人的 library、組織拆過部門。因此走完判定序要留下一份紀錄：四問的答案、日期、當時的消費者數與尾部佔比。沒有這份紀錄，「重跑」沒有可比對的基準，觸發條件命中了也不知道什麼變了。

重評的觸發掛在既有節奏上比掛在事件偵測上可靠，因為那四類事件（消費者數量跳一個量級、出現能單獨否決時程的合約級客戶、開始經由轉售或嵌入通路散佈、發現有消費者聯絡不上）沒有人負責偵測，而最後一類只會在退場當天現形——正是 tripwire 想避開的時點。務實的掛法是季度 review 與「每次接入新的大型整合方」這兩個既有時機，重讀那份紀錄，問四個答案有沒有變。

走完三問拿到的是機制，不是全部。四派在支援窗口那一題上重新匯合——消費者感受得到的始終是「舊語意什麼時候停止供應」，而這一題的答案由誰來寫、寫在哪裡，各派都得自己交代。選完機制之後真正要動筆的是那份承諾。

## 下一步路由

- 版本方案的落地與 deprecation 執行工具箱：[11.5 版本策略與 deprecation](/backend/11-api-design/versioning-and-deprecation/)
- 什麼算 breaking change、變更怎麼審：[11.6 向後相容的變更紀律](/backend/11-api-design/backward-compatibility-discipline/)
- 承諾成本結構的上游框架：[11.1 API 作為服務邊界的責任](/backend/11-api-design/api-boundary-responsibility/)
- versionless 的紀律代價與 schema 演進實作：[Schema 演進](/backend/11-api-design/styles/graphql/graphql-schema-evolution/)
- hypermedia 前提的完整展開：[Hypermedia 適用邊界](/backend/11-api-design/styles/rest/hypermedia-hateoas-revival/)
- 支援窗口承諾怎麼送到消費者手上：[11.14 契約條款的送達](/backend/11-api-design/contract-clause-delivery/)
- 已在某一派、要換到另一派的路徑：[11.13 既有 API 的改造路徑](/backend/11-api-design/existing-api-retrofit/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
