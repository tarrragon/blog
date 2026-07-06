---
title: "表單與事件觸發器"
date: 2026-07-06
slug: "form-and-event-triggers"
description: "由 Google 檔案事件（表單提交、試算表編輯）觸發的 Apps Script，以及 simple 與 installable 觸發器在權限上的差別"
weight: 2
tags: ["automation", "apps-script", "trigger", "onformsubmit", "event-driven"]
---

事件觸發器讓 Apps Script 在「某個 Google 檔案發生某件事」的當下自動執行，跟時間觸發器的「到點就跑」互補。最常用的是 `onFormSubmit`（有人提交 Google 表單）跟 `onEdit`（有人編輯試算表）。這一篇講事件觸發器能做什麼、以及一個容易踩的權限分界。

## onFormSubmit：表單提交即時處理

Google 表單本身會把回應存進一張試算表，但「存進去之後要做什麼」需要 Apps Script。`onFormSubmit` 觸發器在每次有人提交表單時執行，拿得到這次提交的內容：

```javascript
function onFormSubmit(e) {
  var answers = e.namedValues;        // { "Email": ["a@b.com"], "問題": ["內容"] }
  // 例如：寄一封通知信給自己
  MailApp.sendEmail("you@gmail.com", "新表單回應", JSON.stringify(answers));
}
```

這讓表單從「被動收集」變成「即時反應」——提交當下就寄通知、寫進別的表、或呼叫外部 API。對 blog 的延伸應用，例如做一個「訂閱通知」或「回饋表單」，`onFormSubmit` 是接手處理的入口。要注意 `MailApp.sendEmail` 受每日寄信配額約束（個人帳號每天 100 封收件人，見[執行配額](/automation/knowledge-cards/execution-quota/)），高頻通知要留意。

## onEdit：試算表被編輯

`onEdit` 在試算表任何一格被改動時觸發，拿得到改了哪一格、新值是什麼。它適合「維護試算表內部的衍生狀態」，例如某欄被填值時自動在旁邊算出對應結果。對流量統計這條主線用得不多，但它是 Sheets 自動化的常見工具，值得知道它存在。

## simple 與 installable：一個權限分界

事件觸發器有兩種形式，差別在**能不能做需要授權的事**，這是容易踩的分界。

**Simple 觸發器**是靠函式命名約定自動生效的：把函式命名為 `onOpen`、`onEdit` 這些保留名字，不必註冊就會在對應事件觸發。代價是它跑在受限環境裡——**不能做需要授權的操作**，例如寄信、呼叫外部 URL、存取其他檔案。它適合純粹在當前檔案內、不碰外部的輕量反應。

**Installable 觸發器**是明確註冊的（用 `ScriptApp.newTrigger(...).forSpreadsheet(...).onEdit().create()`，或在觸發條件介面建立），它以你的授權身分執行，**能做需要權限的操作**（寄信、UrlFetch、跨檔案）。`onFormSubmit` 要做寄信這類事，必須是 installable 的。

判準很直接：**這個事件處理要不要碰當前檔案以外的東西**——不要（只在表內算個值），simple 夠用；要（寄信、打 API、寫別的表），得用 installable。踩雷的典型情境是「我寫了一個 `onFormSubmit` 想寄通知信，怎麼都沒寄出」——因為它被當成 simple 觸發器、而 simple 不能寄信；改成明確註冊的 installable 就好。

## 下一步

觸發器（時間的與事件的）把統計從「手動查」變成「自動跑」。整套統計上線後怎麼守住配額、擋濫用、保持資料乾淨，見[模組五：部署、配額與安全](/automation/05-deploy-quota-security/)。
