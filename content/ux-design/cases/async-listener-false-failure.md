---
title: "U.C9 提取成功卻誤報失敗 — 結果通知鏈路被搶通道"
date: 2026-07-17
description: "操作實際成功、資料已寫入，UI 卻顯示失敗時使用。多 context 的訊息通道語意（誰負責回應）是結果通知鏈路的一部分，async listener 搶通道會把 undefined 當成回應送回"
weight: 9
tags: ["ux-design", "case-study", "interaction-feedback", "chrome-extension", "web", "messaging"]
---

這個案例的核心責任是說明「結果通知」不只是 UI 呈現問題 — 結果從執行端傳回 UI 的鏈路本身會斷、會錯，而鏈路故障的最壞形態是誠實度反轉：操作成功、UI 報失敗。

## 觀察

電子書庫總覽 Chrome 擴充功能（book_overview_v1，Manifest V3）的提取流程：popup 觸發 content script 擷取書目、寫入 storage、回報結果。實機測試中 content script 成功提取 96 本且 storage 已寫入，popup UI 卻顯示「提取失敗 / 未知錯誤」。

根因在訊息通道語意（commit `97c24b2b6`）：橋接模組的 message listener 宣告成 async。收到非它負責的訊息型別時函式體直接結束，async 函式回傳 `Promise.resolve(undefined)` — Manifest V3 把「listener 回傳 Promise」解讀為「此 listener 負責回應」，把 undefined 搶先送回 popup，與真正處理該訊息的 listener 競爭。popup 拿到 undefined、走 else 分支拋「未知錯誤」。

修復：listener 改為同步函式，非處理訊息回傳 undefined（不搶通道）、async 邏輯抽成 fire-and-forget handler。

同專案的 sibling 事故（commit `a62ce00d8`）：訊息路由的 handler 沒被注入、事件協調器沒被啟動，`EXTRACTION.COMPLETED` 事件沒有任何訂閱者 — 提取完成但資料未儲存、popup 連線失敗。鏈路斷的位置不同（組裝遺漏 vs 通道語意），使用者看到的都是「操作沒有結果」。

## 判讀

1. **結果通知有一個隱含前提：結果會正確到達 UI**。回饋設計通常聚焦「到達之後怎麼呈現」（訊息形式、通知元件），但 popup / content script / service worker 是三個獨立 context，結果要跨兩次訊息通道才到 UI — 每一跳都是回饋鏈路的一部分，通道語意錯誤等於回饋設計全部白做。

2. **成功誤報失敗比沒有回饋更糟**。零回饋讓使用者困惑；誠實度反轉讓使用者採取錯誤行動 — 重做一次提取（資料重複）、回報 bug、放棄使用。UI 的宣告與系統實際狀態相反時，使用者對介面的每一個訊息都會失去信任。

3. **通道語意是平台契約、不是實作細節**。「listener 回傳 Promise = 認領回應權」是 Manifest V3 的行為規格，混用 async 語法糖與訊息協定就會觸發。這類契約在單元測試中不可見（mock 掉通道）、只有整合層才會現形。

## 策略

1. **結果通知鏈路要有端對端驗證**：「操作成功 → UI 顯示成功」作為整合測試斷言，涵蓋跨 context 的完整鏈路，不只測 UI 元件收到資料後的呈現。

2. **通道上的每個 listener 明確宣告回應權**：負責回應的同步回傳 true 保持通道、不負責的不回傳 — async listener 在共享通道上是候選錯誤。

3. **事件鏈路的組裝有清單**：事件的發佈者與訂閱者在啟動時逐一核對（handler 已注入、coordinator 已啟動），組裝遺漏讓事件無聲消失。

## 下一步路由

- 結果通知該呈現什麼 → [互動回饋三層模型](/ux-design/06-interaction-feedback/feedback-three-layers/)
- 類似案例（UI 未接線、三層回饋全缺）→ [U.C5 匯出按鈕零回饋](/ux-design/cases/export-button-zero-feedback/)
- 完成宣告的證據強度 → [U.C11 抓到 96/928 本就顯示完成](/ux-design/cases/lazy-load-premature-completion/)
