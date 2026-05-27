---
title: "Modular Monolith"
date: 2026-05-27
description: "單一部署單位 + 模組化內部邊界的架構模式、是 monolith 跟 microservice 之間的折衷形態"
weight: 355
---

Modular monolith 是 monolith 跟 microservice 之間的折衷架構：保留單一部署單位、但在程式碼內部用明確的模組邊界防止 dependency 互相穿透。換取的是「monolith 的部署簡單」+「microservice 的邊界紀律」、避免兩個極端各自的代價。Shopify、Basecamp、Stack Overflow 是大規模長期維持的代表。跟 [Strangler Fig pattern](/backend/knowledge-cards/strangler-fig/) 經常一起出現 — modular monolith 是拆分前該先嘗試的中間態、若邊界已紮實、可能根本不需要進到 microservice。

## 概念位置

Modular monolith 處於系統架構演進的「中段」位置、跟 [cell-based architecture](/backend/knowledge-cards/cell-based-architecture/) 是不同維度的拆分（cell-based 沿使用者群 / region 拆、modular monolith 沿業務功能拆內部）：

| 階段                 | 部署單位 | 內部邊界          | 適合規模                |
| -------------------- | -------- | ----------------- | ----------------------- |
| Monolith             | 單一     | 鬆散 / 無顯式邊界 | 早期、單一團隊          |
| **Modular monolith** | **單一** | **明確模組邊界**  | **中型、多人 / 多模組** |
| Microservice         | 多個獨立 | 服務 + 網路邊界   | 多團隊、業務已分化      |

## 模組化的具體做法

- **明確的內部 interface**：每個模組對外公開的 API 用 interface / port 定義、不允許其他模組直接 access 內部
- **資料邊界**：每個模組擁有自己的 table / schema、跨模組查詢走 interface 而非 join
- **依賴方向限制**：用 lint rule / build tool 強制 dependency graph 是 DAG（有向無環）
- **可分離的編譯單元**：每個模組可獨立 build / test、雖然最終 deploy 是 monolithic

## 適用 vs 不適用

適用：

- 業務複雜但團隊規模不大（5-30 人）
- 部署複雜度敏感（不想維護多服務 ops 成本）
- 還沒到強制拆分時機（流量 / 團隊 / 變更頻率邊界尚未強）
- 想為未來拆分做準備（modular 邊界扎實後拆服務代價低）

不適用：

- 多團隊發布節奏完全不同（部署綁在一起變主要痛點）
- 流量 / 資源需求差距大（需要不同擴展軸）
- 已經到拆分時機（pretend modular monolith 拖延必要決策）

## 反模式

- **「modular monolith」當口號、不執行邊界紀律**：聲稱模組化但實際 import 散落各處、跟普通 monolith 沒區別
- **過度模組化早期**：3 人團隊強迫每個 feature 都用嚴格 interface、增加實作摩擦但無收益
- **把 modular monolith 當「拆分失敗的退路」**：應該是主動選擇、不是「拆不出來只好回來」
