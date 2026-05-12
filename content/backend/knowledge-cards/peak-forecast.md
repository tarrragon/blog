---
title: "Peak Forecast"
date: 2026-05-12
description: "說明預期峰值流量的預測方法 — 容量規劃的第一個輸入"
weight: 228
---

Peak forecast 的核心概念是「估計未來 N 個月的峰值流量」。容量公式 = 預期峰值 × (1 + headroom)、forecast 錯了下游全部錯。可先對照 [Headroom Budget](/backend/knowledge-cards/headroom-budget/)。

## 概念位置

Forecast 方法分三層：歷史線性外推（適合 sustained growth）、季節性分解（STL，適合電商 / 串流）、業務 ML 模型（結合 marketing pipeline、新用戶獲取、留存）。最常見錯誤是「拿去年同期 × (1 + 預期成長 %)」 — 忽略產品改動 + 行銷投入變化 + 外部事件。可先對照 [Headroom Budget](/backend/knowledge-cards/headroom-budget/)。

## 可觀察訊號與例子

需要重新 forecast 的訊號是「上次 forecast 跟實際差超過 20%」或「業務有重大改動」（新 feature、新市場、新合作）。對應案例：[Disney+ 新片發布](/backend/09-performance-capacity/cases/disney-plus-content-metadata/) 內容型 forecast；[Zoom 30x COVID](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) 外部衝擊讓 forecast 完全失效、必須 reset baseline。

## 設計責任

Forecast 必須有 *誤差範圍*、不能單一數字。給上下界（最壞 / 預期 / 最好）、容量規劃才能用 worst-case 訂 baseline。事件型 forecast 要按 tier 分級（regular / major / critical）、不同 tier 對應不同準備強度。Forecast 跟 [headroom budget](/backend/knowledge-cards/headroom-budget/) 一起算才有意義。
