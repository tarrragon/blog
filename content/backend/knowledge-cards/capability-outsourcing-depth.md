---
title: "Capability Outsourcing Depth（外包深度）"
slug: "capability-outsourcing-depth"
date: 2026-06-14
description: "說明外包一塊後端能力有三種深度（managed 基礎設施、feature SaaS、BaaS bundle）、深度決定保留多少控制權與遷出代價"
weight: 375
---

外包深度的核心概念是：把一塊後端能力交出去有深淺之分、不是「全有或全無」的二元 — 同樣是「不自己寫」、把維運交出去跟把整塊能力連業務邏輯一起交出去、保留的控制權與 [Vendor Lock-In](/backend/knowledge-cards/vendor-lock-in/) 的退出成本差一個量級。三種深度由淺到深是 managed 基礎設施、feature SaaS 與 BaaS bundle — 這條軸只涵蓋雲端託管側、自架 OSS 或 on-prem 授權、只租控制平面的自管形態鎖定在運維 know-how 與授權、屬軸外的另一類。判斷一塊能力該外包到哪個深度、是選型時與「買還是建」並列的問題。它跟 [BaaS](/backend/knowledge-cards/baas/) 的差別在抽象層級：BaaS 是最深那一層的具體交付形態、外包深度是涵蓋三層的判讀軸。

## 概念位置

外包深度位在「買 vs 建」決策的下一層：決定了某塊能力要買之後、還要決定買到多深。最淺的 managed 基礎設施只外包維運、schema 與 query 仍是自己的、跟自建世界的 [database](/backend/knowledge-cards/database/) 共用同一套資料模型控制權；中間的 feature SaaS 透過 [Provider Adapter](/backend/knowledge-cards/provider-adapter/) 消費一組 API、整塊能力的內部邏輯交給 vendor；最深的 BaaS bundle 一個 vendor 同時交付多塊能力、用整合當賣點。深度越深、保留的控制權越少、遷出時要拆解的整合面越大。

## 可觀察訊號與例子

辨識深度看「撞牆時你改得動的邊界在哪」。一個跑在 Aurora 或 Neon 上的服務撞到慢查詢、可以自己加 index、改 schema、重寫 query — 能動的邊界很寬、只有底層硬體與維運落在 vendor 手上、這是 managed 基礎設施（managed 內部還有梯度：受限的 serverless 或 BaaS 內嵌的 Postgres 可能沒有 superuser、裝不了 extension、能動的邊界比一台完整 managed 實例窄）。換成 Auth0 或 Algolia、撞到的是 vendor 沒開放的客製：它的擴展點到哪、邊界就到哪、再過去只能在它之外另搭一層 — 這是 feature SaaS、Auth0、Algolia、Stripe 在 dev-tool 端、Ragic、SurveyCake、Airtable 在同深度的 no-code 端、差別在誰來維護。最深一層撞牆時連邊界都不只一條：Supabase 把 Postgres、Auth、Storage、Realtime 用同一套身分綁在一起、想搬走資料層、得連帶拆掉它跟認證、儲存的接點 — 這是 BaaS bundle。

## 設計責任

選定外包深度時的設計責任是把深度對應的遷出代價先記進選型結論。managed 基礎設施遷出代價低到中、資料是標準格式、換家主要是搬資料改連線；feature SaaS 中到高、資料模型與業務規則沿 vendor 特性長出來；BaaS bundle 最高、代價落在被同一套整合綁住的能力之間、不在資料量。深度不是越淺越好 — 越深省下的整合與維運越多、bundle 的整合本身就是它的價值；責任是讓「省下多少」與「綁住多深」在同一筆帳上算清、而不是只看其中一邊。判斷一塊能力該外包到哪個深度、屬於能力級買 vs 建的選型判讀。
