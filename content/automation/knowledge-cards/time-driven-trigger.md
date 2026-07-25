---
title: "Time-Driven Trigger（時間觸發器）"
date: 2026-07-06
description: "讓 Apps Script 在固定時間自動執行的排程機制，把被動等呼叫的膠水層變成主動定時跑的任務"
weight: 5
tags: ["automation", "apps-script", "trigger", "scheduling", "knowledge-card"]
---

時間觸發器（time-driven trigger）是讓 Apps Script 在固定時間自動執行某個函式的排程機制。它把膠水層從「被動等 HTTP 請求呼叫」（見 [doGet / doPost](/automation/knowledge-cards/doget-dopost/)）變成「主動定時執行」——不需要有人打網址，到點就自己跑。

## 概念位置

流量統計用它把 [beacon](/automation/knowledge-cards/beacon/) 累積的原始 log 每天彙總成一張日報表，實作見[模組四](/automation/04-triggers-automation/)。

## 可觀察訊號與例子

時間觸發器可以設成每分鐘、每小時、每天固定時段、或每週執行。典型用法是「每天凌晨把前一天的 raw log 依日期與路徑 group 成彙總表」，讓人打開試算表看到的是整理過的數字、而不是逐筆原始紀錄。

## 判讀方式

觸發器的成本受[執行配額](/automation/knowledge-cards/execution-quota/)約束：個人帳號所有觸發器每天總執行時間上限 90 分鐘。所以彙總邏輯要寫得有效率，資料量大時避免每次都全表掃描——這條線在原始 log 累積到很多列時才會逼近，判讀與最佳化見[模組三：Sheets 的容量邊界](/automation/03-sheet-as-database/)。
