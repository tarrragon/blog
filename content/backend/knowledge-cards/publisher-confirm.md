---
title: "Publisher Confirm"
date: 2026-04-23
description: "說明 producer 如何確認 broker 已接收並承擔訊息"
weight: 67
---


Publisher confirm 的核心概念是「producer 取得 broker 已接收訊息的確認」。它讓 producer 區分訊息已交給 broker，或在發送途中失敗。 可先對照 [Queue Contract](/backend/knowledge-cards/queue-contract/)。

## 概念位置

Publisher confirm 是發布可靠性的下半段。Application 寫出事件後，仍需要確認 broker 是否承擔保存或投遞責任；若 confirm 失敗，producer 要重試、寫 outbox 或回報錯誤。 可先對照 [Queue Contract](/backend/knowledge-cards/queue-contract/)。

## 可觀察訊號與例子

系統需要 publisher confirm 的訊號是事件遺失會造成後續流程漏執行。訂單付款後發布出貨事件時，producer 需要知道 broker 是否成功接收，否則倉儲服務可能永遠收不到事件。

## 設計責任

Publisher confirm 要搭配 timeout、retry、outbox 與 idempotency。觀測上要記錄 publish attempt、confirm latency、confirm failure 與未確認事件數。
