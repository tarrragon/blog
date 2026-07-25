---
title: "doGet / doPost"
date: 2026-07-06
description: "Apps Script web app 的兩個進入點函式，分別接住 GET 與 POST 請求，決定端點收到請求時執行什麼"
weight: 3
tags: ["automation", "apps-script", "doget", "dopost", "knowledge-card"]
---

`doGet` 與 `doPost` 是 Apps Script web app 的兩個進入點函式：端點收到 GET 請求時平台呼叫 `doGet(e)`，收到 POST 請求時呼叫 `doPost(e)`。它們是 [web app 部署](/automation/knowledge-cards/web-app-deployment/)後對外行為的定義處——寫什麼在裡面，端點被呼叫時就執行什麼。參數 `e` 帶著請求內容：`doGet` 從 `e.parameter` 拿 query string，`doPost` 從 `e.postData.contents` 拿請求主體。

## 概念位置

兩個函式都必須回傳一個 `ContentService` 或 `HtmlService` 的輸出，這是平台的硬性要求；不回傳會被當成執行沒有正常結束。接收 [beacon](/automation/knowledge-cards/beacon/) 這類「送資料進來」的場景用 `doPost`，因為 `sendBeacon` 送的是 POST，主體放在 `e.postData.contents`（是個字串，需要自己 `JSON.parse`）。

## 可觀察訊號與例子

一個影響靜態站的關鍵限制是：Apps Script **沒有** `doOptions`。跨網域請求的 CORS preflight 會送 `OPTIONS`，但它打不到你的程式、平台的預設回應也不帶 CORS 許可標頭，於是 preflight 失敗、真正的請求送不出去。

## 判讀方式

這是「用 `fetch` 送 `application/json` 打 Apps Script 得到 CORS 錯誤」的根因，繞法是讓請求成為不觸發 preflight 的 simple request，見[前端 beacon 與 CORS 障礙](/automation/02-analytics-beacon/frontend-beacon/)。
