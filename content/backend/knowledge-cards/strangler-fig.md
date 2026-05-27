---
title: "Strangler Fig Pattern"
date: 2026-05-27
description: "服務拆分 / 系統替換的漸進演進模式、用「新舊共存 + 逐步遷移 + 最終下架」取代 big bang 重寫"
weight: 354
---

Strangler Fig pattern 是漸進拆分 / 替換 legacy 系統的工程模式。Martin Fowler 用熱帶絞殺榕做比喻：榕樹依附宿主樹生長、最終取代宿主。應用到服務拆分：新服務從舊 monolith 旁長出、流量逐步遷移、舊系統最終下架。跟 big bang 重寫的本質差異是「失敗代價可控」— 大爆炸失敗就整個服務掛、Strangler 拆分失敗只影響該功能。常跟 [dual write](/backend/knowledge-cards/dual-write/) 跟 routing layer（API gateway / proxy / feature flag）組合使用。

## 概念位置

Strangler Fig 處於系統演進的策略層、不是單一技術。跟 [dual write](/backend/knowledge-cards/dual-write/) 是組合關係（dual write 是 strangler 階段 2 的核心執行）。完整執行需要四階段：

1. **邊界冷凍 + Adapter 抽出**：在 monolith 內把要拆出去的功能封進 adapter / interface、強制 dependency 顯式化
2. **新服務 + 雙寫期**：新服務 spin up、所有寫入 dual write、讀取仍走舊
3. **切流（讀路徑遷移）**：用 routing layer 把讀路徑逐步切到新服務、按 user ID hash / endpoint / dark launch 分流
4. **寫路徑遷移 + Monolith 退役**：寫路徑切到新服務、舊系統變 read-only、最後下架

## 關鍵設計

- **Routing layer 是 strangler 的核心**：API gateway / proxy / feature flag 決定每個 request 走新或舊、出問題能瞬間切回
- **每階段都有回退路徑**：階段 1-3 回退代價低、階段 4 是 point of no return（過了寫路徑切換、新服務累積寫入、回 monolith 要 backfill）
- **觀察期不可省**：讀切完後至少 2 週觀察、確認穩定再進階段 4
- **monolith 下架前 access log audit**：用 access log 確認真實流量為 0、避免有 batch job / report / 內部 tool 還在用舊系統

## 適用 vs 不適用

適用：

- 大型 legacy monolith 重寫
- 服務拆分（從 monolith 拆出 microservice）
- 資料庫遷移（同個概念套用到資料層）
- 第三方 SaaS 換家

不適用：

- 新系統跟舊系統業務邏輯差異大（dual write 對應不上）
- 沒有 routing layer 能力（無法精細控制流量比例）
- 緊急合規截止日（漸進演進需要時間、不如快速重寫）

## 失敗模式

- **跳過階段 1**：直接拆功能出去、新舊服務 dependency 邊界不清楚、雙寫期會出現難 debug 的隱式依賴
- **雙寫期太短**：差異率沒收斂就切流、出資料一致性事故
- **monolith 下架太早**：仍有隱藏呼叫者、下架後出事
