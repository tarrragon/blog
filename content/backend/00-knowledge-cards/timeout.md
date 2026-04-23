---
title: "Timeout"
date: 2026-04-23
description: "說明等待外部操作的時間上限如何保護資源與使用者體驗"
weight: 43
---

Timeout 的核心概念是「為一次等待設定時間上限」。後端服務等待 [database](../database/)、cache、[broker](../broker/)、[HTTP client](../http-client/) 呼叫、檔案系統或下游服務時，timeout 決定這次等待最久可以佔用多少資源。

## 概念位置

Timeout 是資源保護與失敗分類的基礎。等待時間上限讓 connection、worker、goroutine、thread、memory 與 request slot 可以釋放，降低單一慢依賴擴散成整體容量問題的機率。

## 可觀察訊號與例子

系統需要 timeout 設計的訊號是 request latency 長尾變高、[connection pool](../connection-pool/) 等待增加、worker 長時間卡住或使用者重複送出操作。Checkout 呼叫付款 API 時，timeout 要短到能保護使用者流程，也要長到能涵蓋正常付款延遲。

## 設計責任

Timeout 要依呼叫目的分層設定。使用者 request、背景 job、database query、外部 API 與 [graceful shutdown](../graceful-shutdown/) cleanup 應有不同時間上限；錯誤回報要標出 timeout 來源，讓 [runbook](../runbook/) 能定位是哪個依賴超時。
