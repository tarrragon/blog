---
title: "Modular Monolith"
date: 2026-05-27
description: "單一部署單位 + 模組化內部邊界的架構、是 monolith 跟 microservice 之間的折衷形態"
weight: 355
---

Modular monolith 的核心責任是讓單一部署單位內維持明確的模組邊界、防止 dependency 互相穿透。換取的是「monolith 的部署簡單」+「microservice 的邊界紀律」、避免兩個極端各自的代價。Shopify、Basecamp、Stack Overflow 是大規模長期維持的代表。跟 [cell-based architecture](/backend/knowledge-cards/cell-based-architecture/) 是不同維度的拆分（cell-based 沿使用者群 / region 拆、modular monolith 沿業務功能拆內部）、跟 [strangler fig](/backend/knowledge-cards/strangler-fig/) 是策略階段關係（modular monolith 是拆分前該先嘗試的中間態）。

## 概念位置

Modular monolith 處於系統架構演進的「中段」位置、跟 [cell-based architecture](/backend/knowledge-cards/cell-based-architecture/) 是不同維度的拆分。模組化的具體做法包含：每個模組對外公開的 API 用 interface / port 定義、不允許其他模組直接 access 內部；每個模組擁有自己的 table / schema、跨模組查詢走 interface 而非 join；用 lint rule / build tool 強制 dependency graph 是 DAG；模組可獨立 build / test、但最終 deploy 是 monolithic。

## 可觀察訊號與例子

適合採用的訊號：業務複雜但團隊規模 5-30 人、部署複雜度敏感（不想維護多服務 ops）、流量 / 團隊 / 變更頻率邊界尚未強到需要拆服務、想為未來拆分做準備。Shopify 在 Rails monolith 內維持 component-based 邊界、Stack Overflow 用單一 ASP.NET monolith 服務全球流量、Basecamp 拒絕 microservice 並 ship Modular Monolith 為長期 endgame。

## 設計責任

維持模組邊界需要團隊紀律 — 聲稱模組化但實際 import 散落各處、跟普通 monolith 沒區別。要在 CI 強制 dependency 方向、不依賴 review 自律。早期團隊（3 人以下）強迫每個 feature 都用嚴格 interface、會增加實作摩擦但無收益。當多團隊發布節奏完全不同、或流量 / 資源需求差距大、就到強制拆服務時機、modular monolith 不該拖延必要決策。
