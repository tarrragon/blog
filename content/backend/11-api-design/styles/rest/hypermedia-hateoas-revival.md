---
title: "Hypermedia 與 HATEOAS 復興"
date: 2026-07-03
description: "復興派的論證本體：uniform client 前提、語意漂移史、格式標準化的失敗現實、反方的收益假設拆解 — 與 hypermedia 的適用邊界"
weight: 2
tags: ["backend", "api-design", "rest", "hypermedia"]
---

Hypermedia 復興派的核心主張是一個工程論點、而非對原義的懷舊：**application state 的可用轉移由 server 編碼在回應裡、client 不持有業務知識 — 這個性質只在存在 uniform client 時兌現、而瀏覽器就是那個 uniform client**。本文攤開這條論證的完整結構、格式標準化的失敗現實、以及反方的逐條拆解。HATEOAS 有無的操作型判別法（available actions 由誰計算）與最小範例、主寫在 [11.3 的建模層](/backend/11-api-design/resource-modeling-operation-semantics/) — 本文的 lens 是流派論證本體、兩處分工不同。

## 語意漂移史：復興派的問題意識

復興派的論證起點是一段歷史重建（見 [11.C4](/backend/11-api-design/cases/rest-gross-opposite-of-rest/)）：XML-RPC 與 SOAP 世代之後、JSON 取代 XML 成為 API 的通用格式 — 但 JSON 是純資料格式、不是 hypertext、hypermedia controls 沒有了自然的載體；Richardson 成熟度模型普及、業界集體停在 Level 2；SPA 興起讓前端與 REST 原則脫鉤；GraphQL 最後乾脆放棄 REST 名義。重建的結論：今日的 JSON API 是掛著 REST 名字的 RPC、真正 hypermedia-driven 的回應形式是 HTML。

這段敘事裡有一個兩派共享的觀察、也是整場爭論的樞紐：**REST 的 self-describing 特性是為 uniform client（瀏覽器）設計的、machine-to-machine 的 JSON 生態並不存在這種 client**。復興派從這個觀察推出「所以回到 HTML、讓瀏覽器當 uniform client」；pragmatic 派從同一個觀察推出「所以 machine-to-machine 場景放棄 hypermedia」— 同一個前提、兩個方向的合理結論、分歧點在 consumer 是誰。

## 復興論證的正面版本

htmx 一系的 essays 把復興論證落到具體工程性質（範例層見 [11.C5](/backend/11-api-design/cases/rest-htmx-hateoas-html-necessity/) 與 11.3 的展開）：業務狀態直接編碼在可用操作裡、client 端零業務邏輯 — 狀態機改版時只有 server 要改、部署即生效、沒有 client 端的版本滯後問題。從這個角度、hypermedia 是 [版本策略](/backend/11-api-design/versioning-and-deprecation/) 的另一種解法：Fielding 的 no-versioning 立場（[11.C14](/backend/11-api-design/cases/versioning-fielding-no-versioning/)）在 hypermedia 前提下是自洽的 — 控制項在執行期習得、演化不需要版本號。

論證同時對 GraphQL 保留了讓步：thick-client 場景（client 本來就要持有大量邏輯）用 GraphQL 是合理選擇 — 復興派的攻擊對象是「掛 REST 名的 JSON RPC」、而非所有非 hypermedia 的設計。

## 格式標準化的現實：JSON 上補 hypermedia 的失敗

復興論證有一個要正面回答的歷史事實：在 JSON 上疊 hypermedia controls 的嘗試、生態上失敗了。HAL 用 `_links` 與 `_embedded` 兩個保留屬性做最小侵入的 hypermedia 化、有 spec、有生態（曾是 Spring HATEOAS 預設格式）、標準化止步於過期的 IETF draft（見 [11.C6](/backend/11-api-design/cases/rest-kelly-hal-spec/)）。Siren 走表達力路線、first-class 的 `actions` 帶 method 與欄位、比 HAL 更接近 HTML form 的 JSON 化 — 採用反而更少、release 停在 2017（見 [11.C7](/backend/11-api-design/cases/rest-swiber-siren-adoption/)）。

兩案並排的判讀：表達力不是 hypermedia 格式勝出的變數、client 生態才是 — HAL、Siren、JSON-LD、Collection+JSON 並立無一勝出、uniform client 沒有形成、每個消費者仍要為每個 API 寫專屬邏輯、hypermedia 的收益前提落空。這個碎片化現實同時支撐兩派：復興派引它證明「JSON 不是 natural hypermedia、所以回到 HTML」；pragmatic 派引它證明「別等標準收斂、直接放棄 controls」。

## 反方的收益假設拆解

Pragmatic 派的拆解值得完整轉述、因為它針對的是收益假設而非名詞（見 [11.C8](/backend/11-api-design/cases/rest-morris-pragmatic-no-hateoas/)、對照組）：解耦（decoupling）— client 開發者讀文件、hardcode endpoint、不跟連結走、server 換 URI 結構照樣壞；可發現性（discoverability）— 機器消費者沒有「瀏覽」行為、發現靠文件跟 SDK；可演化性（evolvability）— hypermedia 只解決「下一步網址」的演化、欄位語意的演化照樣要文件與版本管理。三條拆解共享同一個前提：消費者是程式、不是人 — 把這個前提換掉（消費者是瀏覽器後面的人）、三條拆解全部失效、這正是 htmx 一系在 web UI 場景成立的原因。

## 適用邊界

把兩派論證疊起來、hypermedia 的適用邊界可以畫得相當清楚。收益前提成立的場景：consumer 是瀏覽器（或任何會 render hypermedia 的 uniform client）、UI 由 server 驅動、業務狀態機常變 — server-rendered web 應用、後台管理介面、htmx 式的漸進增強前端。收益前提不成立的場景：machine-to-machine 整合、第三方開發者寫程式消費、mobile app 內建業務邏輯 — 這些場景的務實選擇是「狀態欄位 + 明文狀態機」路線（判準見 [11.3](/backend/11-api-design/resource-modeling-operation-semantics/)）。誤區是把邊界問題當立場問題：同一個組織可以對外 API 走 pragmatic、後台 UI 走 hypermedia、兩者引用的是同一組論證的不同半邊。

## 下一步路由

- 這個詞的定義權爭奪全景：[REST 語意學之爭](/backend/11-api-design/styles/rest/rest-semantics-dispute/)
- 判別法與建模層判準：[11.3 資源建模與操作語意](/backend/11-api-design/resource-modeling-operation-semantics/)
- no-versioning 立場的版本策略語境：[11.5 版本策略與 deprecation](/backend/11-api-design/versioning-and-deprecation/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
