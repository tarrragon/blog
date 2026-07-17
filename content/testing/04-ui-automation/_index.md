---
title: "模組四：自動化 UI 驗證"
date: 2026-06-19
description: "Widget test 的狀態覆蓋策略、Playwright 驗證流程、螢幕狀態 coverage"
weight: 4
tags: ["testing", "widget-test", "playwright", "ui-test"]
---

回答「畫面上的東西是否如設計工作」。狀態矩陣直接轉成 test case。

## 待寫章節

- [x] Widget test 的狀態覆蓋策略（從狀態矩陣推導 test case）
- [x] 導航路徑 test（back 按鈕、route 可達性）
- [x] Playwright 瀏覽器驗證流程
- [x] 螢幕截圖比對（visual regression）

## 跨分類引用

- ← [ux-design 模組一 畫面狀態機](/ux-design/01-screen-state-machine/)：狀態矩陣是 test case 的 SOT
- ← [ux-design 模組五 導航模式](/ux-design/05-navigation-patterns/)：go vs push 語意影響 test 斷言
- ← [ux-design 模組六 互動回饋設計](/ux-design/06-interaction-feedback/)：按鈕級與畫面級檢查清單可直接轉 widget test 斷言（loading 進入 disabled、完成後恢復）
- ← 案例入口：[T.C9 外接螢幕漏通知](/testing/cases/outbox-sequence-external-display/)：外接裝置／第二螢幕的驗證邊界——斷言送出的訊息流，裝置端的渲染交由裝置自己的系統驗證
