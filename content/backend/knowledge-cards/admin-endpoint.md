---
title: "Admin Endpoint"
tags: ["管理端點", "Admin Endpoint"]
date: 2026-04-23
description: "說明管理入口如何承擔高權限操作與稽核責任"
weight: 1
---

Admin Endpoint 的核心概念是「只給受信任角色使用的高權限入口」。它通常處理管理、調整、匯出或修正資料的操作。 可先對照 [Alert Fatigue](/backend/knowledge-cards/alert-fatigue/)。

## 跟其他概念的關係

Admin Endpoint 位在內部網路、身份驗證與授權層之後，和一般 public API 分開管理。 可先對照 [Alert Fatigue](/backend/knowledge-cards/alert-fatigue/)。

客服後台上停用帳號、退款這類寫入按鈕背後呼叫的就是 admin endpoint；客服後台本身以讀取為主，讀取那一側的欄位、遮罩與查詢紀錄見 [Internal Admin Tool（客服後台）](/backend/knowledge-cards/internal-admin-tool/)。

## 可觀察訊號

系統需要 admin endpoint 的訊號是操作會影響大量使用者、資料完整性或金流狀態，且需要額外稽核與來源限制。

## 接近真實網路服務的例子

後台修改使用者角色、停用帳號、調整活動規則、匯出敏感報表，都應透過 admin endpoint 完成，並保留 audit log。

## 判斷條件與後果

Admin Endpoint 一次操作就能改到大量使用者、資料完整性或金流狀態，所以它的防護依這個代價比 public API 高一級，每一項防護不足各有對應的後果。身份驗證只有一般使用者的強度時，任何一個被盜的後台帳號都能呼叫它；授權沒有細分時，持有後台權限的人都能做全部的修改；沒有來源限制時，入口對整個網際網路開放，憑證一外洩就能直接使用；沒有操作追蹤時，帳號被停用或角色被改之後查不出是誰做的；錯誤回應寫出內部細節時，任何呼叫得到它的人都能從錯誤訊息推回後台的內部結構。
