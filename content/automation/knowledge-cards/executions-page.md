---
title: "Executions（執行項目）"
date: 2026-08-03
description: "Apps Script 平台記錄每一次函式執行的時間、耗時與狀態的頁面，用來判斷請求究竟有沒有抵達接收端"
weight: 7
tags: ["automation", "apps-script", "debugging", "observability", "knowledge-card"]
---

執行項目是 Apps Script 編輯器左側的一個頁面，列出這個專案每一次函式執行的時間、耗時、觸發方式與狀態。它記錄的是平台實際跑過什麼，因此是這類架構裡唯一不依賴推測的觀測點——程式碼只顯示它宣稱會做什麼，執行項目顯示它做了什麼。接收 [beacon](/automation/knowledge-cards/beacon/) 的 [doPost](/automation/knowledge-cards/doget-dopost/) 每被呼叫一次就在這裡留下一列。

## 概念位置

這個頁面回答的問題是「請求有沒有抵達端點」，而它把故障範圍切成兩半：**有執行紀錄但狀態失敗**代表請求送達了、接收端出錯；**完全沒有對應時間的執行紀錄**代表請求根本沒送出來，問題在瀏覽器端或網路。兩者的排查方向相反，而在此之前它們的症狀完全相同——試算表都沒有新資料。

它與 `Logger.log` 的分工也在這裡：`Logger` 記錄的是程式自己選擇要說的話，執行項目記錄的是平台觀察到的事實，程式在第一行就爆掉時前者什麼都沒有、後者仍有一列失敗紀錄。判讀失敗紀錄時常要對照[執行配額](/automation/knowledge-cards/execution-quota/)的三條上限，因為逼近上限的症狀（耗時拉長、密集失敗）都先出現在這一頁。

## 可觀察訊號與例子

一次正常的 beacon 接收在這裡是「`doPost` / 網頁應用程式 / 一秒出頭 / 已完成」。耗時異常拉長是逼近[執行配額](/automation/knowledge-cards/execution-quota/)單次上限的前兆；同一時段出現大量失敗則指向併發撞頂。

版本欄位還洩漏另一件事：它顯示這次執行用的是哪一個部署版本，因此「程式碼改了但端點跑舊版」這個假故障在這裡看得出來。

## 判讀方式

排查「資料沒進來」時先開這一頁，再決定往哪個方向查——這一步的成本是開一個頁面，而它省下的是往錯誤方向排查的整段時間。實際運用見[假故障與靜默失效的診斷](/automation/06-reading-the-data/diagnosing-silent-failures/)。
