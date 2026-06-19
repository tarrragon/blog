---
title: "開發環境 vs 真機的 gate 行為差異表"
date: 2026-06-19
description: "模擬器、debug build、test 環境中的 gate 行為和真機 release build 不同 — 差異表讓開發者在上機前知道哪些 gate 還沒被真實驗證"
weight: 5
tags: ["ux-design", "gate", "simulator", "testing", "development-environment"]
---

開發環境遮蔽 gate 問題的機制是：模擬器或 debug build 中的 gate 行為比真機寬鬆，讓問題在開發階段不可見，直到實機測試或 production 才浮現。這和 mock 遮蔽 protocol 問題的機制結構相同（[testing 模組一](/testing/01-test-strategy-layers/)）— 開發環境的「寬鬆模式」讓功能缺失變得不可見。

## 差異機制

### 模擬器不支援硬體功能

iOS 模擬器不支援 Face ID / Touch ID 硬體。`local_auth` 的 `isAvailable()` 在模擬器上回傳 `false`（`isDeviceSupported()` 為 `true` 但 `getAvailableBiometrics()` 為空），app 跳過認證走預設路徑。

在真機上 `isAvailable()` 回傳 `true`，app 嘗試認證，如果設定了 `biometricOnly: true` 且 Face ID 失敗，使用者被擋住。模擬器上「跳過認證直接使用」的體驗讓開發者以為認證流程沒有問題（[U.C2](/ux-design/cases/biometric-only-no-fallback/)）。

### Debug build 的權限行為不同

某些平台在 debug build 和 release build 的權限處理不同。例如 Android 的某些 OEM 客製化系統在 debug mode 下自動授予特定權限，release mode 下需要手動授權。

### Test 環境跳過 gate

Unit test 和 integration test 通常 mock 掉所有 gate — `FakeBiometricService` 永遠回傳成功，`FakeNetworkChecker` 永遠回傳已連線。這和名義 integration test 的問題相同 — test 環境的「一切正常」遮蔽了真實環境的 gate 失敗場景。

## Gate 行為差異表

在功能規格中建立一張差異表，列出每個 gate 在不同環境下的行為差異：

| Gate         | 模擬器行為            | 真機 debug       | 真機 release    | 風險                              |
| ------------ | --------------------- | ---------------- | --------------- | --------------------------------- |
| 生物辨識     | 跳過（硬體不可用）    | 可測試（需設定） | 正常            | 模擬器上看不到 fallback 缺失      |
| 網路連線     | 通常正常（host 網路） | 可斷 WiFi 測試   | 行動網路 + WiFi | 模擬器的網路狀態不代表行動網路    |
| 相機權限     | 無相機（或虛擬相機）  | 可測試           | 正常            | 模擬器無法測試真實權限流程        |
| 藍牙         | 不支援                | 可測試           | 正常            | 模擬器完全跳過藍牙相關功能        |
| Push 通知    | 不支援（iOS 模擬器）  | 可測試           | 正常            | 通知觸發的導航路徑在模擬器不可測  |
| App 簽名驗證 | debug 簽名自動通過    | debug 簽名       | release 簽名    | 簽名相關的 gate 只在 release 生效 |

## 差異表的使用方式

### 開發階段

開發者對照差異表，意識到哪些 gate 在當前環境下沒有被真實驗證。差異表中「模擬器行為」和「真機 release」不同的行 = 需要上真機確認的項目。

### 實機測試規劃

測試計畫中針對差異表的每一行設計測試案例。生物辨識的測試案例必須涵蓋「Face ID 失敗時的 fallback」，網路連線的測試案例必須涵蓋「飛航模式下的 UX」。

### Code review

Review 涉及 gate 的程式碼時，對照差異表確認 fallback 路徑是否存在。如果 review 的程式碼用了 `biometricOnly: true`，差異表立刻提示「模擬器上看不到這個問題，需要上真機確認 fallback」。

差異表揭露的問題和 testing 領域的 mock 遮蔽在結構上相同 — [testing 模組一 Mock 遮蔽機制](/testing/01-test-strategy-layers/mock-masking-mechanism/)從 API 層 vs 協議層的角度分析同一類問題。差異表本身是[三問設計法](/ux-design/02-gate-fallback/gate-three-questions/)在實機驗證階段的延伸，biometric gate 的完整 fallback 設計見 [Biometric fallback 完整設計](/ux-design/02-gate-fallback/biometric-fallback-design/)。
