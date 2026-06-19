---
title: "iOS HIG vs Material Design 導航差異"
date: 2026-06-19
description: "兩個平台在 back 行為、手勢、tab bar 位置、modal 呈現上的差異 — 跨平台 app 需要決定遵循哪套慣例"
weight: 3
tags: ["ux-design", "navigation", "ios", "android", "material-design", "hig"]
---

iOS Human Interface Guidelines（HIG）和 Material Design 對導航行為有不同的慣例。跨平台 app（Flutter、React Native）需要決定：完全遵循一套、各平台遵循各自的慣例、或混合使用。這個決策影響使用者在不同平台上的操作體驗。

## Back 行為

### iOS

iOS 沒有系統級的 back 按鈕。導航列左上角的 back 按鈕由 app 提供（`UINavigationController` 自動加入）。使用者也可以從螢幕左邊緣向右滑動觸發 back（edge swipe gesture）。

iOS 的 back 行為是 pop — 彈出堆疊頂端，回到前一個畫面。沒有 Android 的系統 back 按鈕覆寫機制。

### Android / Material Design

Android 有系統級的 back 按鈕（虛擬或實體）。Material Design 在 app bar 左上角也放 back 箭頭或 hamburger menu 圖示。

Android 的 back 行為由 app 控制（`onBackPressed`），可以被覆寫。常見的覆寫場景：在首頁按 back 詢問「是否離開 app」、在表單中按 back 詢問「是否放棄編輯」。

### 跨平台決策

Flutter 預設在 Android 上攔截系統 back 按鈕，在 iOS 上提供 back 按鈕和 edge swipe。GoRouter 的 `pop()` 在兩個平台上行為一致。

跨平台 app 需要注意的差異：iOS 使用者習慣 edge swipe back，Android 使用者習慣按系統 back 按鈕。兩者都要支援。

## Tab bar 位置

### iOS

Tab bar 固定在畫面底部。iOS 使用者期望 tab bar 永遠可見、永遠在底部。Apple 的 HIG 明確建議 tab bar 在底部。

### Material Design

Material Design 的 bottom navigation 也在底部，但額外支援 top tabs（在 app bar 下方的可滑動標籤列）。Top tabs 適合同一類內容的不同視角（全部 / 未讀 / 已標記）。

### 跨平台決策

底部 tab bar 在兩個平台上都是標準做法。Top tabs 在 iOS 上較少見（iOS 偏好用 segmented control 代替 top tabs）。跨平台 app 用底部 tab bar 是最安全的選擇。

## Modal 呈現

### iOS

iOS 的 modal 畫面從底部滑上來，覆蓋前一個畫面但不完全遮擋（iOS 13+ 的 sheet 呈現樣式可以看到前一個畫面的上緣）。Dismiss 操作是向下滑動或點擊關閉按鈕。

### Material Design

Material Design 的 bottom sheet 和 dialog 是 modal 的主要形式。Full-screen dialog 從底部滑上來，有 close 按鈕在左上角和 action 按鈕在右上角。

### 跨平台決策

Flutter 的 `showModalBottomSheet` 和 `showDialog` 在兩個平台上都可用。視覺呈現可以用 platform-adaptive widget（`CupertinoPageRoute` vs `MaterialPageRoute`）按平台切換。

## 選擇策略

| 策略                   | 適合場景                        | 代價                     |
| ---------------------- | ------------------------------- | ------------------------ |
| 統一用 Material Design | 以 Android 為主的 app、快速開發 | iOS 使用者體驗不原生     |
| 統一用 iOS HIG         | 以 iOS 為主的 app               | Android 使用者體驗不原生 |
| 各平台遵循各自慣例     | 重視兩個平台原生體驗            | 開發和測試成本翻倍       |
| 共用核心、差異點適配   | 多數跨平台 app 的實際選擇       | 需要判斷哪些差異值得適配 |

多數跨平台 app 選擇「共用核心、差異點適配」— 底部 tab bar、push/pop 導航在兩個平台上一致；back 手勢、modal 呈現按平台適配。

## 下一步路由

- Deep link 設計 → [Deep link 設計](/ux-design/05-navigation-patterns/deep-link-design/)
- go vs push 的語意差異 → [go vs push vs pushReplacement 語意表](/ux-design/05-navigation-patterns/go-push-semantics/)
- 導航模式分類 → [Mobile 導航模式分類](/ux-design/05-navigation-patterns/mobile-navigation-taxonomy/)
