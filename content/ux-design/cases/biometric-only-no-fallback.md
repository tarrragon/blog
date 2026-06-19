---
title: "U.C2 biometricOnly=true 無密碼 fallback"
date: 2026-06-19
description: "Flutter app 的生物辨識設定 biometricOnly: true 阻擋所有非生物辨識認證方式 — Face ID 不可用時使用者直接被擋住，沒有替代路徑"
weight: 2
tags: ["ux-design", "case-study", "authentication", "biometric", "gate-fallback", "flutter"]
---

這個案例的核心責任是說明 Gate（使用者必須通過的關卡）的設計不只是「成功時怎麼做」，還必須包含「失敗時的替代路徑」。

## 觀察

app_tunnel 使用 `local_auth` 套件進行生物辨識認證。`AuthenticationOptions` 設定 `biometricOnly: true`，表示只接受生物辨識（Face ID / 指紋），不接受裝置密碼作為 fallback。

```dart
// 修復前
options: const AuthenticationOptions(
  stickyAuth: true,
  biometricOnly: true,  // Face ID 不可用 → 認證直接失敗
),

// 修復後
options: const AuthenticationOptions(
  stickyAuth: true,
  biometricOnly: false, // Face ID 不可用 → 系統自動提示輸入裝置密碼
),
```

| 指標     | 值                                                                   |
| -------- | -------------------------------------------------------------------- |
| 影響範圍 | Face ID 不可用時（戴口罩、光線差、指紋模糊、模擬器）完全無法使用 app |
| 修復成本 | 改一個 boolean                                                       |
| 根因     | 企劃階段未設計 biometric gate 的 fallback                            |

## 判讀

1. **Gate fallback 是設計問題，不是實作問題**。`biometricOnly` 的預設值是 `false`（允許密碼 fallback），開發時特意改成 `true` 是因為認為「安全性更高」。但這個判斷沒有考慮 fallback 缺失時的 UX 代價 — 使用者完全無法進入 app。

2. **開發環境遮蔽了問題**。iOS 模擬器預設不支援 Face ID，但 `isAvailable()` 的實作會檢查 `isDeviceSupported()` + `getAvailableBiometrics().isNotEmpty`。模擬器回傳 `isDeviceSupported() = true` 但 `getAvailableBiometrics() = []`，所以在模擬器上 `isAvailable()` 回傳 false，直接跳過認證走預設路徑。真實裝置上 `isAvailable() = true` 但 Face ID 可能失敗，這時沒有 fallback。

3. **安全性 vs 可用性的取捨需要顯式記錄**。`biometricOnly: true` 的安全收益是「確保只有生物特徵擁有者能操作」；代價是「任何生物辨識失敗場景都阻擋使用」。自用工具的使用者就是 owner，密碼 fallback 的安全風險遠低於「完全無法使用」的可用性風險。

## 策略

1. **每個 gate 設計時列三問**：成功時做什麼？失敗時做什麼？使用者不知道發生什麼時做什麼？
2. **在狀態矩陣標注 gate fallback**：biometric / network / auth 每個 gate 旁邊標注替代路徑，空白 = 使用者被擋住。
3. **安全 vs 可用性取捨顯式記錄**：在 spec 文件記錄「`biometricOnly: false` — 接受密碼 fallback，因為自用工具可用性優先於生物辨識強制」。

## 下一步路由

- 想設計 Gate fallback 體系 → [Gate 分類與三問設計法](/ux-design/02-gate-fallback/gate-three-questions/)
- 想了解 biometric 在不同平台的行為差異 → 待補：iOS/Android biometric API 行為對照
- 類似案例（導航死胡同）→ [U.C1 五個狀態零個退出](/ux-design/cases/five-states-zero-exits/)
