---
title: "執行配額"
date: 2026-07-06
description: "Apps Script 個人帳號的執行時間、同時併發與觸發器每日總時間上限，決定免費膠水層能承受多大的量"
weight: 4
tags: ["automation", "apps-script", "quota", "knowledge-card"]
---

執行配額是 Apps Script 對免費個人帳號設的一組執行上限，決定膠水層能承受多大的量。對個人（gmail.com）帳號，關鍵的三條是：單次執行最長 6 分鐘、同時併發最多 30 個執行、觸發器每日總執行時間 90 分鐘。理解這些上限才能判斷免費夠不夠，選型的完整討論見[免費額度的思考方式與工具選型](/automation/00-mental-model/free-tier-and-tool-choice/)。配額同時限制 [web app 部署](/automation/knowledge-cards/web-app-deployment/) 端點的併發與[時間觸發器](/automation/knowledge-cards/time-driven-trigger/)的總執行時間。

## 概念位置

觸發器的 90 分鐘每日總時間是另一條線，影響的是[時間觸發器](/automation/knowledge-cards/time-driven-trigger/)做的排程彙總，不是接收 beacon。

## 可觀察訊號與例子

估算容量時該看的是**併發**而非總量。接收 [beacon](/automation/knowledge-cards/beacon/) 的膠水層，每次執行只寫一筆、幾百毫秒結束，遠用不到 6 分鐘；binding 的限制是「同一瞬間最多 30 個 beacon 在處理」。個人 blog 的流量分散在整天、任何瞬間的併發都遠低於 30，所以不會撞牆；會逼近上限的是「某篇文章短時間爆量」這種尖峰。

## 判讀方式

值得注意的是個人帳號的配額比 Google Workspace 帳號低，所以同一段程式在測試帳號能過、在別的帳號可能撞限。碰到配額上限的處理見[模組五](/automation/05-deploy-quota-security/)。
