---
title: "U.C14 hash SPA 的 pathname 永遠是根路徑 — 路由辨識遺漏 fragment"
date: 2026-07-17
description: "依 URL 判斷「目前在哪一頁」的功能對 hash-based SPA 失效時使用。web 路由有 path-based 與 hash-based 兩套慣例，跨 app 讀取對方 URL 時對方的路由形態是輸入規格的一部分"
weight: 14
tags: ["ux-design", "case-study", "navigation", "chrome-extension", "web", "spa", "routing"]
---

這個案例的核心責任是說明 web 路由辨識的一個系統性盲點：hash-based SPA 的頁面資訊在 URL fragment 裡，只讀 pathname 的辨識邏輯會把所有頁面都判成根路徑 — 讀取的是別人的 app 時，對方用哪套路由慣例不由你決定。

## 觀察

電子書庫總覽 Chrome 擴充功能（book_overview_v1）的 popup 顯示「目前所在的目標網站頁面」標籤。目標平台 Readmoo 是 hash-based SPA — 書庫頁的 URL 是 `read.readmoo.com/#/library`，路由資訊在 `#` 之後。popup 用 `URL.pathname` 取頁面路徑，pathname 永遠是 `/`，所有頁面都被顯示成根路徑、無法辨識使用者目前在哪一頁（commit `a27de860e`）。

修復：改用 `pathname + hash` 組合顯示；補三類 URL 的解析測試（hash SPA `/#/library`、根路徑 `/`、傳統 path `/account`）；並掃描全 codebase 確認 pathname-only 邏輯只影響顯示標籤、無 functional 用途。

## 判讀

1. **web 路由有兩套並存的慣例**。path-based（`/library`、伺服器路由或 History API）與 hash-based（`/#/library`、fragment 路由）。「目前在哪頁」的判斷邏輯只支援其中一套時，另一套的所有頁面都會塌縮成同一個值 — 塌縮是靜默的，pathname 讀 hash SPA 不會報錯、只會永遠回傳 `/`。

2. **跨 app 邊界讀 URL 時，對方的路由慣例是輸入規格**。擴充功能、爬蟲、分析工具讀取宿主頁面的 URL — 宿主用哪套路由不受讀取方控制、還會隨對方改版變動。辨識邏輯要把「對方是哪種路由形態」當成必須確認的規格項，不能假設「URL 的頁面資訊都在 path」。

3. **顯示層的錯位是低嚴重度、但同一邏輯的 functional 用途是高嚴重度**。這個案例只影響標籤顯示；同樣的 pathname-only 邏輯若用於「判斷是否在可提取頁面」，會讓功能在所有頁面都誤判。修復時的全 codebase 掃描（確認無 functional 用途）就是在排除這個升級風險。

## 策略

1. **依 URL 辨識頁面的功能，列出目標的路由形態**：path-based / hash-based / 混合，測試各涵蓋一組 URL。

2. **取「完整路由」用 pathname + hash 組合**，只在確認目標是純 path-based 時才省略 fragment。

3. **發現一處路由辨識錯誤時，掃描同 pattern 的所有用途** — 顯示用途與 functional 用途的嚴重度不同，修復範圍要以掃描結果為準、不是以回報的症狀為準。

## 下一步路由

- Deep link 的 URL 結構設計 → [Deep link 設計](/ux-design/05-navigation-patterns/deep-link-design/)
- 導航模式與宣告式路由 → [Mobile 導航模式分類](/ux-design/05-navigation-patterns/mobile-navigation-taxonomy/)
- 類似案例（外部頁面結構是輸入規格 — 提取器對 lazy-load 的假設）→ [U.C11 抓到 96/928 本就顯示完成](/ux-design/cases/lazy-load-premature-completion/)
