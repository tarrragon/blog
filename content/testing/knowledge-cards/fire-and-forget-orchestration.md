---
title: "Fire-and-forget 編排"
date: 2026-07-17
description: "呼叫後不等待完成的編排形態；產生「方法返回不等於流程完成」的時序落差，是 flaky test 的常見根因之一"
weight: 8
tags: ["testing", "async", "fire-and-forget", "flaky"]
---

Fire-and-forget 編排是呼叫後不等待完成的執行形態：主方法觸發一組背景動作後立刻返回，背景動作在獨立的排程中繼續。這個時序落差是[流程測試](/testing/knowledge-cards/flow-test/)中「單跑綠、合跑紅」型 flaky 的常見根因——斷言假設「方法返回＝流程完成」，實際上方法只承諾「請求已送出」。

## 概念位置

Fire-and-forget 是編排層的設計選擇，常見於刻意的 UX 決策（結帳成功後先解鎖畫面、收尾動作在背景執行）。它與非同步程式的其他時序問題（callback 順序依賴、事件到達順序）同屬 [flaky test 根因分類](/testing/05-test-design-judgment/flaky-test-root-cause/)的計時依賴類，區別在於根因不是「等太短」而是「根本沒等」。同一時序落差反覆出現的測試，常被送進 [quarantine](/testing/knowledge-cards/quarantine/)：先隔離觀察、依根因分類排修復優先序。

## 可觀察訊號與例子

同一條測試單獨跑通過、與其他測試檔合跑失敗，且失敗在「狀態尚未更新」或「副作用尚未發生」的斷言上。典型案例：結帳流程收尾（列印、狀態清理、資料同步）沒有被 await，測試斷言在收尾完成前執行（[T.C8](/testing/cases/fire-and-forget-test-race/)）。

## 設計責任

測試策略是輪詢終態取代固定等待：定義「完成」的可觀察條件（狀態欄位值、計數器到位），輪詢直到條件滿足或超過上限次數。固定 sleep 只是把賽跑的起跑線挪後，不同環境的排程速度不同，問題會再次出現。修法的選擇取決於 fire-and-forget 是否為刻意的產品設計——是的話改測試等待策略並記錄時序特性，改成可等待的則直接修正編排。劇本模板在[語意級假後端與流程測試](/testing/01-test-strategy-layers/semantic-fake-backend/)章。
