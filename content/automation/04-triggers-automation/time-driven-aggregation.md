---
title: "時間觸發器：把 raw log 彙總成日報"
date: 2026-07-06
slug: "time-driven-aggregation"
description: "用時間觸發器每天定時把原始瀏覽 log group 成日報，以及在 90 分鐘觸發配額下只讀增量的效率寫法"
weight: 1
tags: ["automation", "apps-script", "trigger", "aggregation", "cron"]
---

[時間觸發器](/automation/knowledge-cards/time-driven-trigger/)（time-driven trigger）讓 Apps Script 從「被動等 beacon 打進來」變成「主動定時執行」。它的用途是把 raw log 這種逐筆、直接看沒意義的原始資料，每天固定時間彙總成「昨天每篇看幾次」的日報，讓人打開試算表看到的是整理過的數字。先講怎麼設定定時、再講彙總邏輯、最後講怎麼在配額內寫得有效率。

## 設定每日定時執行

觸發器可以用程式建立，也可以在編輯器左側的「觸發條件」介面點選建立。用程式建立的好處是設定跟著專案走、可版本控制：

```javascript
function createDailyTrigger() {
  ScriptApp.newTrigger("aggregateYesterday")
    .timeBased()
    .atHour(1)          // 每天凌晨 1 點
    .everyDays(1)
    .create();
}
```

這段執行一次（手動按執行），就註冊了一個「每天凌晨 1 點呼叫 `aggregateYesterday`」的觸發器。凌晨執行是刻意的：那時流量低、raw log 當天的資料已經齊了，彙總前一天不會漏。要注意 `createDailyTrigger` 只該跑一次——每跑一次就多註冊一個觸發器，重複跑會變成一天彙總很多次。管理現有觸發器用 `ScriptApp.getProjectTriggers()` 查、`deleteTrigger` 刪。

## 彙總邏輯

彙總做的事是：讀 raw log、把同一天同一路徑的瀏覽數出來、寫進另一張「日報」工作表。核心是一個 group by：

```javascript
function aggregateYesterday() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var raw = ss.getSheetByName("工作表1").getDataRange().getValues();
  var report = ss.getSheetByName("日報") || ss.insertSheet("日報");

  var counts = {}; // key = "日期|路徑" → 次數
  for (var i = 1; i < raw.length; i++) {      // 從第 2 列起，跳過標題
    var d = raw[i][0];                        // 時間欄
    var day = Utilities.formatDate(d, "Asia/Taipei", "yyyy-MM-dd");
    var path = raw[i][1];
    var key = day + "|" + path;
    counts[key] = (counts[key] || 0) + 1;
  }

  var rows = Object.keys(counts).map(function (k) {
    var parts = k.split("|");
    return [parts[0], parts[1], counts[k]];   // 日期、路徑、次數
  });
  if (rows.length) {
    report.getRange(report.getLastRow() + 1, 1, rows.length, 3).setValues(rows);
  }
}
```

這段 group by 有一個前提要明寫出來：**它假設 raw log 裡一列等於一次瀏覽**。這在模組二的資料模型下成立，因為 beacon 只在頁面載入時送一次。日後若在 payload 加入其他事件型別（例如離開事件，見[模組六](/automation/06-reading-the-data/event-model/)），每次瀏覽會產生多列，而這個迴圈仍然合法執行、只是把多數瀏覽數了不只一次——數字膨脹而沒有任何錯誤訊息。膨脹的倍率不固定（離開事件會丟失一部分），所以它比整數倍的錯誤更難從數字本身看出來。屆時的修法是在迴圈裡先篩事件型別：

```javascript
if (raw[i][5] !== "view") continue;   // 只數進入事件（第 6 欄）
```

**這個修法有一個連帶條件容易漏掉**：下一節的增量讀取寫的是 `getRange(..., newCount, 5)`，只讀五欄。五欄讀進來時 `raw[i][5]` 是 `undefined`，`undefined !== "view"` 恆真，於是每一列都被跳過、日報變成空白。兩個常數（讀幾欄、事件欄在第幾欄）必須一起改，而它們相隔兩節、都不會報錯。

把這個前提寫在程式碼旁邊，是為了讓資料模型變更的人搜尋得到所有依賴它的地方。這類「條件式合法執行但已換語意」的失效方式，見[假故障與靜默失效的診斷](/automation/06-reading-the-data/diagnosing-silent-failures/)。

兩個實作決定值得說明。**日期用 `Utilities.formatDate` 明確指定時區**（這裡 `Asia/Taipei`），否則跨午夜的資料可能因為時區偏移被算到錯的日子。**寫日報用 `setValues` 一次寫一整塊、不用 `appendRow` 逐列寫**——彙總結果可能有幾十上百列，逐列 append 會慢且容易逼近執行時間，一次 `setValues` 快得多（呼應[寫入與並發](/automation/03-sheet-as-database/append-and-concurrency/)講的批次寫入）。

## 在 90 分鐘配額內寫得有效率

觸發器受一條配額約束：個人帳號所有觸發器每天總執行時間上限 90 分鐘，且單次一樣不能超過 6 分鐘（見[執行配額](/automation/knowledge-cards/execution-quota/)）。上面那段每次 `getDataRange().getValues()` 把**整張 raw log** 讀進來——log 還小時沒問題，但累積到數十萬列後，光讀取就可能逼近 6 分鐘。

有效率的寫法是**只讀增量**：記住「上次彙總處理到第幾列」，這次只讀新增的部分。用 `PropertiesService` 存這個游標：

```javascript
var props = PropertiesService.getScriptProperties();
var lastRow = Number(props.getProperty("lastAggregatedRow") || 1);
var sheet = ss.getSheetByName("工作表1");
var newCount = sheet.getLastRow() - lastRow;
if (newCount > 0) {
  var fresh = sheet.getRange(lastRow + 1, 1, newCount, 5).getValues();   // 5 = 目前的欄數
  // ... 只彙總 fresh ...
  props.setProperty("lastAggregatedRow", String(sheet.getLastRow()));
}
```

那個 `5` 是目前的欄數，它與前面那個「一列等於一次瀏覽」是同一種前提：欄位增加時要跟著改，而讀少了不會報錯、只會讓後面的欄位變成 `undefined`。

只讀增量讓每次彙總的成本跟「昨天新增多少」成正比、而不是跟「歷史總量」成正比，執行時間就穩定、不隨資料累積膨脹。這跟[資料模型與容量邊界](/automation/03-sheet-as-database/data-model-and-capacity/)講的分表是互補的兩招——分表縮小單張表、只讀增量縮小單次讀取，都是為了讓彙總不被歷史總量拖垮。

## 下一步

時間觸發器是「到點就跑」的排程。另一類觸發器是「某個事件發生就跑」，例如表單被提交——見[表單與事件觸發器](/automation/04-triggers-automation/form-and-event-triggers/)。
