---
title: "模組一：Apps Script 地基"
date: 2026-07-06
description: "搞懂 Apps Script 的 web app 部署模型與授權模型，才不會在做 beacon 時卡在網址打不通或權限被擋"
weight: 2
tags: ["automation", "apps-script", "web-app", "authorization"]
---

回答「Apps Script 到底是什麼、它跟一台伺服器差在哪」。這一章打的是地基：`doGet`/`doPost` 進入點、部署成 web app 的模型、以及「執行身分」與「誰可存取」這兩個授權設定的含義。把地基搞懂，模組二做 beacon 時遇到的網址與權限狀況就不再是黑盒。

Apps Script 是 Google 托管的 JavaScript 執行環境，跑在 V8 runtime 上，對個人帳號免費。它跟一般伺服器最大的差別是沒有一台常駐主機——程式只在被呼叫時執行、跑完就休眠，你不必管作業系統、不必管開機關機、不必付閒置費用。代價是它有執行時間與併發上限（見[模組零：免費額度的思考方式](/automation/00-mental-model/free-tier-and-tool-choice/)）。

## 章節文章

| 文章                                                                                             | 主題                                                                       |
| ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| [Apps Script 是什麼、跟一般伺服器差在哪](/automation/01-apps-script-basics/what-is-apps-script/) | 無主機執行模型、容器綁定 vs 獨立專案、沒有常駐程序的取捨、用到的服務       |
| [web app 部署模型與授權](/automation/01-apps-script-basics/web-app-deployment-model/)            | `doGet`/`doPost`、`exec` 與 `dev` 兩種網址、更新部署不換網址、首次授權警告 |

## 跨分類引用

- → [模組零：免費額度的思考方式與工具選型](/automation/00-mental-model/free-tier-and-tool-choice/)：為什麼選 Apps Script
- → [模組二：流量 beacon 實作](/automation/02-analytics-beacon/)：把地基用在實作上
