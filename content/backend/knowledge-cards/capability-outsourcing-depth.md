---
title: "Capability Outsourcing Depth（外包深度）"
slug: "capability-outsourcing-depth"
date: 2026-06-14
description: "說明外包一塊後端能力有三種深度（managed 基礎設施、feature SaaS、BaaS bundle）、深度決定保留多少控制權與遷出代價"
weight: 375
---

外包深度的核心概念是：把一塊後端能力交給外部服務、不是一個二元動作、而是有層次的 — 同樣是「不自己寫」、把維運交出去跟把整塊能力連業務邏輯一起交出去、保留的控制權與 [Vendor Lock-In](/backend/knowledge-cards/vendor-lock-in/) 的退出成本差一個量級。三種深度由淺到深是 managed 基礎設施、feature SaaS 與 BaaS bundle；判斷一塊能力該外包到哪個深度、是選型時與「買還是建」並列的問題。它跟 [BaaS](/backend/knowledge-cards/baas/) 的差別在抽象層級：BaaS 是最深那一層的具體交付形態、外包深度是涵蓋三層的判讀軸。

## 概念位置

外包深度位在「買 vs 建」決策的下一層：決定了某塊能力要買之後、還要決定買到多深。最淺的 managed 基礎設施只外包維運、schema 與 query 仍是自己的、跟自建世界的 [database](/backend/knowledge-cards/database/) 共用同一套資料模型控制權；中間的 feature SaaS 透過 [Provider Adapter](/backend/knowledge-cards/provider-adapter/) 消費一組 API、整塊能力的內部邏輯交給 vendor；最深的 BaaS bundle 一個 vendor 同時交付多塊能力、用整合當賣點。深度越深、保留的控制權越少、遷出時要拆解的整合面越大。

## 可觀察訊號與例子

辨識深度看「撞牆時你改得動的邊界在哪」。managed 基礎設施撞到慢查詢、自己加 index、自己改 schema — 邊界很寬、只有底層硬體與維運在 vendor 手上、代表服務是 Aurora、ElastiCache、Neon。feature SaaS 撞到 vendor 沒開放的客製、就只能在它之外再搭一層、邊界縮到 vendor 的擴展點為止 — Auth0、Algolia、Stripe 屬 dev-tool 端、Ragic、SurveyCake、Airtable 屬同深度的 no-code 端、差別在誰來維護。BaaS bundle 撞牆時要把一塊能力跟它和其他能力的整合關係一起拆 — Supabase 把 Postgres、Auth、Storage、Realtime 用同一套身分綁在一起、搬走資料層要連帶處理它跟認證、儲存的接點。

## 設計責任

選定外包深度時的設計責任是把深度對應的遷出代價先記進選型結論。managed 基礎設施遷出代價低到中、資料是標準格式、換家主要是搬資料改連線；feature SaaS 中到高、資料模型與業務規則沿 vendor 特性長出來；BaaS bundle 最高、代價不在資料量而在被同一套整合綁住的能力之間。深度不是越淺越好 — 越深省下的整合與維運越多、bundle 的整合本身就是它的價值；責任是讓「省下多少」與「綁住多深」在同一筆帳上算清、而不是只看其中一邊。判斷一塊能力該外包到哪個深度、屬於能力級買 vs 建的選型判讀。
