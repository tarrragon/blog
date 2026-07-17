---
title: "UX 設計案例庫"
date: 2026-06-19
description: "畫面狀態機缺口、導航死胡同、Gate fallback 缺失、輸入機制遺漏的實戰案例"
weight: 90
tags: ["ux-design", "case-study"]
---

這個資料夾收錄 UX 設計的實戰案例 — 重點不在「畫面怎麼設計」，而在「設計方法的哪個步驟遺漏了什麼」。每個案例記錄一個真實的 UX 缺口、分析企劃階段的遺漏機制、提出系統性的預防方法。

案例來源分兩類：

- **自有案例**：app_tunnel、book_overview_app（Flutter mobile）與 book_overview_v1（Chrome extension）專案的實機測試教訓（first-party，有完整程式碼和 commit 歷史）
- **外部案例**：iOS/Android 設計指南中的反模式和社群討論（third-party，引用公開來源）

U.C1-C8 來自 mobile app、U.C9-C14 來自 Chrome extension — 兩類 surface 的失敗模式互補：mobile 案例集中在狀態機退出路徑、觸控與輸入機制；extension 案例集中在多 context 的回饋鏈路可靠性、查詢對象生命週期、完成判定誠實度與跨 app 邊界的路由辨識。

## 案例覆蓋缺口

| 章節                   | 缺口                                         | 備註                                        |
| ---------------------- | -------------------------------------------- | ------------------------------------------- |
| 模組三（輸入機制設計） | mobile CLI app 的鍵盤設計案例                | 小眾需求，公開案例稀少                      |
| 模組五（導航模式）     | GoRouter vs Navigator 2.0 的導航 UX 差異案例 | Flutter 社群有討論但少系統化                |
| 模組六（互動回饋）     | web 桌面端 hover / focus 專屬的回饋案例      | extension 案例未涉及；候選源是 web app 專案 |

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
| [U.C9](/ux-design/cases/async-listener-false-failure/)             | 提取成功卻誤報失敗                 | book_overview_v1  | 模組六    | 結果通知鏈路被搶通道（誠實度反轉）         |
| [U.C10](/ux-design/cases/service-worker-cold-start-false-offline/) | Service Worker 冷啟動假離線        | book_overview_v1  | 模組一    | initializing 狀態未建模                    |
| [U.C11](/ux-design/cases/lazy-load-premature-completion/)          | 抓到 96/928 本就顯示完成           | book_overview_v1  | 模組六    | 完成判定的證據強度不足                     |
| [U.C12](/ux-design/cases/destructive-import-fail-safe-confirm/)    | 匯入清空書庫的確認與安全預設       | book_overview_v1  | 模組二    | 破壞性操作 gate（正面案例）                |
| [U.C13](/ux-design/cases/import-error-reload-extension-mismatch/)  | 匯入錯誤配重載擴充功能按鈕         | book_overview_v1  | 模組四    | 錯誤行動與層級不對位                       |
| [U.C14](/ux-design/cases/hash-spa-route-label-loss/)               | hash SPA 的 pathname 永遠是根路徑  | book_overview_v1  | 模組五    | 路由辨識遺漏 fragment                      |
