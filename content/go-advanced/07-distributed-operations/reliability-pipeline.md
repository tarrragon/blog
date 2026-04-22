---
title: "7.6 CI、fuzz、load test 與 chaos testing"
date: 2026-04-22
description: "把單元測試與整合測試擴展成服務可靠性驗證流程"
weight: 6
---

可靠性驗證流程的核心責任是讓不同層級的測試回答不同風險。Unit test 驗證規則，integration test 驗證協定協作，race test 檢查資料競爭，fuzz test 尋找輸入邊界，load test 驗證容量，chaos test 驗證失敗復原。

## 前置章節

- [Go 入門：testing 基礎](../../go/05-error-testing/testing-basics/)
- [Go 進階：WebSocket integration test](../05-testing-reliability/websocket-integration/)
- [Go 進階：race condition 檢查](../05-testing-reliability/race-check/)
- [Go 進階：table-driven test 的設計邊界](../05-testing-reliability/table-tests/)

## 後續撰寫方向

1. CI 中哪些測試應每次執行，哪些可以排程或合併前執行。
2. Fuzzing 適合驗證 parser、normalizer 與 protocol decoder 的哪些邊界。
3. Load test 如何設定 client 數、message rate、payload size 與觀測指標。
4. Chaos testing 如何模擬 broker 斷線、資料庫延遲、server shutdown 與網路抖動。
5. 測試結果如何回饋到 capacity planning 與 feature gate。

## 本章不處理

本章不會綁定特定 CI 或壓測平台。教材重點會放在測試層級分工，避免把所有風險都塞進端到端測試。
