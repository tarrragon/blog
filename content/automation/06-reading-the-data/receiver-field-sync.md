---
title: "接收端的欄位要跟著 payload 一起改"
date: 2026-09-24
description: "本模組三篇在前端 payload 上加的欄位、模組二接收端與試算表表頭要跟著改的程式碼，以及改完之後讓端點跑新版本的部署步驟"
weight: 6
tags: ["automation", "apps-script", "analytics"]
---

本模組的訪客識別、事件模型與自動化流量辨識三篇實作，都在前端的 payload 上加欄位，而**接收端與試算表表頭不會自己跟著長**。模組二的 `doPost` 是一個寫死的五欄陣列，新欄位送到之後會被靜默丟棄——沒有錯誤、沒有警告，只是那幾欄永遠是空的。這正是[假故障與靜默失效的診斷](/automation/06-reading-the-data/diagnosing-silent-failures/)講的欄位錯位，而它最容易發生在「跟著教學一路改前端」的過程裡。

三篇的欄位都加上之後，payload 會長成下面這十一個欄位：

| 欄位                            | 來自哪一篇                                                              |
| ------------------------------- | ----------------------------------------------------------------------- |
| `path` / `ref` / `lang` / `dev` | 模組二既有                                                              |
| `vid` / `sid`                   | [訪客識別與 opt-out](/automation/06-reading-the-data/visitor-identity/) |
| `t` / `dur` / `act`             | [事件模型與停留時間](/automation/06-reading-the-data/event-model/)      |
| `bot`                           | [辨識自動化流量](/automation/06-reading-the-data/automated-traffic/)    |

對應的接收端要把 `appendRow` 的陣列改成同樣長度，並讓表頭在工作表被清空時自動重建：

```javascript
var HEADERS = ['時間', '路徑', '來源', '語言', '裝置',
               '事件', '訪客ID', 'SessionID', '自動化訊號', '停留秒數', '有互動'];

function getLogSheet() {
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.getSheetByName('工作表1') || ss.insertSheet('工作表1');
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

// doPost 內：陣列順序必須與 HEADERS 一致
getLogSheet().appendRow([
  new Date(), data.path || '', data.ref || '', data.lang || '', data.dev || '',
  data.t || 'view', data.vid || '', data.sid || '', data.bot || '',
  data.dur === undefined ? '' : data.dur,
  data.act === undefined ? '' : data.act
]);
```

把表頭建立放進讀取路徑而非一次性腳本，是因為一次性腳本有個隱性假設：「執行過了」這個狀態存在執行者的記憶裡、不在系統裡。固定位置的 `setValues` 重複執行結果相同，工作表被清空後也會自動重建。

改完之後記得走「管理部署作業 → 編輯 → 版本選新版本」讓端點跑新程式碼——改了程式碼卻沒更新部署是這裡最常見的假故障。

**新欄位只對之後進來的資料生效。** 既有的記錄不會回填，所以本模組教的判讀方法要等新資料累積一段時間才用得上；拿舊資料套新判斷標準會得到「所有記錄都不可識別」這個沒有意義的結論。
