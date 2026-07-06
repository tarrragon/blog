---
title: "寫入與並發：appendRow 與 LockService"
date: 2026-07-06
slug: "append-and-concurrency"
description: "多個 beacon 同時寫進同一張 Sheet 時，appendRow 的競態風險與 LockService 序列化寫入的時機判斷"
weight: 1
tags: ["automation", "google-sheets", "appendrow", "lockservice", "concurrency"]
---

Sheet 的寫入層要處理的核心問題是：當多個 beacon 幾乎同時打進來、各自觸發一個 `doPost` 執行實例、都要往同一張表寫一列時，這些並發寫入會不會互相干擾。單筆寫入很單純，並發才是這一層真正要判斷的地方。先講單筆怎麼寫，再講並發何時需要保護。

## appendRow：單筆寫入

`appendRow` 在表格最後一列的後面新增一列，是 log 型資料最自然的寫法——每個事件就是一列、append 到尾巴。它一次接一個陣列、對應各欄：

```javascript
sheet.appendRow([new Date(), data.path, data.dev]);
```

`appendRow` 的好處是它自己找「最後一列的下一列」，不必你算行號。對「一次寫一筆瀏覽」這種場景，它是最直接的選擇。要注意它是「整列 append」——如果需要一次寫很多列（例如批次彙總），逐筆呼叫 `appendRow` 會慢，那時改用 `getRange(...).setValues(二維陣列)` 一次寫一整塊，效能差很多。單筆用 `appendRow`、批次用 `setValues`，是 Sheets 寫入的基本分工。

## 並發：兩個 doPost 同時 append 會怎樣

Apps Script 允許多個執行實例同時跑（個人帳號上限 30 個併發）。當兩個 beacon 幾乎同時到達，平台會起兩個 `doPost` 實例並行執行，兩者都呼叫 `appendRow`。多數情況下 Google 會把兩次 append 排到不同列、相安無事；但在高並發下，「兩個實例同時判斷『最後一列是第 100 列』、都想寫第 101 列」的競態是可能發生的，結果是一筆覆蓋另一筆、少記一筆。

這個風險要不要處理，取決於**你的瞬間併發有多高**。個人 blog 的流量分散在整天，任何一刻同時到達的 beacon 通常是個位數甚至零，競態機率極低、就算偶爾少記一筆對「哪篇有人看」的判斷也無影響——這種情境不必加保護，保持 `appendRow` 的簡單。真正需要處理的是「短時間尖峰」：某篇文章被大量分享、一分鐘湧入幾百次瀏覽，這時並發拉高、競態才變得值得防。

## LockService：需要時才序列化

要防競態，用 `LockService` 把寫入序列化——讓同一時間只有一個執行實例能進入寫入區段，其他的排隊等它做完：

```javascript
function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(5000); // 最多等 5 秒拿鎖
  try {
    var data = JSON.parse(e.postData.contents);
    SpreadsheetApp.getActiveSpreadsheet().getSheetByName("工作表1")
      .appendRow([new Date(), data.path || "", data.dev || ""]);
  } finally {
    lock.releaseLock(); // 一定要放，否則後面全部卡住
  }
  return ContentService.createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

`getScriptLock` 取的是整個腳本共用的鎖，保證所有 `doPost` 實例排隊寫入。`waitLock(5000)` 是「最多等 5 秒」——等不到就丟例外（併發高到 5 秒還排不進來，這筆放棄，總比無限等好）。`releaseLock` 必須放在 `finally`，確保就算中間出錯也會釋放，否則鎖沒放、後面的請求全部卡死。

加鎖的代價是寫入從並行變序列，尖峰時每筆要多等前面的做完，吞吐下降。所以它是「有並發競態風險時才加」的保護，不是預設就要有的東西。判斷訊號回到前面那句：**瞬間併發會不會高到讓競態實際發生**——不會就別加，會就加上。這也是為什麼流量統計的基本版 `doPost`（模組二）刻意不含 lock：先讓簡單版跑起來，等真的遇到尖峰漏記，再加這一層。

## 下一步

寫入處理好了，資料表本身怎麼設計、以及 Sheets 累積到多大會撐不住，見[資料模型與容量邊界](/automation/03-sheet-as-database/data-model-and-capacity/)。
