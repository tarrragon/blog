---
title: "GraphQL 執行成本與攻擊面"
date: 2026-07-03
description: "resolver 執行模型讓請求成本不再是常數 — N+1 的基礎設施化、成本計點限流、introspection 偵察、persisted queries 的收斂路線"
weight: 2
tags: ["backend", "api-design", "graphql", "security"]
---

一個只有 128 bytes 的惡意查詢、可以耗掉 10 秒 CPU。這組數字出自一位六年 GraphQL 使用者的撤退紀錄（[11.C22](/backend/11-api-design/cases/graphql-bessey-retreat/)、反例、含畸形 directives 造成 2,000 倍記憶體放大的並列觀察）、它濃縮了 GraphQL 執行層的結構性質：**請求的成本由 query 的結構決定、而 query 的結構由消費者決定** — 傳統「一個請求約等於一份成本」的容量假設、在 resolver 執行模型下不成立。下面沿這個性質追出四個工程後果；限流的判準層語意已由 [11.9](/backend/11-api-design/external-traffic-semantics/) 承擔、這裡往機制層走。

## N+1：從偶發問題變成預設行為

resolver-per-field 的執行模型讓 N+1 從查詢寫壞才發生的偶發問題、變成不做處理就必然發生的預設：列表的每個元素各自觸發子欄位的 resolver、一層巢狀就是一輪 N 次資料庫存取。[11.C24](/backend/11-api-design/cases/graphql-dataloader-n-plus-one/) 記錄了官方生態的回應方式 — batching 做成基礎設施而非優化技巧：DataLoader 把單一執行 frame 內的個別 load 合併成 batch、概念源自 Facebook 2010 年的內部 Loader API、早於 GraphQL 開源；GitHub 2016 年上線 GraphQL 時、技術棧 day one 就帶著 Shopify 維護的 graphql-batch。判讀：評估 GraphQL 的建置成本時、dataloader 層是基礎配備、不是後期優化項 — 缺少它的 GraphQL 服務、第一個帶列表的巢狀 query 就會對資料庫造成 N 倍讀放大。

## 成本計點：限流模型的被迫重建

請求成本不是常數的直接後果是 per-request 限流失效。[11.C19](/backend/11-api-design/cases/graphql-github-cost-rate-limiting/) 記錄了 GitHub 的完整應對：對每個 query 依 connection 展開計算 point、每小時 5,000 點；另設 500,000 node 上限與分頁參數 1-100 的限制；消費者可事前預估、也可事後查 `rateLimit.cost`。動靜兩層各擋一類風險（C19 判讀）— 成本計點管累積用量、node 上限管單發炸彈；成本模型對消費者透明可預估、是它能當契約的前提（對外流量語意的承諾邊界、見 [11.9](/backend/11-api-design/external-traffic-semantics/)）。自建 GraphQL 公開 API 時這一整層都要自己蓋 — 這是 REST 世界拿現成 gateway 限流就能用的能力。

## Introspection：型別系統是雙面刃

introspection 讓 schema 自我描述、工具鏈（IDE、codegen、文件生成）全建立在它上面 — 同一個能力對攻擊者是免 fuzzing 的偵察工具。[11.C25](/backend/11-api-design/cases/graphql-introspection-auth-bypass/) 是具體實證：某電商平台的第三方服務暴露 GraphQL 端點、introspection 開啟、研究者列舉 schema 後發現未加驗證的 `CreateAdminUser` mutation、直接取得管理權限。REST 世界要靠字典檔猜端點、GraphQL 用型別系統直接把地圖交出去。加上授權模型的難度 — 每個 field 都要各自做授權檢查、且授權檢查本身也會 N+1（C22 觀察）— GraphQL 的攻擊面治理是欄位粒度的、middleware 式的單點防護模型在結構上對不上。

## Persisted queries：介於全開與撤退之間

執行成本與攻擊面的問題有一條收斂路線：把 named operations 存在 server 端、對外只暴露操作 ID、完全不接受任意 query。[11.C27](/backend/11-api-design/cases/graphql-wundergraph-not-for-internet/) 把這條路線推到論證的極端 —「GraphQL 不該直接暴露在公網、該當 server-side 查詢語言用」；來源是販售此方案的 vendor、立場要標明、但攻擊面描述與 C22、C25 獨立互證。persisted queries 的效果是把 GraphQL 的彈性收回開發期：開發時保有 client 聲明取數的 DX、上線後對外面積等於一組預先審核過的操作 — 成本可預算、introspection 可關閉、任意 query 的攻擊面消失。代價是把「第三方自由組合查詢」這個公開 API 的賣點一起收掉 — 對內部 client 幾乎是純收益、對開放平台則等於換了一種產品。

## 判讀訊號

資料庫讀放大跟 API 請求量的比值持續高於預期、先查 dataloader 覆蓋率而非加 read replica；限流被繞過的事故發生在「配額內的重查詢」、代表還在用 per-request 模型計量；滲透測試報告第一項是 introspection 開啟、關掉它之後要接著問「欄位級授權有沒有做」— introspection 只是地圖、權限缺口才是漏洞本體。

## 下一步路由

- 判準層的流量語意與承諾邊界：[11.9 對外流量語意](/backend/11-api-design/external-traffic-semantics/)
- schema 層的演進紀律：[Schema 演進](/backend/11-api-design/styles/graphql/graphql-schema-evolution/)
- 這些成本在組織層的總帳：[公開 API 的 GraphQL 進退](/backend/11-api-design/styles/graphql/graphql-public-api-tradeoffs/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
