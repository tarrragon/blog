---
title: "Biometric fallback 完整設計"
date: 2026-06-19
description: "iOS Face ID / Touch ID 和 Android BiometricPrompt 的行為差異、fallback 策略、安全 vs 可用性取捨的顯式記錄方法"
weight: 2
tags: ["ux-design", "biometric", "authentication", "fallback", "ios", "android"]
---

Biometric gate 的 fallback 設計需要理解兩件事：平台的認證 API 在不同情境下的行為差異，以及安全收益和可用性代價之間的顯式取捨。

## 生物辨識失敗的情境

生物辨識失敗有多種原因，每種原因對使用者的影響和合理的 fallback 不同。

### 暫時性失敗

Face ID 因光線不足辨識失敗、指紋因手指潮濕讀取失敗。使用者的生物特徵正常，只是當次辨識條件不佳。重試可能成功。

### 持續性失敗

使用者戴口罩讓 Face ID 無法辨識（較舊的 iOS 版本）、手指受傷影響指紋辨識。生物特徵暫時改變，短期內重試都不會成功。需要替代認證方式。

### 硬體不可用

裝置沒有 Face ID / Touch ID 模組（較舊機型）、模擬器不支援生物辨識、生物辨識功能被裝置管理策略（MDM）禁用。需要替代認證方式。

### 使用者未設定

裝置有硬體但使用者沒有設定 Face ID 或指紋。系統的 `canCheckBiometrics` 回傳 `true`（硬體存在）但實際認證會失敗。需要引導使用者設定或提供替代認證。

## iOS 和 Android 的行為差異

### iOS（LocalAuthentication）

iOS 的 `LAContext.evaluatePolicy` 有兩個 policy：

- `deviceOwnerAuthenticationWithBiometrics`：只接受生物辨識，失敗後不自動提示密碼
- `deviceOwnerAuthentication`：先嘗試生物辨識，失敗後系統自動彈出裝置密碼輸入

Flutter 的 `local_auth` 套件的 `biometricOnly` 參數對應這兩個 policy。`biometricOnly: true` 用前者，`biometricOnly: false` 用後者。

iOS 的行為特點：系統控制認證 UI（不是 app 自行繪製），認證失敗次數過多會自動鎖定（需要輸入密碼解鎖），Face ID 多次失敗後系統會自動提供密碼選項（即使 app 要求 biometricOnly）。

### Android（BiometricPrompt）

Android 的 BiometricPrompt 分成三個 class：

- `BIOMETRIC_STRONG`：只接受 Class 3 生物辨識（經過硬體安全模組驗證的指紋/面部）
- `BIOMETRIC_WEAK`：接受 Class 2 和 Class 3 生物辨識
- `DEVICE_CREDENTIAL`：接受裝置 PIN/圖形/密碼

三個 class 可以用 `|` 組合。`BIOMETRIC_STRONG | DEVICE_CREDENTIAL` 表示先嘗試強生物辨識，失敗後 fallback 到裝置密碼。

Android 的行為特點：不同廠商的生物辨識品質差異大（Samsung 的面部辨識和 Pixel 的面部辨識安全等級不同）、部分裝置的指紋感測器在螢幕下方（使用者可能不知道在哪裡觸碰）。

## 安全 vs 可用性的顯式取捨

`biometricOnly` 的決策涉及安全和可用性的取捨。這個取捨應該在功能規格中顯式記錄，讓後續的 code review 和維護者能理解決策的背景。

記錄格式建議：

```text
Gate: biometric authentication
Decision: biometricOnly = false (allow device credential fallback)
Security trade-off: device credential (PIN/password) is weaker than biometric
Rationale: self-hosted tool, user = owner, availability > auth strength
Risk accepted: someone with device PIN can access the app
```

app_tunnel 選擇 `biometricOnly: true` 的原始意圖是「安全性更高」，但沒有顯式記錄取捨，也沒有評估「Face ID 不可用時使用者完全無法使用 app」的代價。自用工具的使用者就是 owner，密碼 fallback 的安全風險遠低於完全無法使用的可用性風險（[U.C2](/ux-design/cases/biometric-only-no-fallback/)）。

## 下一步路由

- Gate 設計的通用方法論 → [Gate 分類與三問設計法](/ux-design/02-gate-fallback/gate-three-questions/)
- 開發環境遮蔽 gate 問題 → [開發環境 vs 真機的 gate 行為差異表](/ux-design/02-gate-fallback/dev-vs-real-gate-behavior/)
- 安全 vs 可用性在 monitoring 中的對應 → [monitoring 模組七 資安](/monitoring/07-security-privacy/)
