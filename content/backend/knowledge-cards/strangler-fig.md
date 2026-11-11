---
title: "Strangler Fig Pattern"
date: 2026-05-27
description: "服務拆分 / 系統替換的漸進演進模式、用『新舊共存 + 逐步遷移 + 最終下架』取代 big bang 重寫"
weight: 355
---

Strangler Fig pattern 的核心責任是讓 legacy 系統替換成新系統的過程可控、用「新服務從舊 monolith 旁長出、流量逐步遷移、舊系統最終下架」取代 big bang 重寫。跟 big bang 的本質差異是失敗代價可控 — 大爆炸失敗就整個服務掛、Strangler 拆分失敗只影響該功能、可即時切回。跟 [dual write](/backend/knowledge-cards/dual-write/) 是組合關係（dual write 是 strangler 階段 2 的核心執行）。

## 跟其他概念的關係

Strangler Fig 處於系統演進的策略層、是組合多種技術的執行框架。完整執行需要四階段：邊界冷凍 + Adapter 抽出（在 monolith 內封 interface）、新服務 + [dual write](/backend/knowledge-cards/dual-write/) 雙寫期（並驗證對賬）、切流（讀路徑逐步遷移、按 user ID hash / endpoint / dark launch 分流）、寫路徑遷移 + Monolith 退役（寫路徑切到新服務、舊系統 read-only、最後下架）。

階段 4 是 point of no return — 過了寫路徑切換、新服務累積寫入、回 monolith 要 backfill 成本指數成長。

## 可觀察訊號與例子

大型 monolith 重寫、microservice 拆分、資料庫遷移、第三方 SaaS 換家都用 strangler。完整四階段通常 3-12 個月、雙寫期 1-4 週收斂、切流期 4-12 週逐步推進。Routing layer（API gateway / proxy / feature flag）是核心基礎設施、決定每個 request 走新或舊、出問題能瞬間切回。

## 判斷條件與後果

Strangler 各階段的回退代價不同。階段 1 到 3 的寫入仍在 monolith，切回只是改 routing，代價低；進入階段 4 之後新服務開始累積 monolith 沒有的寫入，回退之前要先 backfill，成本隨累積的寫入快速成長。所以 monolith 下架得越晚，回退的選項保留得越久，代價是多維運一套系統；經驗值是寧可多保留 monolith 1-2 個月，到回退已經罕見才下架。讀路徑切完之後的觀察期（經驗值是至少 2 週）確認新服務在真實流量下穩定，跳過觀察期等於把還沒驗證過的讀路徑帶進沒有回頭路的階段 4。下架之前 access log 若仍有請求打到 monolith，代表還有 batch job、報表或內部工具沒有切換，這時下架會讓它們直接失敗，所以 access log 確認真實流量為 0 才下架。
