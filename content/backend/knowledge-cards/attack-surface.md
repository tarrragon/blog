---
title: "Attack Surface"
date: 2026-04-24
description: "說明系統哪些對外暴露面會被先行探測與枚舉"
weight: 123
---


Attack surface 的核心概念是「攻擊者能先看見並嘗試互動的所有暴露面」。它不只包括 public API，也包括 admin route、webhook、diagnostic endpoint、upload path、debug flag、雲端資源與任何能被外部觸及的入口。 可先對照 [Public API Endpoint](/backend/knowledge-cards/public-api-endpoint/)。

## 概念位置

Attack surface 是紅隊分析的起點。它回答「哪裡先被看到」，因此會和 [Public API](/backend/knowledge-cards/public-api-endpoint/)、[Admin Endpoint](/backend/knowledge-cards/admin-endpoint/)、[Diagnostic Endpoint](/backend/knowledge-cards/diagnostic-endpoint/)、[Internal Endpoint](/backend/knowledge-cards/internal-endpoint/)、[webhook](/backend/knowledge-cards/webhook/) 與 [Security Misconfiguration](/backend/knowledge-cards/security-misconfiguration/) 一起被檢查。

## 可觀察訊號與例子

系統只要有多種入口、不同權限等級、可枚舉資源或可回傳診斷資訊，就需要明確盤點 attack surface。若某個 endpoint 可以被猜路徑、透過錯誤訊息推回內部結構，或因預設設定而暴露額外能力，這個 surface 就應該被優先標記。

## 設計責任

暴露面管理要把入口用途、來源限制、資料回應與日誌責任分開定義。對外公開的 surface 需要比內部 surface 更嚴格的驗證、速率控制與回應最小化。
