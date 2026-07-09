---
title: "Forecast（需求預測，FCST）"
date: 2026-07-09
description: "說明需求預測作為參考基準與其失準特性"
weight: 20
tags: ["business", "procurement", "knowledge-cards"]
---

Forecast（需求預測，簡稱 FCST）的核心概念是「對未來用量的預估」，它是備料的起點參考，而不是保證。採購用 forecast 決定要提前備哪些料、備多少，但同時要清楚 forecast 會失準，尤其在搶單旺季。Forecast 要搭歷史數據與淡旺季判斷一起讀，才不會被單一數字誤導；它跟 [Lead Time](/business/procurement-planning/cards/lead-time/) 一起決定每顆料的下單時點與備量。

## 概念位置

Forecast 是需求端送給採購的訊號，跟 [Lead Time](/business/procurement-planning/cards/lead-time/) 一起決定下單時點與數量。對長交期料，forecast 是提前卡位的依據；對短交期料，實際訂單拉動比 forecast 更可靠。Forecast 也是判斷要不要 [Risk Buy](/business/procurement-planning/cards/risk-buy/) 的基礎—根據 forecast 的風險比例，決定備多少原材料。

## 可觀察訊號與例子

判讀 forecast 可信度的訊號：這個客戶或產品線過去 forecast 與實際用量的落差有多大、目前是淡季還是旺季、市場是否正在搶單（全面性 LT 拉長、原廠發 allocation、broker 現貨價跳動都是徵兆）。搶單旺季時 forecast 幾乎測不準，因為大家都在超額下單卡產能。有經驗的採購會把 forecast 放進系統跑，再用歷史數據比對抓出系統性偏差—例如某產品線 forecast 長期高估兩成，備料時就自動打折。

## 判讀方式

拿到 forecast 時，把它當參考而非命令。若 forecast 有進系統，依系統做事並用歷史數據校正差異；若沒進系統，依各料件的 LT 與市場狀況主動推前端做策略性備料。最危險的是把 forecast 當成準確的未來、照單全收備料，結果旺季實際暴衝或淡季庫存積壓。Forecast 的價值在於觸發思考「這個數字在什麼條件下會錯」，而不是提供一個可以照抄的答案。
