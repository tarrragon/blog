---
title: "Mock 邊界判斷決策表"
date: 2026-06-19
description: "什麼時候 mock 夠用、什麼時候需要真實服務 — 從 API 層 / 協議層 / 環境層的斷裂點判斷 mock 的適用範圍"
weight: 1
tags: ["testing", "mock", "decision", "boundary", "integration-test"]
---

Mock 的適用範圍由它模擬的層級決定。Mock 忠實模擬 API 層的契約（方法簽名、參數型別），但無法模擬協議層的語意差異和環境層的行為差異。判斷「這個 test 用 mock 夠不夠」的依據是：test 要驗證的行為發生在哪一層。

## 決策依據

### Mock 夠用的場景

Test 驗證的行為完全在程式碼內部 — 函式邏輯、狀態機轉換、資料轉換、錯誤處理分支。這些行為不依賴外部服務的協議細節，mock 提供的 API 層模擬已經足夠。

判斷問題：**如果把 mock 替換成真實服務，test 的斷言結果會不會改變？** 如果不會改變，mock 夠用。

例：`ConnectionManager` 收到 error 後是否正確切換到 error 狀態 — 不管 error 來自 mock 還是真實 WebSocket，狀態機邏輯相同。Mock 夠用。

### Mock 不夠的場景

Test 要驗證的行為涉及外部服務的協議行為 — frame type 差異、認證流程、編碼格式、逾時行為。Mock 的 API 層模擬跳過了這些行為，test 通過不代表真實互動也通過。

判斷問題：**Mock 跳過了外部服務的哪些步驟？這些步驟的行為是否影響 test 要驗證的結果？** 如果是，需要 protocol integration test（[testing 模組三](/testing/03-protocol-integration-test/)）。

例：`sendData()` 發送鍵盤輸入 — mock 的 `sink.add(dynamic)` 接受任何型別，但真實 `IOWebSocketChannel` 對 `String` 和 `Uint8List` 產生不同 frame type。Mock 不夠。

## 決策表

| 驗證對象          | Mock 夠用？ | 理由                                    |
| ----------------- | ----------- | --------------------------------------- |
| 函式回傳值        | 夠          | 回傳值只依賴程式碼邏輯                  |
| 狀態機轉換        | 夠          | 轉換邏輯在程式碼內部                    |
| 錯誤處理分支      | 夠          | error 來源不影響處理邏輯                |
| 資料格式轉換      | 夠          | 轉換邏輯在程式碼內部                    |
| 連線建立成功/失敗 | 視情況      | 如果只驗證「收到成功/失敗後做什麼」→ 夠 |
| 認證流程完整性    | 不夠        | mock 可能跳過認證步驟                   |
| 資料編碼格式      | 不夠        | mock 不區分編碼差異（text vs binary）   |
| 逾時行為          | 不夠        | mock 的回應時間和真實服務不同           |
| 多步驟協議流程    | 不夠        | mock 可能簡化多步驟為單步               |

## 灰色地帶的判斷

有些 test 介於「mock 夠用」和「mock 不夠」之間。例如驗證「連線失敗時顯示 error 訊息」— 觸發失敗的方式可以是 mock 回傳 error（驗證顯示邏輯），也可以是真實服務拒絕連線（驗證真實失敗場景的處理）。

灰色地帶的判斷策略是：用 mock test 驗證「收到 error 後的處理邏輯」，用 protocol integration test 驗證「真實服務在什麼情況下回傳 error」。兩層 test 各自回答不同問題，不互相替代（[testing 模組一 三層定義](/testing/01-test-strategy-layers/three-layer-definition/)）。

## 下一步路由

- 測試資料的代表性問題 → [Test data 代表性](/testing/05-test-design-judgment/test-data-representativeness/)
- Mock 遮蔽的結構性分析 → [testing 模組一 Mock 遮蔽機制](/testing/01-test-strategy-layers/mock-masking-mechanism/)
- Protocol integration test 的成本判斷 → [testing 模組三 成本判斷表](/testing/03-protocol-integration-test/cost-judgment/)
