---
title: "SLI / SLO"
date: 2026-06-22
description: "說明服務品質指標與服務品質目標如何連接產品承諾"
weight: 35
tags: ["backend", "observability"]
---

SLI / SLO 的核心概念是「用可量測訊號表達服務承諾」。SLI（Service Level Indicator）是服務品質指標 — 成功率、延遲、可用性；SLO（Service Level Objective）是這些指標的目標 — 99.9% request 在 300ms 內成功回應。SLO 的執行力來自 [error budget](/backend/knowledge-cards/error-budget/) — 預算耗盡就暫停發版。

## 跟其他概念的關係

SLI / SLO 把觀測資料轉成決策語言。單純看到 error rate 上升只能說明症狀；對照 SLO 後，團隊才能判斷是否需要暫停發版、啟動 incident、擴容或降級。SLO 不是「越高越好」— 99.999% 的 SLO 意味著幾乎沒有 [error budget](/backend/knowledge-cards/error-budget/) 做變更，反而限制了功能交付速度。

SLI 的設計起點是使用者旅程（checkout 是否成功、搜尋是否夠快），量測點選擇（edge / gateway / service）決定了 SLI 反映的是「使用者體驗」還是「基礎設施健康」。

## 使用情境

系統需要 SLI / SLO 的訊號是服務重要性已經影響收入、合約或使用者信任。付款、登入、訂單建立與訊息送達通常需要不同 SLO，因為失敗代價不同。

## 判斷條件與後果

SLI 與 SLO 的定義缺了某一項時，數字照樣算得出來，卻支持不了決策。SLI 沒有界定什麼算 good request 時，client 送錯參數造成的 4xx 也可能被算成服務失敗，SLI 混進了 client 自己的錯誤，所以常見的界定是 5xx 算 bad、4xx 通常不算；SLO 沒有量測窗口（例如 30 天 rolling）時，同一個目標值換一個時段計算就可能從達標變成不達標；SLO 沒有 owner 時，[error budget](/backend/knowledge-cards/error-budget/) 耗盡之後，暫停發版這個決定沒有指定的決策者。SLO 搭配 [burn rate](/backend/knowledge-cards/burn-rate/) alerting 時，[alert](/backend/knowledge-cards/alert/) 依預算消耗的速度觸發，反映使用者受到的影響；直接對基礎設施指標設門檻時，alert 反映資源的波動，其中包括不影響使用者的波動。完整設計見 [4.6 SLI/SLO 訊號設計](/backend/04-observability/sli-slo-signal/)。
