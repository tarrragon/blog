---
title: "「名義 integration test」的識別與修正"
date: 2026-06-19
description: "test 名稱含 integration 但核心依賴全用 fake — 如何辨認、為什麼有害、怎麼修正命名和測試策略"
weight: 3
tags: ["testing", "integration-test", "mock", "naming", "test-design"]
---

[名義 integration test](/testing/knowledge-cards/nominal-integration-test/) 是指 test 的名稱或檔案路徑包含「integration」或「端對端」，但實際上核心外部依賴全部被 fake 替換，驗證的是內部狀態機而非真實服務互動。這類 test 的核心問題是命名造成的認知偏差：團隊以為「integration test 有寫」，實際上協議層完全沒被驗證。它們驗證的邏輯可能完全正確 — 問題在命名，不在品質。

## 辨識特徵

一個遠端終端機 app 的 `connection_flow_test.dart` 是具體案例。檔名標題是端對端整合測試，但內部使用了三個核心替身：`FakeWebSocketChannel`、`FakeBiometricService`、`InMemoryCredentialRepository`（[T.C2](/testing/cases/auth-handshake-missing-mock-blindspot/)）。

名義 integration test 有三個共同特徵可用來辨識。

### 特徵一：核心外部依賴全替換

Integration test 的價值在於驗證程式碼與外部系統的互動邊界。如果所有外部依賴都被 fake 取代，test 驗證的實際上是「假設外部系統行為符合開發者預期，內部邏輯是否正確」。這和 unit test 的差別只在 scope 大小 — 多個內部元件一起測 — 不在驗證對象的本質。

判斷方式：列出 test 的所有依賴注入點，計算有多少外部服務被替換成 fake。如果 100% 的外部依賴都是 fake，這個 test 不驗證任何真實互動。

### 特徵二：沒有真實的 I/O 操作

真正的 integration test 會產生真實的網路連線、讀寫真實的檔案、或呼叫真實的 API endpoint。名義 integration test 的所有 I/O 都在 process 內部完成 — `StreamController` 替代網路 stream，`Map<String, String>` 替代資料庫，`Future.value()` 替代非同步 I/O。

這些替身讓 test 執行速度快、結果穩定，但代價是完全跳過了 I/O 邊界上的所有行為差異。

### 特徵三：沒有環境前置條件

真正的 integration test 需要外部環境準備：啟動服務、建立連線、準備測試資料。名義 integration test 的 `setUp()` 只建立 fake 物件，不啟動任何外部程序，不需要網路，可以在任何環境下執行。

環境前置條件的缺席是一個實用的快速判斷訊號。如果 `setUp()` 裡沒有 `docker compose up`、`Process.start`、`HttpClient.connect` 之類的操作，這個 test 很可能不接觸真實外部服務。

## 名義 integration test 造成的認知偏差

名義 integration test 的技術問題可以修正（改名或補寫真實 integration test），但它造成的認知偏差更難修正。

當團隊看到 test suite 包含「integration test」資料夾且全部通過，決策者的推論是「integration 已經驗證過了」。這個推論在名義 integration test 下是錯的 — 協議層和環境層完全沒被驗證 — 但決策者沒有動機去檢查 test 的內部實作。

該 app 的 11 個 `connection_flow_test` 全過，開發者合理認為「連線流程的整合測試已通過」。實際上這 11 個 test 驗證的是 `ConnectionManager` 的內部狀態機在各種情境下的轉換正確性（斷線重連、錯誤處理、狀態回報），不是「和 ttyd 的連線流程是否正確」。Auth handshake 缺失直到實機測試才被發現。

## 修正策略

### 修正命名

最低成本的修正是讓 test 名稱反映真實驗證對象。命名改動不影響 test 本身的價值 — 這些 test 驗證內部狀態機的邏輯仍然有用 — 只是消除命名造成的認知偏差。

| 原名稱               | 修正後名稱                    | 理由                                     |
| -------------------- | ----------------------------- | ---------------------------------------- |
| connection_flow_test | connection_state_machine_test | 測的是狀態機邏輯，不是真實連線流程       |
| 端對端整合測試       | 狀態機分支覆蓋                | 測的是分支覆蓋，不是端對端               |
| integration_test/    | state_machine_test/           | 資料夾名稱影響團隊對 test 覆蓋範圍的認知 |

### 補寫真實 integration test

命名修正只消除誤解，不補上缺失的驗證層。如果服務的協議互動是關鍵路徑（連線、認證、資料交換），需要補寫對真實服務的 protocol integration test。

補寫的判斷原則不在本章展開 — 見 [判斷原則：什麼時候需要 protocol integration test](/testing/01-test-strategy-layers/when-protocol-integration-test/)。

### 在 test 檔案內標明依賴替換清單

在 test 檔案的頂部註釋中列出所有被 fake 取代的依賴，讓後續讀者不需要逐行追蹤就能判斷這個 test 的驗證邊界。

```dart
// Faked dependencies: WebSocketChannel, BiometricService, CredentialRepository
// Verifies: ConnectionManager state machine transitions
// Does NOT verify: real WS protocol, auth handshake, biometric hardware
```

## 下一步路由

- 判斷是否需要補寫真實 integration test → [判斷原則：什麼時候需要 protocol integration test](/testing/01-test-strategy-layers/when-protocol-integration-test/)
- Mock 遮蔽機制的完整分析 → [Mock 遮蔽機制分析](/testing/01-test-strategy-layers/mock-masking-mechanism/)
- 想建 protocol integration test → [模組三：協議整合測試](/testing/03-protocol-integration-test/)
