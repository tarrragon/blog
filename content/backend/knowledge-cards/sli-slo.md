---
title: "SLI / SLO"
date: 2026-06-22
description: "說明服務品質指標與服務品質目標如何連接產品承諾"
weight: 34
tags: ["backend", "observability"]
---

SLI / SLO 的核心概念是「用可量測訊號表達服務承諾」。SLI（Service Level Indicator）是服務品質指標 — 成功率、延遲、可用性；SLO（Service Level Objective）是這些指標的目標 — 99.9% request 在 300ms 內成功回應。SLO 的執行力來自 [error budget](/backend/knowledge-cards/error-budget/) — 預算耗盡就暫停發版。

## 概念位置

SLI / SLO 把觀測資料轉成決策語言。單純看到 error rate 上升只能說明症狀；對照 SLO 後，團隊才能判斷是否需要暫停發版、啟動 incident、擴容或降級。SLO 不是「越高越好」— 99.999% 的 SLO 意味著幾乎沒有 [error budget](/backend/knowledge-cards/error-budget/) 做變更，反而限制了功能交付速度。

SLI 的設計起點是使用者旅程（checkout 是否成功、搜尋是否夠快），量測點選擇（edge / gateway / service）決定了 SLI 反映的是「使用者體驗」還是「基礎設施健康」。

## 使用情境

系統需要 SLI / SLO 的訊號是服務重要性已經影響收入、合約或使用者信任。付款、登入、訂單建立與訊息送達通常需要不同 SLO，因為失敗代價不同。

## 設計責任

SLI 需要定義「什麼算 good request」的邊界（5xx 算 bad、4xx 通常不算）。SLO 需要定義目標值、量測窗口（30 天 rolling）跟 owner。SLO 跟 [burn rate](/backend/knowledge-cards/burn-rate/) alerting 搭配使用，讓 [alert](/backend/knowledge-cards/alert/) 反映使用者影響而非基礎設施噪音。完整設計見 [4.6 SLI/SLO 訊號設計](/backend/04-observability/sli-slo-signal/)。
