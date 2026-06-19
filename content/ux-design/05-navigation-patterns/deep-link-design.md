---
title: "Deep link 設計"
date: 2026-06-19
description: "URL scheme / Universal Link / App Link — deep link 讓外部來源直接導航到 app 的特定畫面"
weight: 4
tags: ["ux-design", "navigation", "deep-link", "universal-link", "app-link"]
---

Deep link 讓 app 外部的來源（網頁連結、推播通知、其他 app）直接導航到 app 的特定畫面，而非每次都從首頁開始。Deep link 的設計需要考慮三個問題：URL 結構如何對應到畫面、app 未安裝時怎麼處理、導航堆疊如何重建。

## 三種 deep link 機制

### Custom URL scheme

App 註冊自訂的 URL scheme（`myapp://`），系統收到這個 scheme 的 URL 時打開 app。`myapp://terminal?host=192.168.1.100` 打開 app 的 terminal 畫面。

Custom URL scheme 的限制：沒有 ownership 驗證（任何 app 都可以註冊 `myapp://`），只在 app 已安裝時有效（未安裝時 URL 無效），不適合 web 分享（瀏覽器無法開啟 `myapp://`）。

### Universal Link（iOS）/ App Link（Android）

App 宣告擁有特定 domain 的 URL（`https://example.com/terminal`）。系統驗證 domain 的 ownership（domain 上放 `.well-known/apple-app-site-association` 或 `assetlinks.json`），驗證通過後這些 URL 直接在 app 中打開。

優勢：使用標準 HTTPS URL（可以在瀏覽器中分享）、有 ownership 驗證（防止冒充）、app 未安裝時 fallback 到網頁。

### Deferred deep link

使用者點擊 deep link 時 app 未安裝。系統引導使用者到 app store 安裝，安裝後首次開啟時自動導航到 deep link 指定的畫面。

Deferred deep link 需要第三方服務（Firebase Dynamic Links、Branch）或自建機制在安裝前後傳遞 URL 參數。

## URL 結構設計

Deep link 的 URL 結構應該和 GoRouter 的路由定義一致。GoRouter 原生支援 deep link — URL path 就是路由 path。

```text
https://example.com/terminal        → TerminalScreen
https://example.com/enrollment      → EnrollmentScreen
https://example.com/terminal?host=x → TerminalScreen(host: x)
```

URL 參數（query parameters）傳遞畫面需要的資料。參數值避免包含敏感資訊 — URL 可能被系統日誌、分析工具、中間人記錄。

## 導航堆疊重建

使用者從 deep link 直接進入 `/terminal` 畫面時，導航堆疊中沒有首頁。使用者按 back 應該回到首頁還是離開 app？

### 重建完整堆疊

GoRouter 的 `go('/terminal')` 可以設定為自動把前置路由放入堆疊。使用者按 back 回到首頁，再按 back 離開 app。使用者的心理模型是「deep link 帶我到這個畫面，back 帶我到 app 的正常入口」。

### 只放 deep link 目標

堆疊中只有 deep link 目標畫面。按 back 離開 app。適合「一次性操作」的 deep link（打開 → 操作 → 離開）。

### 選擇策略

如果 deep link 的畫面是 app 日常使用的一部分，重建完整堆疊讓使用者能繼續在 app 中操作。如果 deep link 是從外部觸發的獨立操作（掃描 QR code → 顯示結果），只放目標畫面更簡潔。

## Deep link 測試

Deep link 需要端對端測試 — 從外部觸發 URL，驗證 app 導航到正確畫面。

測試項目：

- 每個路由的 deep link 能正確打開
- URL 參數正確傳遞到畫面
- App 在前景、背景、未啟動三種狀態下都能處理 deep link
- 無效的 deep link URL 有合理的 fallback（導航到首頁或顯示錯誤）
- Universal Link 的 domain verification 正確

Deep link 的實作在 Flutter 中由 GoRouter 的 route matching 處理 — [Flutter GoRouter 導航設計](/ux-design/05-navigation-patterns/flutter-gorouter/)包含 deep link 的設定方式。Deep link 觸發的導航操作（go vs push）影響使用者的返回路徑，語意差異見 [go vs push vs pushReplacement 語意表](/ux-design/05-navigation-patterns/go-push-semantics/)。Deep link 的端對端驗證在 [testing 模組四 自動化 UI 驗證](/testing/04-ui-automation/)中歸類到導航路徑 test。
