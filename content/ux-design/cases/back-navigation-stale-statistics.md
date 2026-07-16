---
title: "U.C6 加書後返回不刷新統計 — 只設計了進入時載入"
date: 2026-07-16
description: "Flutter app 資料管理頁的書籍統計只在 initState 載入一次，從頁面進入新增流程加書後 pop 返回，統計停留在舊值（仍顯示無書目），要回首頁再進入才更新。根因是 happy-path-only 反模式的資料版本：設計了「進入時載入」，沒設計「資料變更時的轉移」"
weight: 6
tags: ["ux-design", "case-study", "state-machine", "data-refresh", "flutter", "mobile"]
---

這個案例的核心責任是說明 happy-path-only 反模式不只出現在導航流，也出現在資料流 — 畫面設計只回答「進入時顯示什麼」，沒回答「底層資料在畫面存活期間變更時，畫面如何得知」。

## 觀察

book_overview_app 的資料管理頁顯示書庫統計（書籍總數、書庫狀態）。統計只在 `initState` 的 `addPostFrameCallback` 呼叫一次 `loadData()`。

實機測試路徑：資料管理頁（顯示無書目）→ 點「搜尋加書」進入新增流程 → 成功加入一本書 → pop 返回資料管理頁。返回後統計仍顯示無書目 — Flutter 的 push/pop 導航不會 dispose/rebuild 底下頁面的 State，`initState` 不會再跑一次。使用者要退回首頁再重新進入資料管理頁，統計才更新。

| 項目         | 修復前                       | 修復後（W1-085）                                                                                      |
| ------------ | ---------------------------- | ----------------------------------------------------------------------------------------------------- |
| 統計載入時機 | 僅 `initState` 一次          | 導航返回後再載入一次                                                                                  |
| 加書後返回   | 停留舊值，需回首頁再進入     | 立即反映最新統計                                                                                      |
| 實作         | 三個導航入口各自 `pushNamed` | 三個入口收斂為 `_navigateAndRefresh` helper：`await pushNamed(...)` 完成後呼叫 `viewModel.loadData()` |

修復後規格同步新增 BR-10「衍生統計 reactive 一致性」：衍生統計必須響應底層書庫資料變更自動更新（Riverpod `ref.watch` reactive 監聽），不得依賴頁面重進或手動刷新 — 這是比 await-then-refresh 更徹底的收斂方向。

## 判讀

1. **happy-path-only 反模式的資料版本**。導航版的 happy path 是「使用者只會往前走」，資料版的 happy path 是「畫面顯示的資料在畫面存活期間不會變」。本案的畫面狀態矩陣若有填，「進入條件」欄只會有一條「首次進入時載入」— 「從子流程返回且資料已變更」這條進入條件從未被列出。

2. **「返回時畫面會自己更新」是開發者的隱性假設，且與框架事實相反**。Flutter 的 push/pop 保留底下頁面的 State，這是框架的明確行為。開發者在桌面瀏覽器思維（每次導航都重新載入）下設計行動 app 的資料流，假設與平台事實錯位。

3. **await-then-refresh 是點對點補丁，不是收斂**。修復把三個導航入口包進 `_navigateAndRefresh`，解了當下的三個入口 — 但第 N+1 個新入口忘記包 helper 就重演一次。這也是規格層補 BR-10 的原因：把「統計要 reactive」聲明為業務規則，讓資料層變更自動推送到所有訂閱畫面，而不是每個導航點各自記得刷新。

## 策略

1. **每個顯示衍生資料的畫面固定一問**：「底層資料在此畫面存活期間變更時，畫面如何得知？」答不出來就是缺口。變更來源不只子流程返回，還包括背景同步、其他分頁操作。

2. **畫面狀態矩陣的進入條件欄必須列出「返回/恢復」**：「首次進入」和「從子流程返回」是兩個不同的進入條件，後者攜帶「資料可能已變更」的前提。只列首次進入的矩陣就是 happy-path-only。

3. **架構層收斂優先於導航點補丁**：衍生統計宣告為 reactive 依賴（`ref.watch` 監聽資料層）讓「畫面反映最新資料」成為架構性質而非每個入口的手動責任。過渡期可用 await-then-refresh 止血，但要在規格留下收斂方向（本案的 BR-10），否則補丁會被誤認為終態。

## 下一步路由

- happy-path-only 反模式的完整定義 → [反模式：只設計 happy path](/ux-design/01-screen-state-machine/anti-pattern-happy-path-only/)
- 想用狀態矩陣盤點進入條件 → [畫面狀態矩陣的定義與填寫方法](/ux-design/01-screen-state-machine/state-matrix-definition/)
- 類似案例（狀態矩陣缺口）→ [U.C1 五狀態零退出](/ux-design/cases/five-states-zero-exits/)
