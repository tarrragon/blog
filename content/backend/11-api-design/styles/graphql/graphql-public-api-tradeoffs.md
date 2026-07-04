---
title: "公開 API 的 GraphQL 進退"
date: 2026-07-03
description: "GitHub 雙軌、Shopify all-in、與撤退案例 — 同一技術不同結局的情境變數、GraphQL 的適用邊界"
weight: 3
tags: ["backend", "api-design", "graphql"]
---

同一個技術、公開 API 領域至少有四種結局在一手資料裡並存：GitHub 採用後走向雙軌共存、Shopify 宣告 all-in、一類團隊從執行成本撤退、另一類從開發體驗撤退。四種結局沒有對錯排序 — 每一種都對應一組可辨識的情境變數、本文的目標是把變數抽出來。

## 採用：動機要能量化

[11.C18](/backend/11-api-design/cases/graphql-github-adoption/) 記錄了 GitHub 2016 年的採用動機、關鍵在它的可量化性：既有 REST API 佔資料庫層超過 60% 的請求、且 over-fetching 與 under-fetching 並存 — 送太多資料、又缺消費者要的資料。這是基礎設施成本層的痛、不只是開發體驗敘事。判讀：GraphQL 的採用決策值得用同樣的標準檢驗 — 說得出「哪個資源層指標會因 client 聲明取數而改善」、動機成立；只說得出「前端想要彈性」、先確認這個彈性有多少會被實際用到（消費者形狀判準、見 [11.2](/backend/11-api-design/api-style-selection/)）。

## 穩態一：雙軌共存

GitHub 的十年後狀態記錄在 [11.C20](/backend/11-api-design/cases/graphql-github-rest-parallel/)：官方立場是 REST 與 GraphQL 並行、依情境選用、且明文說明功能覆蓋不對等 — 某功能可能只在其中一個 API 支援。這是「新風格取代舊風格」預期的反面實證：兩套 API 各自累積消費者之後、任何一套的退場都是大規模 breaking change（成本結構見 [11.1](/backend/11-api-design/api-boundary-responsibility/)）、共存從過渡狀態變成永久狀態。雙軌的隱藏成本是每個新功能的「要不要兩邊都做」決策與文件、SDK、支援的雙倍表面積 — 採用前把這筆帳算進去、雙軌不是免費的中間路線。

## 穩態二：平台強制的 all-in

[11.C21](/backend/11-api-design/cases/graphql-shopify-all-in/) 記錄了反方向的極端：Shopify 2024 年把 REST Admin API 標為 legacy、新上架 app 強制只用 GraphQL、配套 rate limit 加倍與 connection query 成本降 75%。這條路線的成立條件寫在案例的結構裡 — Shopify 對 app 生態有審核強制力（新 app 不遷就上不了架）、遷移壓力不靠說服。判讀有兩層：對平台方、all-in 的前提是強制力、沒有 app store 式關卡的組織複製這個策略只會得到雙軌的事實與 all-in 的公告；對生態方、成本降 75% 的配套反向印證了執行成本（[前一篇](/backend/11-api-design/styles/graphql/graphql-execution-cost-security/) 的計點模型）是 GraphQL 採用的隱含稅 — 平台要自己吸收一部分、生態才動得起來。

## 撤退：兩類動機、兩個教訓

撤退案例分兩類、動機幾乎正交。執行成本類（[11.C22](/backend/11-api-design/cases/graphql-bessey-retreat/)、反例）：六年使用者列出的代價全在執行期與安全面 — 欄位級授權、成本不可預測、解析層攻擊面、防禦性 dataloader；撤退判準句是「控制得了 client、就不需要 GraphQL 的彈性」（C22 判讀核心句）。開發體驗類（[11.C23](/backend/11-api-design/cases/graphql-echobind-trpc-retreat/)、反例）：同一資料形狀在五層重複宣告、三層 codegen 產出 8,200 行型別檔拖垮 IDE、遷移到 tRPC 後淨減 1,608 行；作者自列的前提是全 TypeScript 同倉 — schema 作為跨團隊契約的價值、在單團隊同構技術棧下變成純開銷。

兩類撤退指向同一條邊界的兩側：GraphQL 的 schema 中介層、價值在「跨團隊 / 跨 client 的契約協調」— 消費者異質且不受控、彈性有買家、中介層成本值得；消費者單一且同構、彈性沒有買家、中介層是稅。C23 的 tRPC 面向（型別共享的前提與代價）主寫在 [tRPC 型別共享](/backend/11-api-design/styles/rpc-revival/rpc-revival-trpc-type-sharing/)。

## 中間路線與適用邊界

全開與撤退之間有 persisted queries 的收斂路線（案例 [11.C27](/backend/11-api-design/cases/graphql-wundergraph-not-for-internet/)；機制與 vendor 立場標注見 [執行成本篇](/backend/11-api-design/styles/graphql/graphql-execution-cost-security/) 的 persisted queries 段）：內部保留 GraphQL 的開發彈性、對外只暴露預審操作。把四種結局加中間路線並排、適用邊界收斂成三個問句：消費者是誰、有多異質（單團隊同構 → 撤退案例的前車）；對生態有沒有強制力（沒有 → 雙軌是實際終點、all-in 只是公告）；執行層的計點限流、欄位授權、dataloader 誰來蓋（沒人蓋 → 攻擊面與容量問題按 [執行成本篇](/backend/11-api-design/styles/graphql/graphql-execution-cost-security/) 的清單逐項到期）。

## 下一步路由

- 選型判準層：[11.2 風格選型總覽](/backend/11-api-design/api-style-selection/)
- 執行層機制：[GraphQL 執行成本與攻擊面](/backend/11-api-design/styles/graphql/graphql-execution-cost-security/)
- schema 層紀律：[Schema 演進](/backend/11-api-design/styles/graphql/graphql-schema-evolution/)
- 同一條邊界的 tRPC 側：[tRPC 型別共享](/backend/11-api-design/styles/rpc-revival/rpc-revival-trpc-type-sharing/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
