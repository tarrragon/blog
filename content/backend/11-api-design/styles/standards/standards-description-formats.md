---
title: "描述格式的選型：OpenAPI 與 AsyncAPI"
date: 2026-07-03
description: "描述 API 形狀的格式標準怎麼選：看既有採用動能、看涵蓋的介面種類、以及 REST 加 event 混合時的治理配置"
weight: 2
tags: ["backend", "api-design", "standards"]
---

描述格式標準（OpenAPI、AsyncAPI）描述的是 API 本身的形狀 —— 有哪些 endpoint、吃什麼參數、回什麼結構 —— 給文件生成、client codegen（產生呼叫端程式碼）、mock、契約測試這些工具消費。它跟 [response 格式標準](/backend/11-api-design/styles/standards/standards-adopt-or-build/)（回應長什麼樣）不同層：response 格式管「回應長什麼樣」、描述格式管「怎麼把 API 的形狀寫成一份機器可讀的檔」。選這一層的標準、判準是兩件事：它有沒有既有的採用動能、以及它涵不涵蓋你這種介面。

## 描述格式標準靠既有動能、不靠背書

OpenAPI 成為 API 描述的事實標準、走的是一條跟 OData 相反的路。它源自 SmartBear 捐出的 Swagger Specification、轉進 Linux Foundation 下的 OpenAPI Initiative、以開放治理與 vendor neutrality 運作（見 [11.C52](/backend/11-api-design/cases/standards-openapi-initiative-evolution/)）。關鍵差異在轉移的時機：捐出來時 Swagger 已經是事實標準、治理轉移是把一份已有動能的規格中立化、而不是靠標準機構的背書從零創造動能。

這正是[採現成標準篇](/backend/11-api-design/styles/standards/standards-adopt-or-build/)裡 OData（拿了 ISO 認證卻退場的那個案例）的反向情形。選一個描述格式標準時、要問的是它是不是已經被廣泛採用、還是靠機構背書硬推 —— 前者的認證是市場給的、後者的認證是委員會給的、兩者對存活的預測力差很多。OpenAPI 站穩後把描述範圍延伸到周邊問題（Arazzo 描述多 API workflow、Overlay 讓描述自動更新）—— 一個標準組織站穩後往鄰接問題延伸、是可觀察的生命週期訊號。

## REST 加 event 混合時的補位

當系統同時有 REST API 跟 event、描述格式的選型多一個維度：涵蓋範圍。OpenAPI 描述的是 request/response 式的介面、描述不了 event-driven 的 publish/subscribe。AsyncAPI 來補這個空白、而且它補的方式本身是個值得學的策略：不另起爐灶、刻意維持跟 OpenAPI 相容、重用 OpenAPI 的 schema、只把結構換成 event 的語彙（Paths 換成 Channels、HTTP verbs 換成 Publish/Subscribe）（見 [11.C53](/backend/11-api-design/cases/standards-asyncapi-complement/)）。它明講的論證是系統很少只有 REST 或只有 event、多半兩者都有 —— 以相容性換採用曲線、站在既有標準的肩上而不是跟它競爭。

使用層的判讀：描述格式的邊界就是治理的邊界。組織同時有 REST 加 event 時、規範治理需要兩份 spec 格式（OpenAPI 描述同步介面、AsyncAPI 描述事件）、但共用一套 schema 來源 —— schema 是 source of truth、兩份描述格式是它在同步與非同步兩側的投影。event 側的能力與交接落在 [03 訊息佇列](/backend/03-message-queue/)。

## 選描述格式的兩個問題

選描述格式標準收斂成兩問。這個標準是不是已經是事實標準、有沒有工具生態實際在用它 —— 在 REST／HTTP request-response 這個 paradigm 內、OpenAPI 的動能沒有對手、選它不太需要猶豫。（GraphQL 與 gRPC 各自帶原生的形狀描述 —— GraphQL 的 SDL 加 introspection、gRPC 的 protobuf 加 server reflection —— 這不是 OpenAPI 的缺位、是不同 paradigm 各有自己的事實標準。）你的介面涵蓋哪些種類 —— 只有 REST、OpenAPI 一份就夠；有 event、加 AsyncAPI 補位、但守住「一套 schema 源、兩份格式投影」、別讓兩份描述各自長出不一致的真相。

描述格式選型幾乎不會落到「自建」這一格 —— 描述格式的價值全在生態工具、自建一份沒有工具吃的描述格式等於白做。（平台級玩家是例外：AWS 的 Smithy、Google 的 Discovery Document 都自建 IDL、把多語言 SDK 的 codegen 收進自己的 source、再往下游投影成 OpenAPI —— 自建不划算的判準只對沒有自有工具鏈的一般團隊成立。）這跟採現成標準篇裡「response 格式自建仍是合理選項」的判斷剛好相反、差別在於 response 格式的消費者是你自己的 client（自建規範自己遵守就成立）、描述格式的消費者是一整片第三方工具鏈（脫離事實標準就沒工具可用）。

## 下一步路由

- 採標準 vs 自建的治理層判準：[11.10 API 規範治理](/backend/11-api-design/api-governance/)
- response 格式的採用選擇：[採現成標準還是自建規範](/backend/11-api-design/styles/standards/standards-adopt-or-build/)
- event 側的能力與交接：[03 訊息佇列](/backend/03-message-queue/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
