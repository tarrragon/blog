---
title: "版本策略流派之爭：識別碼指向什麼決定誰付遷移成本"
date: 2026-08-11
description: "選版本方案時各派的前提與代價：版本識別什麼、變更成本由誰吸收、借用某派結論而不帶其前提會壞在哪"
weight: 32
tags: ["backend", "api-design", "versioning"]
---

版本策略的流派分歧集中在一個問題上：`v2`、`2022-11-28`、`Stripe-Version` 這類識別碼指向什麼。指向資源身分、指向內容協商、指向消費者自己的屬性，各是一派；主張這個識別碼可以整個拿掉的 no-versioning 派另成一派。前三派分的是成本 —— 介面要演進、消費者要穩定、這筆帳總要有人付，三派選了不同的收款人與不同的付款時點；第四派則要先過一道前提閘門，閘門不通時它不在選項集裡，而非成本較高。本文攤開各派的前提、成本結構與失效條件。版本方案選定之後怎麼落地、舊版怎麼退場，是另一個題目，收在 [版本策略與 deprecation](/backend/11-api-design/versioning-and-deprecation/)。

## 識別碼指向什麼

| 流派        | 識別碼形式                         | 版本指向           | 消費者跟上的動作         | 一手來源                        |
| ----------- | ---------------------------------- | ------------------ | ------------------------ | ------------------------------- |
| URI 版本    | `/v1/orders`                       | 資源身分           | 改呼叫路徑、整包遷移     | 業界廣泛存在、無單一權威來源    |
| header 版本 | `X-GitHub-Api-Version: 2022-11-28` | 內容協商           | 改一個 header 值         | GitHub 2022 年公告              |
| 日期 pin    | 帳號 pin 首次呼叫日、header 可覆寫 | 消費者的屬性       | 維持現狀即維持舊語意     | Stripe 工程部落格與文件         |
| 不做版本    | 無識別碼                           | 執行期習得的控制項 | 依 server 當下的控制項走 | Fielding 訪談、GraphQL 官方文件 |

識別碼指向什麼，決定了「誰在什麼時點被迫動作」。版本進資源身分時，切版是消費者的一次性工程：路徑變了、SDK 換了、整組端點一起翻新，而服務端在遷移完成前得長期並行兩套實作。版本進內容協商時，同一個資源身分下可以並存多個語意切片，粒度細到單一 breaking change，消費者的切換成本降到改一個 header 值 —— GitHub 2022 年為 REST API 引入 calendar versioning 時選的正是這條（見 [11.C12](/backend/11-api-design/cases/versioning-github-calendar-versioning/)）。

版本指向消費者屬性時，動作的預設值反了過來。Stripe 讓帳號在首次呼叫時自動 pin 住當時版本，消費者維持現狀就繼續拿到熟悉的語意，升級是主動選擇而非被動應付（見 [11.C10](/backend/11-api-design/cases/versioning-stripe-rolling-date-versions/)）。這個反轉是 date-based pin 的核心價值：消費者的沉默被解讀成「維持舊約」，而在 URI 版本下，消費者的沉默會在舊版下線那天變成故障。

不做版本時，消費者每次呼叫都在跟當下的 server 對話，穩定性由服務端的自我約束提供。REST 這個架構風格的提出者 Roy Fielding 把這件事推到最遠：對 `/v1/` 式介面版本化的建議是「DON'T」，版本化逼 client 要嘛跟著重佈署、要嘛讓舊版成為「permanent lead weight」，而「Versioning interface names only manages change for the API owner's sake」（InfoQ 訪談、2014，見 [11.C14](/backend/11-api-design/cases/versioning-fielding-no-versioning/)）。

## 成本的收款人換了、總額還在

URI 版本把帳單開給消費者與服務端的維運面：消費者付一次性的大遷移，服務端付雙版本並行期間的重複維護與行為漂移風險。這筆錢的好處是不需要事前投資 —— 第一版上線時只要在路徑裡放一個 `v1`，成本要到第一次 breaking change 才發生。

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

三問構成一道有方向的判定序，順序不能顛倒——第一問決定後面三派要不要進場。

**第一問：client 能不能在執行期習得控制項**（或退一步，能不能顯式宣告自己要哪些欄位、讓服務端判斷加東西安不安全）。答否時 no-versioning 出局，往下走；答是時它是最省的一條，代價轉成只加不改、deprecation 標注與舊欄位用量量測這三份日常工作，而組織執行不了這三份紀律時，答是也要往下走。

**第二問：消費者有多少、多異質、能不能協調**。少而可協調時 URI 版本的簡單性划算 —— 遷移是一次性的協調工作，不需要事前投資轉換層。多而異質時遷移協調做不動，往下走。

**第三問：組織能不能負擔並持續維護一層轉換**。能，date-based pin 最省消費者的力，消費者的沉默被解讀成維持舊約；不能，落點是 header 版本 —— 它讓版本切片顯式且有限、切換成本仍只是改一個 header 值，而服務端付的是為每個宣告過的版本維持行為，不必寫出時間軸上的轉換鏈。

走完三問拿到的是機制，不是全部。四派在支援窗口那一題上重新匯合——消費者感受得到的始終是「舊語意什麼時候停止供應」，而這一題的答案由誰來寫、寫在哪裡，各派都得自己交代。選完機制之後真正要動筆的是那份承諾。

## 下一步路由

- 版本方案的落地與 deprecation 執行工具箱：[11.5 版本策略與 deprecation](/backend/11-api-design/versioning-and-deprecation/)
- 什麼算 breaking change、變更怎麼審：[11.6 向後相容的變更紀律](/backend/11-api-design/backward-compatibility-discipline/)
- 承諾成本結構的上游框架：[11.1 API 作為服務邊界的責任](/backend/11-api-design/api-boundary-responsibility/)
- versionless 的紀律代價與 schema 演進實作：[Schema 演進](/backend/11-api-design/styles/graphql/graphql-schema-evolution/)
- hypermedia 前提的完整展開：[Hypermedia 適用邊界](/backend/11-api-design/styles/rest/hypermedia-hateoas-revival/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
