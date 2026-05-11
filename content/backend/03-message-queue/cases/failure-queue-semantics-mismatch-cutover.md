---
title: "3.C9 反例：Queue 語義切換誤配"
date: 2026-05-07
description: "at-least-once / exactly-once 語義誤配導致資料重複與遺漏。"
weight: 9
tags: ["backend", "message-queue", "case-study"]
---

這個反例的核心責任是說明 broker 遷移失敗常發生在語義假設錯置。

## 事故長相

切換 broker 或 consumer group 後，表面上訊息仍然被送達，但業務資料開始出現重複扣款、重複寄信、狀態漏更新這類問題。這種事故很難只靠 queue depth 判斷，因為錯誤發生在「處理語義」而不是「是否有訊息」。

## 為什麼會擴大

舊系統若依賴特定 offset 行為、重試節奏或 consumer idempotency，新系統即使名稱上提供相近 delivery semantics，也可能在失敗重播時產生不同結果。語義誤配會沿著下游資料寫入擴散。

## 回退判讀

回退前要先確認哪一段資料已經被新語義處理過。若直接切回舊 broker，可能讓同一批事件再次被處理。更穩定的做法是先凍結新 consumer，保留 offset 對照與 replay 範圍，再決定補償或重播。

## Queue 專屬告警條件

- 下游 reconciliation 同時出現重複與遺漏
- DLQ 激增且重播後仍回到相同錯誤
- consumer lag 下降但業務結果沒有收斂

## 下一步路由

回 [3.4](/backend/03-message-queue/consumer-design/) 與 [6.10](/backend/06-reliability/contract-testing/)。
