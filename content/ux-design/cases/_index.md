---
title: "UX 設計案例庫"
date: 2026-06-19
description: "畫面狀態機缺口、導航死胡同、Gate fallback 缺失、輸入機制遺漏的實戰案例"
weight: 90
tags: ["ux-design", "case-study"]
---

這個資料夾收錄 UX 設計的實戰案例 — 重點不在「畫面怎麼設計」，而在「設計方法的哪個步驟遺漏了什麼」。每個案例記錄一個真實的 UX 缺口、分析企劃階段的遺漏機制、提出系統性的預防方法。

案例來源分兩類：

- **自有案例**：app_tunnel 與 book_overview_app 專案的實機測試教訓（first-party，有完整程式碼和 commit 歷史）
- **外部案例**：iOS/Android 設計指南中的反模式和社群討論（third-party，引用公開來源）

## 案例覆蓋缺口

| 章節                   | 缺口                                         | 備註                         |
| ---------------------- | -------------------------------------------- | ---------------------------- |
| 模組三（輸入機制設計） | mobile CLI app 的鍵盤設計案例                | 小眾需求，公開案例稀少       |
| 模組五（導航模式）     | GoRouter vs Navigator 2.0 的導航 UX 差異案例 | Flutter 社群有討論但少系統化 |

## 案例列表

| 案例                                                               | 主題                               | 來源              | 模組      | 缺口類型                                   |
| ------------------------------------------------------------------ | ---------------------------------- | ----------------- | --------- | ------------------------------------------ |
| [U.C1](/ux-design/cases/five-states-zero-exits/)                   | 五個狀態零個退出路徑               | app_tunnel        | 模組一    | 狀態機退出路徑未設計                       |
| [U.C2](/ux-design/cases/biometric-only-no-fallback/)               | biometricOnly=true 無密碼 fallback | app_tunnel        | 模組二    | Gate 無 fallback                           |
| [U.C3](/ux-design/cases/terminal-input-mechanism-absent/)          | 終端機文字輸入機制未設計           | app_tunnel        | 模組三    | 輸入機制是事後 hotfix                      |
| [U.C4](/ux-design/cases/missing-enrollment-entry-point/)           | 首頁缺配對入口按鈕                 | app_tunnel        | 模組一    | 導航流未完整列出                           |
| [U.C5](/ux-design/cases/export-button-zero-feedback/)              | 匯出按鈕按下零回饋                 | book_overview_app | 模組六    | 三層回饋全缺（UI 未接線）                  |
| [U.C6](/ux-design/cases/back-navigation-stale-statistics/)         | 加書後返回不刷新統計               | book_overview_app | 模組一    | 只設計進入時載入（happy-path-only 資料版） |
| [U.C7](/ux-design/cases/misleading-no-result-for-product-barcode/) | 商品條碼的誤導性查無結果           | book_overview_app | 模組三/六 | 輸入驗證未前移、錯誤訊息誤導               |
| [U.C8](/ux-design/cases/tag-row-touch-target-scope/)               | 標籤行只有箭頭可點                 | book_overview_app | 模組六    | 觸控目標小於視覺單元                       |
