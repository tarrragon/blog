---
title: "Strangler Fig Pattern"
date: 2026-05-27
description: "服務拆分 / 系統替換的漸進演進模式、用『新舊共存 + 逐步遷移 + 最終下架』取代 big bang 重寫"
weight: 354
---

Strangler Fig pattern 的核心責任是讓 legacy 系統替換成新系統的過程可控、用「新服務從舊 monolith 旁長出、流量逐步遷移、舊系統最終下架」取代 big bang 重寫。跟 big bang 的本質差異是失敗代價可控 — 大爆炸失敗就整個服務掛、Strangler 拆分失敗只影響該功能、可即時切回。跟 [dual write](/backend/knowledge-cards/dual-write/) 是組合關係（dual write 是 strangler 階段 2 的核心執行）。

## 概念位置

Strangler Fig 處於系統演進的策略層、不是單一技術。完整執行需要四階段：邊界冷凍 + Adapter 抽出（在 monolith 內封 interface）、新服務 + [dual write](/backend/knowledge-cards/dual-write/) 雙寫期（並驗證對賬）、切流（讀路徑逐步遷移、按 user ID hash / endpoint / dark launch 分流）、寫路徑遷移 + Monolith 退役（寫路徑切到新服務、舊系統 read-only、最後下架）。

階段 4 是 point of no return — 過了寫路徑切換、新服務累積寫入、回 monolith 要 backfill 成本指數成長。

## 可觀察訊號與例子

大型 monolith 重寫、microservice 拆分、資料庫遷移、第三方 SaaS 換家都用 strangler。完整四階段通常 3-12 個月、雙寫期 1-4 週收斂、切流期 4-12 週逐步推進。Routing layer（API gateway / proxy / feature flag）是核心基礎設施、決定每個 request 走新或舊、出問題能瞬間切回。

## 設計責任

每階段都要有明示的回退條件跟成本評估 — 階段 1-3 回退代價低、階段 4 之後成本指數成長、要把 monolith 下架時點延後到「確信不需要回退」、寧可多保留 monolith 1-2 個月。Monolith 下架前用 access log audit 確認真實流量為 0、避免有 batch job / report / 內部 tool 還在用舊系統。觀察期不可省 — 讀切完後至少 2 週觀察、確認穩定再進階段 4。
