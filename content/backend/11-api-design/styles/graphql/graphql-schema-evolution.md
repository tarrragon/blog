---
title: "GraphQL Schema 演進：versionless 的紀律代價"
date: 2026-07-03
description: "只加不改、deprecation 標注、nullable 預設三個紀律怎麼共同取代版本號 — 以及每個紀律各自的隱藏帳單"
weight: 1
tags: ["backend", "api-design", "graphql"]
---

GraphQL 的 schema 演進機制建立在一條因果鏈上：client 只拿到明確請求的欄位、所以新增 type 與 field 對既有 query 不可見、所以加法演進永遠安全、所以版本號可以不存在。[11.C26](/backend/11-api-design/cases/graphql-versionless-evolution/) 收錄的官方立場把「永遠避免 breaking change、提供 versionless API」稱為 common practice。本文追這條因果鏈的三個支撐紀律、以及各自的隱藏帳單。跨風格的變更紀律框架（格式層 / 工具層 / 流程層）主寫在 [11.6](/backend/11-api-design/backward-compatibility-discipline/)、本文的 lens 是 GraphQL 內部機制的深化。

## 紀律一：只加不改

加法安全的機制基礎是 client 的顯式選取：REST 回應裡新增欄位、所有消費者都會收到（多數忽略、少數壞掉）；GraphQL 新增欄位、沒請求它的 query 完全不受影響。這讓「加」在 GraphQL 是真正的零風險操作 — 但「改」與「刪」的風險跟任何風格相同、versionless 的意思是把這兩類操作用紀律排除、而非讓它們變安全。

隱藏帳單是 schema 只增不減的膨脹：欄位一旦發布、有沒有人用、用的人肯不肯走、都要靠量測回答。GraphQL 在這點上有結構優勢 — client 逐欄位聲明取數、server 端可以精確統計每個欄位的使用量與呼叫方、比 REST 的「整包回應、不知道誰讀了哪個欄位」可觀測得多。這個優勢要主動兌現：欄位使用量進 metrics 是 versionless 能長期運作的基礎設施前提、對應 [11.5](/backend/11-api-design/versioning-and-deprecation/) 退場量測段的同一條原則。

## 紀律二：deprecation 標注

`@deprecated` directive 把退場資訊放進 schema 本身：欄位標注後、introspection 與工具鏈（IDE 自動完成、linter）會對新的使用者顯示警告、既有 query 照常運作。這是 [deprecation 執行工具箱](/backend/11-api-design/versioning-and-deprecation/) 裡 in-band warning 的 schema 層版本 — 訊號出現在開發者寫 query 的當下、時點比 response warning 更早。

隱藏帳單是「標注不等於退場」：`@deprecated` 沒有強制力、沒有日期語意、long tail 消費者可以永遠不動。實務上的補法是把欄位使用量量測跟 deprecation 標注綁在一起 — 標注後看用量衰減曲線、歸零才真正刪除；用量不動、回到 11.5 的遷移壓力工具。

## 紀律三：nullable 預設

GraphQL type system 把每個欄位預設為 nullable、官方理由包含後端局部故障與細粒度授權（C26 觀察層）：某個 resolver 失敗或某個欄位被權限拒絕時、該欄位回 null、response 的其餘部分照常返回 — 局部失敗不炸掉整個回應。這個設計跟演進的關係在第三層：nullable 欄位的移除路徑比 non-null 平緩（消費者本來就要處理 null、欄位「永遠 null」是移除前的可用中繼態）。

隱藏帳單是 null 語意的多義：欄位是 null、消費者無法區分「值就是空」「resolver 失敗」「權限拒絕」三種情況 — 錯誤資訊要靠 response 的 `errors` 陣列補充、而這正是 GraphQL 把 transport status 與業務錯誤解耦的設計（錯誤格式的跨風格交鋒、掛在 [11.4](/backend/11-api-design/error-model-design/) 的爭論文章 backlog）。schema 設計的實務判準：業務上不可能缺席的欄位（id、type）明文標 non-null、其餘保留 nullable 預設 — 全部標 non-null 換到的型別安全、會在第一次局部故障時以整包 response 失敗的形式付還。

## versionless 是承諾結構、不是免維護

三個紀律合起來看、versionless 的實質是把版本管理的工作換了位置：版本號消失、換來的是欄位級的使用量量測、deprecation 生命週期管理、null 語意設計三項常態工作。跟 [11.5](/backend/11-api-design/versioning-and-deprecation/) 的日期版本方案相比、差異在粒度 — 日期版本以「版本」為單位管理遷移、GraphQL 以「欄位」為單位；粒度變細讓大翻版消失、也讓管理點的數量成長一個量級。組織層的判讀：schema 治理（誰能加欄位、誰審 deprecation、linting 進 CI）承擔的角色跟 [11.10](/backend/11-api-design/api-governance/) 的 guidelines 治理同構、schema registry 類工具是這一層的基礎設施。

no-versioning 立場的跨流派交鋒（Fielding 的 hypermedia 路線、Stripe 的 date-based 路線、GraphQL 的欄位粒度路線）、收在掛 11.5 的版本策略爭論文章 backlog（見 [模組頁](/backend/11-api-design/)）。

## 下一步路由

- 跨風格的變更紀律框架：[11.6 向後相容的變更紀律](/backend/11-api-design/backward-compatibility-discipline/)
- 執行層的代價：[執行成本與攻擊面](/backend/11-api-design/styles/graphql/graphql-execution-cost-security/)
- 組織層的進退：[公開 API 的 GraphQL 進退](/backend/11-api-design/styles/graphql/graphql-public-api-tradeoffs/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
