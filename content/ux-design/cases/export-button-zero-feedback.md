---
title: "U.C5 匯出按鈕按下零回饋 — 狀態機完備但 UI 沒接線"
date: 2026-07-16
description: "Flutter app 匯出設定頁的確認匯出按鈕 onPressed 是空 callback，按下畫面毫無變化 — 使用者無法分辨匯出成功、進行中、還是功能根本沒做。ViewModel 的 idle/inProgress/completed/failed 狀態機早已完備，缺的只是頁面接線與三層回饋"
weight: 5
tags: ["ux-design", "case-study", "interaction-feedback", "button-states", "flutter", "mobile"]
---

這個案例的核心責任是實證「沒有回饋的按鈕等同壞掉的按鈕」— 即使背後的業務邏輯與狀態機完全正確，按鈕層級三層回饋（點擊確認 / 等待指示 / 結果通知）全缺時，使用者的體感就是功能壞掉。

## 觀察

book_overview_app 的匯出設定頁有一顆「確認匯出」按鈕。實機測試按下後畫面無任何變化：沒有 loading、沒有成功訊息、沒有錯誤訊息。使用者無法判斷三種可能中的哪一種成立：匯出已完成、匯出正在執行、按鈕根本沒接線。

翻開程式碼，真相是第三種 — `onPressed` 是一個空 callback，裡面只有一行 `// 導航到進度頁面` 註解。而 ViewModel 層的 `startExport()` 早已具備 idle / inProgress / completed / failed 的完整狀態轉換邏輯，頁面從未呼叫它。

| 回饋層   | 修復前            | 修復後（W1-086）                                                            |
| -------- | ----------------- | --------------------------------------------------------------------------- |
| 點擊確認 | 無（空 callback） | `onPressed` 接線 `viewModel.startExport`                                    |
| 等待指示 | 無                | `inProgress` 時按鈕禁用 + `CircularProgressIndicator`                       |
| 結果通知 | 無                | `ref.listen` 監聽狀態：成功彈對話框含檔案路徑；失敗彈對話框含原因與重試按鈕 |

修復只改一個檔案（匯出設定頁），ViewModel 與狀態定義一行未動。

## 判讀

1. **三層回饋全缺時，「正確的後端」對使用者不存在**。回饋是使用者感知系統狀態的唯一通道。點擊確認回答「系統收到了嗎」、等待指示回答「還在跑嗎」、結果通知回答「成功了嗎、檔案在哪」。三層全缺時，使用者只能靠猜 — 而猜的預設答案是「壞掉了」。

2. **缺口不在設計，在接線**。這不是「沒設計狀態機」的案例 — 狀態機四個狀態齊全、`retryExport()` 都寫好了。缺口是 UI 層留了一行 TODO 式註解就交付。domain 層完備反而讓缺口更隱蔽：單元測試全綠（ViewModel 邏輯正確），widget 測試只斷言畫面渲染，沒有斷言「按下後狀態轉換」，測試體系抓不到這種缺口。

3. **`onPressed: () {}` 是可機械掃描的訊號**。空 callback、只含註解的 callback，跟寫了函式沒有呼叫者一樣，是「UI 死路」的字面特徵，grep 就能找到，不需要等實機測試。

## 策略

1. **三層回饋條款化為驗收標準**：每顆觸發非同步操作的按鈕，驗收清單固定三問 — 點擊有確認？等待有指示？結果有通知？本案修復同時把這三層寫進規格（FR-8 補「按鈕層級三層回饋」條款，引用 100ms/400ms/1s 時間門檻），讓後續頁面在設計階段就對照。

2. **接線完整性掃描**：交付前 grep `onPressed: () {}`、`onPressed: null`（非刻意禁用場景）與只含註解的 callback。UI 接線遺漏跟死程式碼一樣可機械偵測。

3. **widget 測試必含行為斷言**：每顆按鈕至少一個「tap 後斷言狀態轉換或副作用」的測試，不能只有「按鈕存在且可見」的渲染斷言。本案的 RED 測試（按下確認匯出後狀態非 idle）正是修復前缺失的那一個。

## 下一步路由

- 三層回饋模型的完整定義 → [互動回饋三層模型](/ux-design/06-interaction-feedback/feedback-three-layers/)
- 非同步按鈕的生命週期設計 → [按鈕狀態設計](/ux-design/06-interaction-feedback/button-state-design/)
- 等待指示的時間門檻 → [Doherty Threshold](/ux-design/knowledge-cards/doherty-threshold/)
- 類似案例（回饋誠實但誤導）→ [U.C7 商品條碼的誤導性查無結果](/ux-design/cases/misleading-no-result-for-product-barcode/)
