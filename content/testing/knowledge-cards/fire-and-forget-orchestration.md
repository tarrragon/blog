---
title: "Fire-and-Forget Orchestration（射後不理編排）"
date: 2026-07-17
description: "呼叫後不等待完成的編排形態；產生「方法返回不等於流程完成」的時序落差，是 flaky test 的常見根因之一"
weight: 8
tags: ["testing", "async", "fire-and-forget", "flaky"]
---

Fire-and-forget 編排是呼叫後不等待完成的執行形態：主方法觸發一組背景動作後立刻返回，背景動作在獨立的排程中繼續。這個時序落差是[流程測試](/testing/knowledge-cards/flow-test/)中「單跑綠、合跑紅」型 flaky 的常見根因——斷言假設「方法返回＝流程完成」，實際上方法只承諾「請求已送出」。

## 跟其他概念的關係

Fire-and-forget 是編排層的設計選擇，常見於刻意的 UX 決策（結帳成功後先解鎖畫面、收尾動作在背景執行）。它與非同步程式的其他時序問題（callback 順序依賴、事件到達順序）同屬 [flaky test 根因分類](/testing/05-test-design-judgment/flaky-test-root-cause/)的計時依賴類，區別在於根因不是「等太短」而是「根本沒等」。同一時序落差反覆出現的測試，常被送進 [quarantine](/testing/knowledge-cards/quarantine/)：先隔離觀察、依根因分類排修復優先序。

## 可觀察訊號與例子

同一條測試單獨跑通過、與其他測試檔合跑失敗，且失敗在「狀態尚未更新」或「副作用尚未發生」的斷言上。典型案例：結帳流程收尾（列印、狀態清理、資料同步）沒有被 await，測試斷言在收尾完成前執行（[fire-and-forget 編排讓測試單跑綠、合跑紅](/testing/cases/fire-and-forget-test-race/)）。

## 判斷條件與後果

斷言在什麼時點執行，取決於測試用什麼方式等背景動作結束。用固定 sleep 等待時，賽跑的起跑線只是往後挪：排程比 sleep 慢的環境（例如跟其他測試檔合跑時）照樣在收尾完成前斷言，測試回到單跑綠、合跑紅的狀態。輪詢終態時，「完成」由一個可觀察的條件定義（狀態欄位的值、計數器到位），輪詢到條件成立或超過上限次數才斷言，等待時間跟著環境的排程速度伸縮。修法的另一個分岔是 fire-and-forget 是否為刻意的產品設計：是的話，編排維持不等待，改的是測試的等待策略，時序特性記錄下來；不是的話，編排改成可等待，方法返回就代表流程完成，測試不必再輪詢。劇本模板在[語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)章。
