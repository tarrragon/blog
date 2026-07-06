---
title: "接收端 handler：寫進第一筆"
date: 2026-07-06
description: "Apps Script 這端怎麼解析 text/plain 的 beacon、用伺服器時間補上時間戳、append 進 Sheet，並在部署後確認收到第一筆真實瀏覽"
weight: 2
tags: ["automation", "apps-script", "dopost", "appendrow", "deployment"]
---

接收端的責任是：接住前端送來的 beacon，把它解析成一筆結構化紀錄，安全地 append 進 Google Sheet，然後回一個簡短回應。這一篇從一張空白試算表開始，做到部署後打開試算表看到第一列瀏覽紀錄。前端那半見[前端 beacon 與 CORS 障礙](/automation/02-analytics-beacon/frontend-beacon/)，這裡假設 beacon 已經在送。

## 準備一張 Sheet 當儲存體

先在 Google Sheets 建一張新試算表，命名例如 `blog-analytics`。第一列放欄位標題，對應接收端要寫的欄位：`時間`、`路徑`、`來源`、`語言`、`裝置`。這一列標題只是給人看的，接收端從第二列開始 append 資料。

Apps Script 有兩種綁定方式，這裡用**容器綁定**：直接在這張試算表的選單開 `擴充功能 → Apps Script`，開出來的 script 專案天生就跟這張試算表綁在一起，程式裡用 `SpreadsheetApp.getActiveSpreadsheet()` 就能拿到它，不必記試算表 ID。兩種綁定方式的差異、以及什麼時候該用獨立專案，見[模組一：Apps Script 地基](/automation/01-apps-script-basics/)。

## 寫 doPost 接住 beacon

前端用 `sendBeacon` 送 `POST`，所以接收端要實作 `doPost`。`sendBeacon` 送來的內容放在 `e.postData.contents`，是一個 JSON 字串（前端刻意用 `text/plain` 傳輸、內容仍是 JSON），接收端 `JSON.parse` 把它還原：

```javascript
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);

    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("工作表1");
    sheet.appendRow([
      new Date(),          // 時間：用伺服器時間，不信任前端傳的時間
      data.path || "",     // 路徑
      data.ref || "",      // 來源
      data.lang || "",     // 語言
      data.dev || "",      // 裝置：mobile / tablet / desktop
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

三個實作決定值得說明：

**時間用伺服器的 `new Date()`，不用前端傳的時間。** 前端時間來自使用者的裝置，時區、時鐘準不準都不可控，還多一個可被偽造的欄位。接收端執行的當下時間就是最接近真實的瀏覽時間，用它最乾淨。這也是前端 payload 不需要送時間戳的原因。

**每個欄位都用 `|| ""` 給預設值。** beacon 有可能因為前端狀況送來缺欄位的資料，`data.path` 若是 `undefined`，直接寫進 Sheet 會是空格但不會報錯；用 `|| ""` 明確寫成空字串，讓資料形狀一致，之後彙總不會踩到 `undefined`。

**整段包在 `try/catch` 裡。** 接收端可能收到格式壞掉的請求（爬蟲亂打、payload 不是合法 JSON）。`JSON.parse` 遇到壞資料會丟例外，沒接住的話這次執行算失敗、也可能讓錯誤累積。包起來後，壞請求就回一個 `ok: false`、不影響服務。真正在意這些壞請求要不要防、怎麼防，見模組五。

回應用 `ContentService.createTextOutput` 回一小段 JSON。`sendBeacon` 是 fire-and-forget、前端根本不會讀這個回應，所以回什麼不重要——但 `doPost` 必須回一個 `ContentService` 的輸出，這是 Apps Script web app 的硬性要求，不回會被當成執行沒有正常結束。

## 部署成 web app

程式寫好還打不通，因為它還沒有對外網址。在 Apps Script 編輯器右上角 `部署 → 新增部署作業`，類型選 `網頁應用程式`，兩個設定要對：

- **執行身分（Execute as）**：選「我」。beacon 是匿名訪客送來的，他們沒有你試算表的權限；選「我」讓這段程式用你的身分執行，才寫得進你的 Sheet。
- **誰可存取（Who has access）**：選「所有人」。訪客是沒登入 Google 的匿名瀏覽器，只有「所有人」這個選項能讓匿名 beacon 打得進來。

部署後會拿到一個網址，形如 `https://script.google.com/macros/s/AKfyc.../exec`。把這個網址填回前端 beacon 的 `ENDPOINT`（見前端那半）。這兩個設定的安全含義——「所有人可存取」會不會被濫用、要不要加保護——在模組五完整討論；先讓它通，才有東西可以保護。

## 確認收到第一筆

部署完、前端網址也填好後，打開你的 blog 任一頁（正式網域，不是本機預覽），beacon 就會送出。回到 Google Sheet，第二列應該出現一筆：伺服器時間、你剛看的路徑、來源、語言。看到這一列，整條 client beacon 管線就打通了——前端偵測、跨網域送達、接收端解析、寫進儲存體，每一環都在運作。

如果沒出現，最常見的兩個原因：一是前端 `ENDPOINT` 填成舊的部署網址（每次「新增部署作業」網址會變，改程式後要用「管理部署作業」更新同一個部署、網址才不變），二是部署的存取權限沒設成「所有人」導致匿名 beacon 被擋。這兩個都是設定問題，不是程式問題。

## 下一步

第一筆進來了，但這只是單筆寫入。當多個瀏覽在同一瞬間打進來，`appendRow` 會不會互相覆蓋？資料列累積到幾萬列時 Sheets 還撐得住嗎？這些是[模組三：Sheets 當資料庫](/automation/03-sheet-as-database/)要處理的並發與容量問題。
