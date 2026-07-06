---
title: "模組二：流量 beacon 實作"
date: 2026-07-06
description: "把「頁面被看了就送一則事件、接收端寫進 Sheet」從零做到收到第一筆真實瀏覽紀錄時的完整實作"
weight: 3
tags: ["automation", "beacon", "apps-script", "sendbeacon", "cors"]
---

把模組零的 client beacon 架構真的做出來：前端在頁面載入時送一則瀏覽事件，Apps Script 接住它、寫進 Google Sheet。這一章的終點是「打開試算表，看到自己剛剛的瀏覽出現在第一列」。

實作拆成兩半，剛好對應架構的兩端。前端這半的重點是用對送出方式，避開靜態站打 Apps Script 最常見的 CORS 障礙。接收端這半的重點是把請求解析出來、安全地 append 進試算表。

## 章節文章

| 文章                                                                            | 主題                                                                            |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| [前端 beacon 與 CORS 障礙](/automation/02-analytics-beacon/frontend-beacon/)    | 用 `sendBeacon` 送 `text/plain` 避開 preflight、beacon 該送什麼、放進 Hugo 哪裡 |
| [接收端 handler：寫進第一筆](/automation/02-analytics-beacon/receiver-handler/) | `doPost` 解析請求、`appendRow` 寫進 Sheet、部署後收到第一筆瀏覽                 |

## 跨分類引用

- → [模組一：Apps Script 地基](/automation/01-apps-script-basics/)：`doGet`/`doPost` 與部署模型的完整說明
- → [模組三：Sheets 當資料庫](/automation/03-sheet-as-database/)：資料進來後的並發、資料模型與容量
