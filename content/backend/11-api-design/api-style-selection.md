---
title: "11.2 風格選型總覽"
date: 2026-07-03
description: "REST 式 HTTP+JSON、GraphQL、gRPC、tRPC、JSON-RPC、event 之間選哪個 — 用消費者形狀、演進成本、操作可及性三軸判讀"
weight: 2
tags: ["backend", "api-design", "selection"]
---

風格選型的判準是介面的使用情境、而非風格本身的技術優劣。同一個團隊裡可能同時存在三個正確答案：對外公開 API 用 HTTP+JSON、內部服務間用 gRPC、前後端同倉的產品用 tRPC — 三個介面的消費者形狀不同、答案就不同。本章建立三條判準軸；各風格內部的深度論證（流派自己怎麼說、失敗案例、適用邊界）收在 `styles/` 流派層、本章結尾的爭論地圖列出路由。本章的判準軸是從 [案例庫](/backend/11-api-design/cases/) 跨案例合成的、標明為推導。

## 判準軸一：消費者形狀

消費者形狀指誰在呼叫、服務端對呼叫方有多少控制力、呼叫方跟服務端的部署與語言關係。這條軸是三條裡權重最高的、因為它決定其他軸的成本怎麼放大。

流派自己劃出的邊界最有說服力。tRPC 官方 FAQ 明言前提：脫離 monorepo 就失去 client 與 server 一起運作的保證、替代方案是把 backend 型別發成 private npm package — 語言鎖定 TypeScript、部署形態鎖定同倉或私包（見 [11.C33](/backend/11-api-design/cases/rpc-trpc-design-philosophy/)）。公開撤退立場的六年 GraphQL 實踐者也給出同構的判準句、並建議控制得了 client 的團隊改用 OpenAPI REST（見 [11.C22](/backend/11-api-design/cases/graphql-bessey-retreat/)、反例、作者判讀層）。兩個相反方向的來源指向同一條判讀：**選型的第一步是確認消費者是誰、再比對風格能力**。

消費者形狀的常見分型與傾向：

| 消費者形狀                   | 傾向風格             | 原因                                                           |
| ---------------------------- | -------------------- | -------------------------------------------------------------- |
| 匿名第三方開發者（公開平台） | HTTP+JSON（REST 式） | 工具鏈普及、curl 可及、文件生態成熟                            |
| 內部服務、跨語言、多團隊     | gRPC / protobuf      | schema-first 跨語言、契約可 CI 檢查                            |
| 前後端同倉、全 TypeScript    | tRPC                 | 型別即契約、零 codegen；前提與代價見上                         |
| 多形狀 client 拼裝巢狀資料   | GraphQL              | client 聲明取數；執行成本與安全代價見爭論地圖                  |
| 本地 process 間、雙向、低頻  | JSON-RPC             | 最小夠用訊息層；LSP 與 MCP 的採用是實證（見下）                |
| 下游要事件不是查詢           | event / queue        | 交接語意不同、路由到 [03 訊息佇列](/backend/03-message-queue/) |

表格是索引、每列的成立條件在真實情境裡要重新判讀。以 JSON-RPC 列為例：它在 web API 世代被 REST 式做法取代、卻在 LSP 與 MCP 兩份現代 spec 裡被選為訊息層 — 兩份 spec 都在 JSON-RPC 2.0 上加約束、而非發明新協議（見 [11.C34](/backend/11-api-design/cases/rpc-jsonrpc-lsp-mcp-revival/)；spec 只陳述採用、選型理由是本模組的判讀）。共同的條件組合是本地、雙向、需要 notification 語意、生態工具要求零 codegen 可自省 — 這組條件下 gRPC 的 HTTP/2 與 codegen 成本全是負資產。判讀重點是條件組合、而非「JSON-RPC 回來了」這種風格敘事。其餘各列的成立條件同樣散在後文 — gRPC 與 tRPC 的前提在判準軸二、三展開、GraphQL 的代價在爭論地圖路由的流派層、表格只負責索引。

## 判準軸二：演進成本

每種風格都要回答「介面上線後怎麼改」、機制差異很大。兩個代表性答案：GraphQL 的 versionless 路線把演進成本轉嫁到 schema 層的紀律、protobuf 把相容性直接做成編碼格式的性質 — 兩者的具體紀律與條款、主寫在 [11.6 變更紀律](/backend/11-api-design/backward-compatibility-discipline/) 的格式層段（案例 [11.C26](/backend/11-api-design/cases/graphql-versionless-evolution/)、[11.C28](/backend/11-api-design/cases/grpc-protobuf-field-number-discipline/)）。HTTP+JSON 的演進紀律則多半靠約定與流程、缺格式層的強制 — 這是它自由度最高也最容易踩線的原因。

選型時的判讀問題是團隊承擔得起哪種紀律：格式層強制（protobuf）適合跨團隊多語言、因為紀律不依賴人的自覺；約定層紀律（JSON、GraphQL SDL）需要配套的變更審查與工具、組織面見 [11.10 規範治理](/backend/11-api-design/api-governance/)。

## 判準軸三：操作與 debug 可及性

介面會被 on-call 的人徒手戳、會過 LB 與 proxy、會被防火牆規則篩 — 這些操作面的成本在能力比較表上通常缺席。gRPC 在這條軸上的代價有完整的一手批評：協議要求端到端 HTTP/2 加 trailers、瀏覽器支援需要翻譯 proxy、debug 時 `curl | jq` 不可行（見 [11.C30](/backend/11-api-design/cases/grpc-buf-connect-critique/)、發布方是競品 vendor、批評點與 [11.C32](/backend/11-api-design/cases/grpc-kmcd-bad-parts/) 的獨立實踐者批評互證後採用）。C32 提出的「傳一個 cURL 範例給朋友」測試是這條軸的可操作判準。

這條軸的權重跟組織的 infra 成熟度成反比：有能力在框架層集中處理 proxy、觀測、部署的組織（如 Dropbox 的 Courier、見 [11.C31](/backend/11-api-design/cases/grpc-dropbox-courier/)）、操作成本被平台吸收；小團隊每個介面都要自己扛操作面、可及性差的風格會在 on-call 時收利息。

## 共存是常態、取代是例外

大平台的長期實證支持「多風格共存」而非「新風格取代舊風格」。GitHub 2016 年採用 GraphQL、多年後的官方立場是 REST 與 GraphQL 並行、依情境選用、且明文說明功能覆蓋不對等（見 [11.C20](/backend/11-api-design/cases/graphql-github-rest-parallel/)）。反方向的 Shopify 宣告 GraphQL 為唯一 API — 但它動用了「新功能只上 GraphQL、新 app 強制」的平台強制力、還配套 rate limit 加倍與查詢成本降 75%（見 [11.C21](/backend/11-api-design/cases/graphql-shopify-all-in/)）。判讀：沒有平台強制力的組織、務實的預期是多風格長期共存、選型的真正產出是「每個介面用對風格」、而非全公司統一答案。

## 爭論地圖

本章只給判準軸；各風格的深度交鋒在 `styles/` 流派層：REST 語意學之爭與 hypermedia 復興（[已完成](/backend/11-api-design/styles/rest/)）、GraphQL 的執行成本與進退（styles/graphql、backlog）、proto 演進紀律與部署邊界（styles/grpc、backlog）、tRPC 與 JSON-RPC 的復興條件（styles/rpc-revival、backlog）、格式標準化的反覆嘗試（styles/standards、backlog）、server 推 client 的承諾差異（styles/realtime、案例待採集）。完整 backlog 見 [模組頁](/backend/11-api-design/) 章節規劃。

## 下一步路由

- 承諾成本結構的框架：[11.1 API 作為服務邊界的責任](/backend/11-api-design/api-boundary-responsibility/)
- 選了風格之後的資源建模：[11.3 資源建模與操作語意](/backend/11-api-design/resource-modeling-operation-semantics/)
- 事件式交接的能力邊界：[03 訊息佇列](/backend/03-message-queue/)、[Webhook 知識卡](/backend/knowledge-cards/webhook/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
