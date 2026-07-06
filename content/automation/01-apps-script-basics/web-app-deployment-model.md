---
title: "web app 部署模型與授權"
date: 2026-07-06
slug: "web-app-deployment-model"
description: "把 Apps Script 掛成可被 HTTP 呼叫的端點時，doGet/doPost 進入點、exec 與 dev 兩種網址、以及更新部署為什麼要用同一個網址"
weight: 2
tags: ["automation", "apps-script", "deployment", "doget-dopost", "authorization"]
---

web app 部署是把 Apps Script 從「只能在編輯器裡手動執行」變成「有公開網址、任何 HTTP 請求都能觸發」的動作。這是讓 blog 的 beacon 能打到接收端的前提。這一篇講三件事：程式怎麼接住請求（`doGet`/`doPost`）、部署產生的兩種網址差在哪、以及授權為什麼第一次會跳警告。

## doGet 與 doPost：兩個進入點

web app 對外的行為由兩個特殊函式定義。收到 GET 請求時，Google 平台呼叫 `doGet(e)`；收到 POST 請求時呼叫 `doPost(e)`。參數 `e` 帶著請求內容：`doGet` 從 `e.parameter` 拿 query string，`doPost` 從 `e.postData.contents` 拿請求主體。流量統計的 beacon 用 `sendBeacon` 送 POST，所以接收端實作 `doPost`，從 `e.postData.contents` 讀那串 JSON 字串。

兩個函式都必須回傳一個 `ContentService` 或 `HtmlService` 的輸出，這是平台的硬性要求——不回傳會被當成執行沒有正常結束。詳細用法見知識卡 [doGet / doPost](/automation/knowledge-cards/doget-dopost/)。

值得先記住的一條限制是 Apps Script **沒有** `doOptions`，所以它無法回應跨網域請求的 CORS preflight。這條限制決定了前端 beacon 必須用不觸發 preflight 的方式送，是[前端 beacon 與 CORS 障礙](/automation/02-analytics-beacon/frontend-beacon/)的核心。

## exec 與 dev：兩種網址

部署 web app 後會遇到兩個結尾不同的網址，用途不一樣，搞混會在測試時卡住。

`/exec` 是**正式版網址**：它對應你「部署」的那個版本、網址固定不變、遵守你設定的「誰可以存取」。blog 的 beacon 要填的是這個。`/dev` 是**測試版網址**：它永遠對應編輯器裡最新存檔的程式碼（不必重新部署就生效），但它只有對這個專案有編輯權的人（也就是你，登入狀態下）能存取。`/dev` 適合你自己邊改邊測，`/exec` 才是給匿名訪客用的。

因為 `/dev` 要登入、`/exec` 才允許匿名，用 `/dev` 當 beacon 端點會讓所有沒登入的訪客都被擋掉——這是一個容易誤用的點。beacon 一律用 `/exec`。

## 更新部署為什麼要用同一個網址

改完程式後怎麼讓 `/exec` 反映新版本，是另一個容易出錯的地方。Apps Script 有兩個看起來都能「部署」的入口：`新增部署作業` 會產生一個**全新的** `/exec` 網址；`管理部署作業 → 編輯 → 版本選「新版本」` 則是把**既有部署**更新到新程式碼、**網址不變**。

正確做法是後者：第一次用「新增部署作業」拿到網址、填進 blog；之後每次改程式，都用「管理部署作業」更新同一個部署。如果每次都「新增部署作業」，會不斷產生新網址，而 blog 裡填的還是舊網址、指向舊版本的程式，於是「我明明改了程式怎麼沒生效」。記住這條分工，就避開了這個常見的假故障。

## 首次授權與未驗證警告

第一次部署（或第一次執行會存取你資料的程式）時，Google 會要求授權，流程中會出現一個「Google 尚未驗證這個應用程式」的警告畫面。這個警告是正常的：它出現的原因是這支腳本是你自己寫的、沒有經過 Google 的應用程式審核，而不是因為程式有問題。走「進階 → 前往（專案名稱）」繼續、再「允許」授予它存取你試算表的權限，就完成授權。

授權授予的範圍只涵蓋程式實際用到的服務（這個案例是那一張試算表），不會給到你其他的 Google 資料。之後這支 web app 以你的身分執行，能做的事就是 `doPost` 裡寫的那些。

## 下一步

部署模型清楚後，就能把接收端實際做出來、部署、收到第一筆瀏覽——見[模組二：接收端 handler](/automation/02-analytics-beacon/receiver-handler/)。部署設定「誰可以存取」的安全含義，見[模組五](/automation/05-deploy-quota-security/)。
