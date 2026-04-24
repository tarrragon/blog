---
title: "7.R1 攻擊面與信任邊界"
date: 2026-04-24
description: "從紅隊角度盤點系統暴露面，以及信任假設在哪裡開始失效"
weight: 711
---

Attack surface 的核心概念是「系統有哪些地方會被外部看見並嘗試互動」。Trust boundary 的核心概念是「信任假設在哪裡開始不再成立」。紅隊會先找這兩件事，因為只要暴露面與邊界不清楚，後面的權限、稽核、遮罩與防護都會變成局部補洞。

## 概念位置

Attack surface 不只是 [Public API](../../knowledge-cards/public-api-endpoint/)。它還包括 [Admin Endpoint](../../knowledge-cards/admin-endpoint/)、[Diagnostic Endpoint](../../knowledge-cards/diagnostic-endpoint/)、[Internal Endpoint](../../knowledge-cards/internal-endpoint/)、[webhook](../../knowledge-cards/webhook/)、upload path、debug flag、cloud resource 與依賴服務的對外介面。Trust boundary 則是從外部呼叫到內部能力、從 tenant 到 tenant、從網路到資料層、從授權前到授權後的切換點。

## 可觀察訊號與例子

系統需要盤點 attack surface 的訊號是存在多種入口、不同權限等級、可枚舉資源與可回傳診斷資訊。若某個 endpoint 可以被猜路徑、透過錯誤訊息推回內部結構，或因預設設定而暴露額外能力，紅隊就會把它視為高優先暴露面。

## 設計責任

暴露面管理要把入口用途、來源限制、資料回應與日誌責任分開定義。對外公開的 surface 需要比內部 surface 更嚴格的驗證、速率控制與回應最小化；任何會跨越 trust boundary 的操作，都要能被明確描述、測試與稽核。
