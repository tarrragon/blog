---
title: "Queue Contract"
date: 2026-04-23
description: "說明佇列工作在重試、確認與重複投遞上的約定"
weight: 1
---

Queue Contract 的核心概念是「producer、queue 與 consumer 對工作如何被確認與重送達成一致」。它描述的是交付語意，而不是單純的格式。 可先對照 [Queue Depth](/backend/knowledge-cards/queue-depth/)。

## 跟其他概念的關係

Queue Contract 位在 producer、broker 與 consumer 之間。當工作要可靠排隊與重試時，就需要清楚的 contract。 可先對照 [Queue Depth](/backend/knowledge-cards/queue-depth/)。

## 可觀察訊號

系統需要 queue contract 的訊號是工作可能重試、可能重複投遞，且 consumer 需要知道確認失敗後會發生什麼。

## 接近真實網路服務的例子

ack / nack、retry、dead-letter、duplicate delivery 與 redelivery 都屬於 queue contract 的範圍。

## 判斷條件與後果

Queue contract 的判斷條件是 broker 與 consumer 對同一個失敗結果的理解是否一致。確認語意沒有約定時，consumer 處理完卻沒在 broker 預期的時間內 ack，broker 判定失敗而重送，同一份工作被做兩次；重試策略與重送條件沒有約定時，每次都會失敗的訊息被反覆重送，形成 [redelivery loop](/backend/knowledge-cards/redelivery-loop/)。隔離方式沒有約定時，處理不了的訊息留在主 queue 裡，持續佔用 consumer；去重責任沒有指定給 producer、broker 或 consumer 其中一方時，每一方都以為由別方去重，重複投遞直接變成重複的副作用。
