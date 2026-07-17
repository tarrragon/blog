---
title: "U.C10 Service Worker 冷啟動期間的假離線 — initializing 狀態未建模"
date: 2026-07-17
description: "畫面把「查詢對象還沒醒」顯示成「離線 / 不可用」時使用。查詢對象有獨立生命週期（service worker、遠端服務）時，「還不知道」是真實狀態，與離線合併會產生假離線窗口"
weight: 10
tags: ["ux-design", "case-study", "state-machine", "chrome-extension", "web", "service-worker"]
---

這個案例的核心責任是說明狀態矩陣列狀態時的一個系統性遺漏：查詢對象有自己的生命週期時，「還不知道對方狀態」（initializing / unknown）是一個真實狀態 — 把它與「離線」「錯誤」合併，會在每次冷啟動時產生一段假離線窗口。

## 觀察

電子書庫總覽 Chrome 擴充功能（book_overview_v1）的 popup 開啟時向 background service worker 查詢狀態。Manifest V3 的 service worker 是事件驅動、閒置即卸載 — popup 開啟的瞬間 SW 可能正在冷啟動、初始化未完成、不回應 `GET_STATUS`。popup 等待期間顯示「正在檢查狀態...」，2 秒 timeout 後轉為「離線」且不再自動恢復 — 冷啟動偶爾超過 2 秒（極端 I/O、低階裝置，低頻但真實發生過）時，系統實際正常、使用者看到的卻是永久離線（`src/background/background.js:272-284`，ticket 1.1.0-W1-019）。

修復採雙管：查詢端加握手重試，加上被查詢端在初始化期間就回應 baseline 的 `initializing` 狀態 — popup 據此顯示「初始化中」而非落入 timeout 判離線。

同專案的 sibling 事故（commit `86216c37f`）：popup 的書籍偵測數硬編「檢測中...」、從未讀取健康查詢回應中的實際數字 — 過渡狀態的顯示寫死了、永遠停在過渡態。兩個事故一體兩面：一個把「還不知道」誤顯示成終態（離線）、一個把終態永遠顯示成「還不知道」。

## 判讀

1. **「還不知道」與「不可用」是不同狀態**。離線 / 錯誤是查詢得到的答案，initializing 是還沒得到答案。合併兩者的畫面會把「這次醒得慢」定格成永久離線 — 頻率低不減輕代價，使用者據此做錯誤決策：放棄操作、重裝、回報故障。

2. **查詢對象的生命週期決定 initializing 是否必要**。查詢對象與畫面同生命週期（同 process 的本地狀態）時不需要；查詢對象獨立生死（service worker、遠端服務、另一個 process、外部裝置）時，畫面開啟瞬間對方「還沒醒」是常態而非邊角 — initializing 必須是狀態矩陣裡的一行，有自己的顯示、操作與退出路徑。

3. **timeout 是 initializing 的退出路徑**。「初始化中」不能無限停留 — 超過合理時間仍無回應才轉入離線 / 錯誤狀態。順序是 initializing → (回應) 正常態 / (timeout) 離線，而非直接顯示離線等回應來救。

## 策略

1. **列狀態時多問一句**：這個畫面查詢的對象，跟畫面同生命週期嗎？不同 → 補 initializing 狀態進矩陣。

2. **被查詢方在初始化期間就能回應 baseline 狀態** — 「我在、還沒準備好」與「沒有回應」對查詢方是完全不同的資訊。

3. **過渡狀態的顯示必須有資料來源與退出條件** — 硬編的「檢測中...」沒有讀任何回應、也永遠不會離開，等於把過渡態寫成死胡同。

## 下一步路由

- 狀態矩陣的四欄與填寫步驟 → [畫面狀態矩陣的定義與填寫方法](/ux-design/01-screen-state-machine/state-matrix-definition/)
- 等待多久該顯示什麼指示 → [時間感知與回應策略](/ux-design/06-interaction-feedback/response-time-strategy/)
- 類似案例（狀態設計遺漏）→ [U.C1 五個狀態零個退出路徑](/ux-design/cases/five-states-zero-exits/)
