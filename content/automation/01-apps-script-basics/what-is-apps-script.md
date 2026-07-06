---
title: "Apps Script 是什麼、跟一般伺服器差在哪"
date: 2026-07-06
slug: "what-is-apps-script"
description: "把 Apps Script 定位成 Google 托管的無主機 JS 執行環境時，容器綁定與獨立專案的差別、以及沒有常駐程序帶來的取捨"
weight: 1
tags: ["automation", "apps-script", "v8", "container-bound"]
---

Apps Script 是 Google 托管的 JavaScript 執行環境：你寫的程式碼跑在 Google 的伺服器上、用 V8 引擎執行，對個人 Google 帳號免費。它的定位是「膠水」——用少量程式碼把 Google 的服務（試算表、Gmail、日曆、雲端硬碟）跟外部串起來，補上這些服務單靠介面做不到的自動化。對流量統計這個案例，它扮演的是接住 beacon、把資料寫進 Sheet 的接收端。

## 沒有常駐程序：跟一般伺服器最大的差別

Apps Script 跟一台伺服器最根本的差別是**沒有一個常駐、屬於你的程序**。一般伺服器是一支持續執行的程式，開機後一直在記憶體裡等請求；Apps Script 的程式碼平時不執行，只在被觸發（有人打 web app 網址、觸發器到點、你手動按執行）時才啟動一個執行實例，跑完就結束。這個模型帶來幾個要先知道的取捨：

- **不必管主機**：沒有作業系統要維護、沒有開關機、沒有閒置費用。程式碼不跑時完全不佔資源。
- **每次執行是獨立的**：兩次執行之間，記憶體裡的變數不會保留。要跨執行記住東西，得寫進外部儲存（Sheet、`PropertiesService`、Drive）。這跟伺服器可以用行程內記憶體 cache 是相反的。
- **有執行上限**：單次執行最長 6 分鐘、同時併發有數量限制。長時間或高併發的工作不適合，細節見[執行配額](/automation/knowledge-cards/execution-quota/)。

理解「沒有常駐程序」才知道 Apps Script 適合什麼：短、偶發、由事件觸發的工作，例如「接一則 beacon 寫一列」「每天彙總一次」。不適合的是需要持續連線、低延遲、或狀態常駐記憶體的服務。

## 容器綁定 vs 獨立專案

Apps Script 專案有兩種存在形式，差別在「它跟一個 Google 檔案綁不綁定」。

**容器綁定（container-bound）** 的專案依附在一個具體檔案上——從某張試算表的 `擴充功能 → Apps Script` 開出來的專案，就綁定那張試算表。它的好處是程式裡用 `SpreadsheetApp.getActiveSpreadsheet()` 直接拿到那張表，不必記檔案 ID；流量統計用這種，程式跟資料表天生綁在一起，最省事。它也能存取容器檔案特有的事件（例如試算表的 `onEdit`、表單的 `onFormSubmit`）。

**獨立專案（standalone）** 不依附任何檔案，從 `script.google.com` 直接建立。它適合「不特別綁一個檔案」的工具，或要跨多個檔案操作的情境；存取試算表要用 `SpreadsheetApp.openById("表的ID")` 明確指定。

選擇判準很直接：**這段程式主要就是服務某一個檔案嗎**——是（流量統計服務那張 log 表），用容器綁定；否（一個要操作很多表的通用工具），用獨立專案。

## 用到的服務

Apps Script 透過一組內建服務物件操作 Google 資源，這個案例會碰到的主要是：

- `SpreadsheetApp`：讀寫試算表，`appendRow`、`getRange` 等，是資料的儲存層（模組三詳談）。
- `ContentService`：產生 web app 的回應內容，`doPost` 必須回傳它的輸出。
- `ScriptApp`：管理觸發器，時間排程彙總會用到（模組四）。
- `PropertiesService`：存少量 key-value 設定或狀態，適合放「上次處理到哪一列」這種跨執行要記住的小資料。

這些服務都以你的 Google 帳號身分執行、受你的授權範圍約束，授權模型是下一篇[web app 部署模型](/automation/01-apps-script-basics/web-app-deployment-model/)的主題。

## 下一步

知道 Apps Script 是什麼之後，要讓它能被 blog 的 beacon 打到，得把它部署成有公開網址的 web app。部署模型、`doGet`/`doPost`、以及授權流程，見[web app 部署模型](/automation/01-apps-script-basics/web-app-deployment-model/)。
