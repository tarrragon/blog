---
title: "三層定義與職責表"
date: 2026-06-19
description: "Unit Test / Protocol Integration Test / Screen State Test 各層職責、驗證目標與盲區的完整論述"
weight: 1
tags: ["testing", "strategy", "mock", "integration-test", "screen-state-test"]
---

測試分層的目的是讓每一層只負責一類問題，使得「哪種 bug 該被哪層抓到」有明確歸屬。三層之間存在語意斷層，單靠一層無論寫多少 test 都無法跨越另一層的職責。

## 三層的職責邊界

### Unit Test：驗證程式碼邏輯

Unit test 驗證的對象是「開發者寫的程式碼是否按預期運作」。它的輸入和輸出都在程式碼控制範圍內 — 函式的參數、回傳值、狀態變化、例外拋出。

Unit test 的盲區是所有程式碼以外的東西。外部服務的協議行為、網路傳輸的編碼方式、作業系統的檔案鎖定機制 — 這些不在 unit test 的驗證範圍內，因為 unit test 用 mock 取代了這些外部依賴。Mock 忠實模擬的是程式語言層面的 API 契約（方法簽名、參數型別、回傳值），不是外部服務的協議行為。

app_tunnel 的 192 個 unit test 全部通過，但實機連線後鍵盤輸入無回應。原因是 WebSocket 的 text frame 與 binary frame 差異屬於協議層語意 — `FakeWebSocketChannel` 的 `sink.add(dynamic)` 接受任何型別，不區分 frame type（[T.C1](/testing/cases/ws-text-binary-frame-mock-blindspot/)）。192 個 test 驗證的是「Dart 程式碼邏輯正確」，沒有任何一個 test 的職責是驗證「ttyd 收到的 frame type 是否正確」。

### Protocol Integration Test：驗證真實協議互動

[Protocol integration test](/testing/knowledge-cards/protocol-integration-test/) 驗證的對象是「程式碼和真實外部服務之間的協議互動是否正確」。它不用 mock，而是對真實的服務實例發送請求，觀察真實的回應。

這一層的驗證目標包括：連線握手是否完成、認證流程是否正確、資料編碼是否符合對方期望、逾時行為是否合理。這些問題的答案不在程式碼裡，而是在程式碼與外部服務的互動過程中。

app_tunnel 的 auth handshake 缺失就是典型案例。ttyd 要求連線後發送 auth token JSON frame，但 `ConnectionManager` 沒有實作這個步驟 — `FakeWebSocketChannel.ready` 立即完成不需認證，所有 test 看到的都是連線成功（[T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/)）。對真實 ttyd 執行一個「連線後不發 auth token，斷言 timeout」的 test，就能暴露這個缺失。

### Screen State Test：驗證畫面狀態完整性

[Screen state test](/testing/knowledge-cards/screen-state-test/) 驗證的對象是「使用者可見的畫面狀態是否覆蓋所有情境」。它的關注點是畫面層級的狀態機 — loading、connected、error、reconnecting 等狀態之間的轉換是否完整，每個狀態下使用者看到什麼、能操作什麼。

Screen state test 和 unit test 的區別在於斷言對象：unit test 斷言「函式回傳值是否正確」，screen state test 斷言「使用者看到的畫面是否正確」。同一段程式碼邏輯可能 unit test 通過（回傳值正確）但 screen state test 失敗（畫面沒顯示對應狀態），因為 UI 層的 binding 有問題。

## 三層對照

| 維度     | Unit Test                  | Protocol Integration Test      | Screen State Test            |
| -------- | -------------------------- | ------------------------------ | ---------------------------- |
| 驗證對象 | 程式碼邏輯                 | 程式碼與真實服務的協議互動     | 使用者可見的畫面狀態         |
| 外部依賴 | 全部 mock                  | 對真實服務實例                 | 視實作而定                   |
| 斷言標的 | 回傳值、狀態變化、例外拋出 | 連線結果、回應內容、逾時行為   | 畫面元素、狀態轉換、可操作性 |
| 能抓到   | 邏輯錯誤、邊界條件、狀態機 | 協議不相容、認證缺失、編碼錯誤 | 狀態遺漏、轉換缺失、顯示錯誤 |
| 抓不到   | 協議層行為、環境差異       | UI 層 binding、畫面狀態完整性  | 內部邏輯錯誤、效能問題       |

## 數量與覆蓋率的關係

測試數量和測試覆蓋率是兩個獨立的維度。192 個 unit test 提供的是 unit test 層的覆蓋率 — 程式碼邏輯的分支覆蓋。把 unit test 從 192 個加到 500 個，增加的仍然是同一層的覆蓋率，不會跨越到協議層或畫面層。

層級缺失的問題無法用數量解決。如果整個 test suite 只有 unit test，即使覆蓋率 100%，protocol integration test 層和 screen state test 層的覆蓋率仍然是 0%。app_tunnel 的經驗是：在 unit test 層加更多 test 不會讓 frame type 問題浮現，因為 `FakeWebSocketChannel` 的行為在每一個 test 中都是一致的 — 一致地遮蔽了協議層差異。

## 下一步路由

- Mock 如何在 API 層和協議層之間製造盲區 → [Mock 遮蔽機制分析](/testing/01-test-strategy-layers/mock-masking-mechanism/)
- 如何辨認「名義 integration test」 → [名義 integration test 的識別與修正](/testing/01-test-strategy-layers/nominal-integration-test/)
- 判斷自己的服務是否需要 protocol integration test → [判斷原則：什麼時候需要 protocol integration test](/testing/01-test-strategy-layers/when-protocol-integration-test/)
- 三層測試如何對應畫面狀態矩陣 → [ux-design 模組一：畫面狀態機](/ux-design/01-screen-state-machine/)
