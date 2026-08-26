---
title: "模組六：收到資料之後"
date: 2026-08-03
description: "流量統計上線、資料開始累積，但欄位讀不出「這是誰、是不是同一個人、是不是機器」時的判讀與補強"
weight: 7
tags: ["automation", "beacon", "analytics", "bot-detection", "privacy", "data-quality"]
---

這一章的責任是把已經收進來的資料變成可判讀的欄位。模組二的終點是「打開試算表，看到自己剛剛的瀏覽出現在第一列」，而從那之後會遇到的問題是：資料持續進來了，欄位卻讀不出意義——來源網址幾乎都是空白、任兩列之間沒有任何關聯可以判斷是不是同一個人、也分不出哪些是真人哪些是機器抓取。

這些問題有一個共同性質——**它們只在真實流量打進來之後才浮現，設計階段推導不出來**。模組零到五處理的是「怎麼把管線接起來」，那條路徑上的每個障礙（CORS preflight、部署授權、配額上限）都能從文件讀出來。這一章處理的是管線接好之後才出現的那一類問題：資料格式完全正確、程式沒有報錯、統計數字看起來合理，而結論是錯的。

補強的方向是給 payload 加上足以交叉判讀的欄位，並理解每個欄位的能力邊界。訪客識別回答「是不是同一個人」，事件模型回答「停留多久、有沒有真的在讀」，自動化訊號回答「這是不是機器」。三者互相驗證——單獨任何一個都能被繞過或誤判，組合起來才有判讀能力。

補強完之後還有一步：把各篇的限制加總，確定這份資料的母體涵蓋了誰。分母不清楚時，比例算得再精確也不知道在說什麼。

## 章節文章

| 文章                                                                                  | 主題                                                                                                                                               |
| ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| [訪客識別與 opt-out](/automation/06-reading-the-data/visitor-identity/)               | 來源網址為何大量空白、用兩層隨機識別碼分辨回訪與單次瀏覽、退出統計為何用 localStorage 而非 cookie 或 IP                                            |
| [事件模型與停留時間](/automation/06-reading-the-data/event-model/)                    | 進入與離開拆成兩則事件、`visibilitychange` 的觸發時機、停留秒數對應的是可見時長、資料模型變更讓既有報表公式換語意                                  |
| [辨識自動化流量](/automation/06-reading-the-data/automated-traffic/)                  | 哪些機器會進入這份統計、接收端讀不到 HTTP 標頭的結構限制、訊號分層與信心度、具名比對與通用退回、先量本站基線、標記而非丟棄、彙總端的分類與條件順序 |
| [這份統計的分母是什麼](/automation/06-reading-the-data/data-coverage/)                | 七條看不見的損失通道、用外部對照估量級、相對問題與絕對問題的分界                                                                                   |
| [假故障與靜默失效的診斷](/automation/06-reading-the-data/diagnosing-silent-failures/) | 錯誤訊息指向的位置不是問題的位置、程式改了但端點沒生效、公式不報錯卻算錯                                                                           |

## 欄位變更要同步到接收端

這一章的三篇實作都在前端的 payload 上加欄位，而**接收端與試算表表頭不會自己跟著長**。模組二的 `doPost` 是一個寫死的五欄陣列，新欄位送到之後會被靜默丟棄——沒有錯誤、沒有警告，只是那幾欄永遠是空的。這正是[假故障與靜默失效的診斷](/automation/06-reading-the-data/diagnosing-silent-failures/)講的欄位錯位，而它最容易發生在「跟著教學一路改前端」的過程裡。

三篇讀完之後，payload 會長成十一個欄位：

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

**新欄位只對之後進來的資料生效。** 既有的記錄不會回填，所以這一章教的判讀方法要等新資料累積一段時間才用得上；拿舊資料套新判斷標準會得到「所有記錄都不可識別」這個沒有意義的結論。

## 讀者旅程

已經跟著模組二把資料收進來、正要開始看報表的人，從[訪客識別](/automation/06-reading-the-data/visitor-identity/)順讀，並在動手改 payload 前先看上一節的欄位變更清單。

已經在懷疑手上的數字的人，入口看症狀分三條：**某個分類永遠是零**多半是資料模型變更後公式沒跟著改，推導在[事件模型談報表公式換語意的那一節](/automation/06-reading-the-data/event-model/)；**懷疑數字裡混了機器**走[辨識自動化流量](/automation/06-reading-the-data/automated-traffic/)；**想知道這些數字到底涵蓋了誰**走[這份統計的分母是什麼](/automation/06-reading-the-data/data-coverage/)；**流量突然變乾淨、或懷疑統計整個壞掉**走[假故障與靜默失效的診斷](/automation/06-reading-the-data/diagnosing-silent-failures/)。

## 跨分類引用

- → [模組二：流量 beacon 實作](/automation/02-analytics-beacon/)：payload 的基本欄位與 CORS 障礙，本章的補強都疊在那個實作上
- → [模組三：Sheets 當資料庫](/automation/03-sheet-as-database/)：欄位增加後的資料模型與容量影響
- → [模組五：部署、配額與安全](/automation/05-deploy-quota-security/)：隱私邊界與防濫用的完整討論，本章的 opt-out 是那一章「過濾自己的瀏覽」的具體實作
- → [Monitoring 的事件分類](/monitoring/)：要收哪些事件、怎麼分類的概念層
- → [Monitoring 的行為資料商業利用](/monitoring/)：漏斗、cohort 與歸因的分析框架，本章只處理自建管線的資料品質
