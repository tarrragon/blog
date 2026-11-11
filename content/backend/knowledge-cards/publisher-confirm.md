---
title: "Publisher Confirm"
date: 2026-04-23
description: "說明 producer 如何確認 broker 已接收並承擔訊息"
weight: 68
---

Publisher confirm 的核心概念是「producer 取得 broker 已接收訊息的確認」。它讓 producer 區分訊息已交給 broker，或在發送途中失敗。 可先對照 [Queue Contract](/backend/knowledge-cards/queue-contract/)。

## 跟其他概念的關係

Publisher confirm 是發布可靠性的下半段。Application 寫出事件後，仍需要確認 broker 是否承擔保存或投遞責任；若 confirm 失敗，producer 要重試、寫 outbox 或回報錯誤。 可先對照 [Queue Contract](/backend/knowledge-cards/queue-contract/)。

## 可觀察訊號與例子

系統需要 publisher confirm 的訊號是事件遺失會造成後續流程漏執行。訂單付款後發布出貨事件時，producer 需要知道 broker 是否成功接收，否則倉儲服務可能永遠收不到事件。

## 判斷條件與後果

Publisher confirm 只告訴 producer 訊息有沒有被 broker 接收，收不到確認之後的行為由搭配的機制決定。沒有 timeout 時，producer 對遲遲不回的確認一直等下去；有 retry 而下游沒有 idempotency 時，確認遺失、訊息已經送達的那一筆被送兩次，下游處理兩次。沒有 outbox 時，application 寫入資料庫之後、取得確認之前 crash，那個事件不會再被發布，倉儲服務收不到出貨事件。觀測上記錄 publish attempt、confirm latency、confirm failure 與未確認事件數；未確認事件數持續累積，代表有一批事件處在可能遺失的狀態。
