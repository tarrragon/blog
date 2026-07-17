---
title: "Gate 分類與三問設計法"
date: 2026-06-19
description: "每個 gate 設計時問三個問題：成功時做什麼、失敗時做什麼、使用者不知道發生什麼時做什麼"
weight: 1
tags: ["ux-design", "gate", "fallback", "design", "authentication"]
---

[Gate](/ux-design/knowledge-cards/gate/) 是使用者操作流程中的「必須通過才能繼續」的關卡。生物辨識認證、網路連線檢查、權限請求、版本檢查 — 這些都是 gate。Gate 設計的核心責任是確保使用者在每種結果下都有路可走，而非只設計「通過」的情境。

## 三問設計法

每個 gate 設計時回答三個問題：

### 成功時做什麼

Gate 通過後使用者進入下一步。這是最直覺的設計 — 認證成功進入主畫面、網路連線成功開始載入資料、權限授予後啟用功能。

成功路徑通常是設計時最先考慮的，也是最不容易遺漏的。

### 失敗時做什麼

Gate 未通過時使用者的[替代路徑](/ux-design/knowledge-cards/ux-fallback/)。替代路徑可以是：降級功能（部分功能可用）、替代驗證方式（密碼代替 Face ID）、手動重試（重試按鈕）、放棄操作（返回上一頁）。

失敗路徑是最容易遺漏的。一個自用遠端終端機 app 的 biometric gate 設定 `biometricOnly: true`，Face ID 不可用時使用者直接被擋住，沒有密碼 fallback、沒有跳過選項、沒有返回路徑（[U.C2](/ux-design/cases/biometric-only-no-fallback/)）。修復只改一個 boolean — `biometricOnly: false` — 讓系統自動提示輸入裝置密碼。但這個決策應該在企劃階段做，而非實機測試時才發現。

### 使用者不知道發生什麼時做什麼

Gate 處理中（loading）或結果不確定（timeout）時使用者看到什麼、能做什麼。

使用者不知道發生什麼的情境包括：認證彈窗尚未出現（系統延遲）、網路請求已發但未回應（loading）、權限對話框被系統遮擋（多個 dialog 堆疊）。

在這個狀態下使用者需要的是：知道系統在做什麼（loading 指示）、可以取消等待（取消按鈕）、超過合理時間後有提示（timeout 訊息 + 重試選項）。loading 指示該在等多久後出現、timeout 該設多久，判準在[時間感知與回應策略](/ux-design/06-interaction-feedback/response-time-strategy/)與[互動回饋三層模型](/ux-design/06-interaction-feedback/feedback-three-layers/)的畫面級 timeout 段。

## Gate 的常見類型

### 認證 Gate

使用者必須驗證身份才能使用功能。生物辨識、密碼、PIN 碼、OAuth 登入。

認證 gate 的 fallback 設計取決於安全需求和使用場景。銀行 app 可能要求生物辨識 + PIN 碼雙重驗證，沒有更低層級的 fallback。自用工具可以接受密碼 fallback，因為使用者本身就是 owner — 可用性優先於認證強度（[U.C2](/ux-design/cases/biometric-only-no-fallback/)）。

### 網路 Gate

功能需要網路連線才能運作。連線存在但不穩定的場景比完全離線更難處理 — 請求可能成功、可能逾時、可能部分成功。

### 權限 Gate

App 需要系統權限（相機、位置、通知）才能使用特定功能。

權限 gate 的特殊性在於使用者可以永久拒絕。拒絕後再次請求不會彈出系統對話框 — 必須引導使用者到系統設定手動開啟。

### 環境 Gate

特定的硬體或軟體條件必須滿足。最低 OS 版本、特定感測器（NFC、深度相機）、特定連接（藍牙已開啟）。

環境 gate 的 fallback 通常有限 — 硬體不存在時無法用軟體模擬。但至少應該告知使用者為什麼功能不可用，而非靜默禁用。

### 破壞性操作確認 Gate

操作的破壞半徑大於使用者直覺預期時（不可逆、覆蓋既有資料），在執行前攔一道確認。這類 gate 的觸發條件不是身分或環境，是操作語意：「匯入」聽起來是加法、實際語意可能是取代 — 語意與直覺預期的落差越大，越需要確認。確認 UI 要描述具體後果（「將清空現有 N 本書」），不只問「確定嗎」。

三問中的「使用者不知道發生什麼」在這類 gate 有一個特化：要涵蓋**確認機制本身故障**的情況。確認元件沒渲染、事件沒綁上時，系統要選一個預設方向 — 安全預設是視為未確認、不執行破壞（倒向不可逆性低的那邊：不清空可以重試、清空無法還原）。一個 Chrome extension 的匯入功能在覆蓋模式下語意是「取代現有書庫」，該模式匯入空檔前彈出描述後果的確認 Modal，且確認元件 DOM 缺失時一律視為未確認、預設不清空（[U.C12](/ux-design/cases/destructive-import-fail-safe-confirm/)，正面案例）。

### 其他常見 Gate

商業 app 還有兩種 gate 在本系列涵蓋範圍之外但實務常見：

**付費 Gate**（paywall）：功能需要付費才能使用。付費 gate 的 fallback 設計和上述四種不同 — 「失敗」路徑的目標是引導使用者付費而非提供替代功能。試用期、降級功能、付費引導 vs 付費強制的取捨依賴商業模式決策。

**版本相容性 Gate**：API 版本過舊需要升級 app。Fallback 是提示使用者更新，但強制更新會阻擋無法更新的使用者（舊 OS 版本不支援新版 app）。

## Gate 設計表

把三問設計法應用到每個 gate，產出一張設計表：

| Gate     | 成功         | 失敗                | 不確定              |
| -------- | ------------ | ------------------- | ------------------- |
| 生物辨識 | 進入主畫面   | 提示輸入裝置密碼    | 顯示「驗證中」      |
| 網路連線 | 開始載入資料 | 顯示離線提示 + 重試 | 顯示 loading + 取消 |
| 相機權限 | 開啟掃描功能 | 說明原因 + 設定連結 | 等待系統對話框      |
| 藍牙     | 開始裝置搜尋 | 提示開啟藍牙 + 連結 | 顯示搜尋中 + 取消   |

失敗欄和不確定欄為空的 gate 就是 UX 死胡同的候選 — 和[畫面狀態矩陣](/ux-design/01-screen-state-machine/state-matrix-definition/)的退出路徑檢查同樣的邏輯。

三問設計法的具體應用在 [Biometric fallback 完整設計](/ux-design/02-gate-fallback/biometric-fallback-design/)中以生物辨識 gate 為例展開。Gate 在開發環境的行為可能和真機不同，[開發環境 vs 真機的 gate 行為差異表](/ux-design/02-gate-fallback/dev-vs-real-gate-behavior/)列出每個 gate 在模擬器和真機上的差異。Gate 設計表的「失敗」欄和[畫面狀態矩陣](/ux-design/01-screen-state-machine/)的「退出路徑」欄是同一個問題在不同層級的表達。
