---
title: "Modular Monolith"
date: 2026-05-27
description: "單一部署單位 + 模組化內部邊界的架構、是 monolith 跟 microservice 之間的折衷形態"
weight: 356
---

Modular monolith 的核心責任是讓單一部署單位內維持明確的模組邊界、約束 dependency 走 interface。換取的是「monolith 的部署簡單」+「microservice 的邊界紀律」、收回兩個極端各自的代價。Shopify、Basecamp、Stack Overflow 是大規模長期維持的代表。跟 [cell-based architecture](/backend/knowledge-cards/cell-based-architecture/) 沿不同維度拆分（cell-based 沿使用者群 / region 拆、modular monolith 沿業務功能拆內部）、跟 [strangler fig](/backend/knowledge-cards/strangler-fig/) 是策略階段關係（modular monolith 是拆分前該先嘗試的中間態）。

## 跟其他概念的關係

Modular monolith 處於系統架構演進的「中段」位置、跟 [cell-based architecture](/backend/knowledge-cards/cell-based-architecture/) 沿不同維度拆分。模組化的具體做法包含：每個模組對外公開的 API 用 interface / port 定義、其他模組只能透過 interface 互動；每個模組擁有自己的 table / schema、跨模組查詢走 interface（取代直接 join）；用 lint rule / build tool 強制 dependency graph 是 DAG；模組可獨立 build / test、最終 deploy 仍是 monolithic。

## 可觀察訊號與例子

適合採用的訊號：業務複雜但團隊規模 5-30 人、部署複雜度敏感（不想維護多服務 ops）、流量 / 團隊 / 變更頻率邊界尚未強到需要拆服務、想為未來拆分做準備。Shopify 在 Rails monolith 內維持 component-based 邊界、Stack Overflow 用單一 ASP.NET monolith 服務全球流量、Basecamp 拒絕 microservice 並 ship Modular Monolith 為長期 endgame。

## 判斷條件與後果

模組邊界只靠約定維持時，跨模組的 import 逐步散落各處，系統退化成普通 monolith，原因是單一部署單位裡沒有任何機制阻止一個模組直接呼叫另一個模組的內部；dependency 方向由 CI 檢查時，違反邊界的 import 在合併前就失敗，不必靠 review 的人逐一記得邊界。團隊在 3 人以下時，每個 feature 都套嚴格 interface 只增加實作摩擦，原因是邊界要防的多團隊互相干擾還沒有出現。多個團隊的發布節奏完全不同，或各模組的流量與資源需求差距大時，單一部署單位讓所有模組一起發布、一起擴充，這時拆成 microservice 換到的獨立部署與獨立擴充，大於多服務的維運成本。
