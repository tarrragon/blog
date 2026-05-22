---
title: "Document Store"
date: 2026-05-22
description: "說明以 JSON 文件與彈性 schema 提供資料存取的模式，以及它仍需的治理邊界"
weight: 335
---

Document Store 的核心概念是以 JSON 或 BSON 文件為單位儲存與查詢資料，schema 較彈性、巢狀結構可以直接存。它讓形狀多變或快速演進的資料容易落地，代價是 index、schema 演進與一致性仍要治理，彈性的範圍止於資料形狀、不延伸到免治理。它和關聯式的 [Database](/backend/knowledge-cards/database/) 是不同的資料模型，查詢需求複雜時要對照 [Read Model](/backend/knowledge-cards/read-model/)。

## 概念位置

Document Store 位在資料模型光譜上、和嚴格關聯式 schema 相對的一端。它可以是獨立的 document database，也可以是關聯式引擎內的 JSON 欄位或 document API。它適合放整份一起讀取的聚合資料；當資料間關係變多、需要 join 與跨文件一致性時，要回到關聯式建模或拆出 [Read Model](/backend/knowledge-cards/read-model/)。

## 可觀察訊號與例子

適合 document store 的訊號是資料以「一份完整文件」被讀寫、形狀因來源而異，例如使用者 profile、第三方整合 payload、feature flag 設定。需要重新評估的訊號是巢狀文件變成主要關聯模型，或 JSON 路徑變成核心查詢條件 — 這時要把熱欄位抽出來建 index，或把這部分 relationalize。

## 設計責任

設計時要決定哪些資料適合文件、單份文件多大、哪些 JSON 路徑需要 index，以及 schema 演進怎麼做。文件型資料仍需要 [Schema Migration](/backend/knowledge-cards/schema-migration/) 的紀律 — 欄位語意改變時要有版本與相容策略。observability 要看文件大小分佈，以及熱查詢路徑是否有 index 支撐。
