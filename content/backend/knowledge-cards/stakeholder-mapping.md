---
title: "Stakeholder Mapping"
tags: ["利害關係人地圖", "Stakeholder Mapping"]
date: 2026-05-02
description: "說明事故期間如何把通報對象分層與對應 owner"
weight: 315
---

Stakeholder mapping 的核心概念是「把誰需要知道什麼、由誰負責、在什麼節奏通知」先畫清楚。它和 [incident communication channel](/backend/knowledge-cards/incident-communication-channel/) 以及 [status page](/backend/knowledge-cards/status-page/) 一起決定通報的分層。

## 跟其他概念的關係

Stakeholder mapping 位在 [incident communication channel](/backend/knowledge-cards/incident-communication-channel/)、[escalation policy](/backend/knowledge-cards/escalation-policy/) 與 [post-incident-review](/backend/knowledge-cards/post-incident-review/) 之間。它把內部、客戶、管理層、法務與監管需求拆開，避免事故中漏通知或重複通知。

## 可觀察訊號與例子

系統需要 stakeholder mapping 的訊號是事故時通知對象不固定、每次都靠記憶補。常見例子包括：客戶已受影響但 account team 沒收到、法務通報窗口被錯過、或補償政策需要臨時討論。

## 判斷條件與後果

Stakeholder mapping 固定的是責任鏈：哪一群人在什麼條件下、由誰通知、多久通知一次，每一環缺席都對應一種通報失誤。沒有角色群組時，通知對象每次靠記憶補，客戶已受影響而 account team 沒收到通知；有群組而沒有 owner 時，每個群組的通知沒有指定的執行者，事故中可能沒有人送出，或兩個人各送一次；沒有通知頻率時，同一群人在事故中被重複通知，或長時間收不到更新；沒有升級條件時，影響擴大到需要法務或監管通報的程度，通報窗口仍可能被錯過；沒有例外處理時，補償政策這類名單之外的決定要在事故當下臨時討論。這些缺口跟名單長度無關，名單再長，缺了 owner 與升級條件，通報照樣會漏。
