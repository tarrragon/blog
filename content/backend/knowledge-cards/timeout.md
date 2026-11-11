---
title: "Timeout"
tags: ["逾時", "Timeout"]
date: 2026-04-23
description: "說明等待外部操作的時間上限如何保護資源與使用者體驗"
weight: 44
---

Timeout 的核心概念是「為一次等待設定時間上限」。後端服務等待 [database](/backend/knowledge-cards/database/)、cache、[broker](/backend/knowledge-cards/broker/)、[HTTP client](/backend/knowledge-cards/http-client/) 呼叫、檔案系統或下游服務時，timeout 決定這次等待最久可以佔用多少資源。

## 跟其他概念的關係

Timeout 是資源保護與失敗分類的基礎。等待時間上限讓 connection、worker、goroutine、thread、memory 與 request slot 可以釋放，降低單一慢依賴擴散成整體容量問題的機率。 可先對照 [Database](/backend/knowledge-cards/database/)。服務端的等待上限讓過載時的結果從無回應變成請求失敗，見 [9.16 負載超過容量時服務的表現](/backend/09-performance-capacity/overload-outcomes/)〈無回應：程序還在，請求等到逾時也沒有結果〉。

## 可觀察訊號與例子

系統需要 timeout 設計的訊號是 request latency 長尾變高、[connection pool](/backend/knowledge-cards/connection-pool/) 等待增加、worker 長時間卡住或使用者重複送出操作。Checkout 呼叫付款 API 時，timeout 要短到能保護使用者流程，也要長到能涵蓋正常付款延遲。

## 判斷條件與後果

Timeout 的上限取決於呼叫目的，因為每一種等待佔住的資源與可以接受的等待時間不同：使用者 request 的上限受使用者願意等多久限制，背景 job 沒有人在等，可以放寬；database query 的上限決定 [connection pool](/backend/knowledge-cards/connection-pool/) 裡的連線被佔住多久；外部 API 的上限太短時正常的付款也被判成失敗，太長時卡住的呼叫佔住 worker；[graceful shutdown](/backend/knowledge-cards/graceful-shutdown/) cleanup 的上限決定程序最久多久才結束。全部用同一個值時，至少有一種呼叫的上限不合它的目的。錯誤回報沒有標出 timeout 發生在哪一個依賴時，上層只看到「逾時」，[runbook](/backend/knowledge-cards/runbook/) 定位不了是哪個依賴變慢。
