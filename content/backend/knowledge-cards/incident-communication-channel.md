---
title: "Incident Communication Channel"
date: 2026-04-23
description: "說明事故期間內外部溝通要使用哪些固定通道與節奏"
weight: 155
---

Incident communication channel 的核心概念是「事故期間用固定通道承接對內同步、對外公告與跨角色協作」。它關心的是誰在什麼通道收到什麼資訊，而不是技術傳輸格式。 可先對照 [Incident Command System](/backend/knowledge-cards/incident-command-system/)。

## 跟其他概念的關係

Incident communication channel 位在 [incident command system](/backend/knowledge-cards/incident-command-system/)、[incident timeline](/backend/knowledge-cards/incident-timeline/) 與對外通知流程之間。它讓指揮者、執行者、利害關係人與客服能在同一節奏上更新狀態。

## 可觀察訊號與例子

系統需要 incident communication channel 的訊號是事故時資訊散落在多個聊天群、會議室與郵件串，導致外部說法不一致。常見例子包括內部 war room、對外 status update、客服同步與管理層簡報。

## 判斷條件與後果

只有一個主要通道而它在事故中無法使用時，指揮者與執行者失去同步的位置，資訊散落到私訊、會議室與郵件串，所以備援通道要事先約定。更新頻率沒有約定時，利害關係人與客服在兩次更新之間各自去問執行者，打斷處置；對象沒有分層時，管理層、客服與工程收到同一份訊息，各自需要的資訊都不完整；發言權限沒有指定時，對外說法來自不同的人，外部看到的說法不一致。對外公告與內部推進放在同一個通道時，內部還在驗證的假設會被當成定論轉述出去，原因是讀那個通道的人分不出哪一則已經確認，所以對外公告另開通道，由有發言權限的人發。
