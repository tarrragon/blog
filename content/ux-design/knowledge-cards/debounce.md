---
title: "Debounce（防連點）"
date: 2026-07-13
description: "說明合併短時間內重複觸發的技巧，以及 leading-edge 與 trailing-edge 兩種執行語意在按鈕防連點上的差別"
weight: 4
tags: ["ux-design", "knowledge-card", "interaction-feedback", "button-states"]
---

Debounce 的核心概念是「短時間內的重複觸發只算一次」。同一顆按鈕在 300ms 內被點三次，系統只執行一次操作 — 剩下兩次點擊被視為誤觸或焦慮性連點而忽略。它跟 [Doherty Threshold](/ux-design/knowledge-cards/doherty-threshold/) 同屬互動回饋的時間參數：前者管「重複輸入怎麼收斂」、後者管「輸出多快要回來」。

## 兩種執行語意

同一個 debounce 週期有兩個可執行的時間點，選錯會直接改變使用者體感：

- **Leading-edge（立即執行）**：第一次點擊立即生效，之後一段時間內的點擊忽略。按鈕防連點要用這種 — 第一次點擊本來就該立即回應。
- **Trailing-edge（延遲執行）**：等一段時間內沒有新觸發才執行。適合搜尋框輸入這類「等使用者打完字再送查詢」的場景；用在按鈕上會給每次操作加上等待週期的延遲，違反點擊確認的 100ms 即時門檻。

導航鎖（in-flight flag）是按鈕防連點的替代做法：操作進行中拒絕新請求、完成後解鎖，不依賴固定時間窗。

## 可觀察訊號與例子

需要 debounce 的訊號是同一個操作被觸發多次的紀錄：導航堆疊被 push 兩層一樣的頁面、後端收到毫秒級間隔的重複請求、表單被建立兩筆相同資料。非同步按鈕通常用 Loading + disabled 防重複提交，debounce 主要負責同步按鈕（導航、切換）— 這些按鈕操作瞬間完成、沒有 loading 狀態可以擋。

## 設計責任

Debounce 的設計責任是在不犧牲第一次點擊即時性的前提下吸收重複觸發。時間窗常見慣例值是 300ms 上下，依操作型態調整。完整的防連點決策（哪類按鈕用 debounce、哪類用 disabled）見[互動回饋三層模型](/ux-design/06-interaction-feedback/feedback-three-layers/)的兩類按鈕段。
