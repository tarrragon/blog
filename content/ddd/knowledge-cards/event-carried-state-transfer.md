---
title: "Event-Carried State Transfer"
tags: ["event-carried-state-transfer", "domain-event", "state-stream"]
date: 2026-07-20
description: "跨服務的 domain event payload 開始塞進足量當前狀態、要判斷這是正當設計還是載體誤用時使用。event-carried state transfer 是刻意讓事件攜帶足量狀態、讓下游服務不必回頭查詢來源的設計。"
weight: 22
---

event-carried state transfer 是刻意讓 [domain event](/ddd/knowledge-cards/domain-event/) 的 payload 攜帶足量的當前狀態、不只是「發生了什麼」的事實本身。目的是讓下游服務收到事件後就能拿到完整資訊、不必回頭同步查詢來源系統——payload 帶全量狀態在這裡是設計選擇，不是把事件當狀態通知的誤用。

## 概念位置

這個設計只在跨服務、跨信任邊界的情境下成立。同進程情境下，事件開始攜帶全量狀態通常是載體錯位的訊號——消費者真正要問的是「現在是什麼」，正確載體是 [state stream](/ddd/knowledge-cards/state-stream/) 而非塞胖的事件；跨服務時「回頭查詢來源」本身有同步耦合的成本，event-carried state transfer 用胖 payload 換掉這個成本，是同一個訊號在不同信任邊界下的相反判讀，完整推導見 [domain event 與狀態流](/ddd/domain-event-vs-state-stream/)。

## 可觀察訊號

事件的 payload 從「哪本書、什麼時間」這類事實欄位，長出「現在的全貌」這類當前狀態欄位，是判讀的觸發點；判讀不看 payload 胖不胖，看消費者是不是跟事件來源在同一個信任邊界——邊界內是錯位、邊界外是正當設計。

## 設計責任

event-carried state transfer 換來的是下游服務不必為了拿到完整資訊而同步呼叫來源，代價是事件 payload 的 schema 跟著狀態演進、下游要一起處理相容性。這個代價只有在真的省下跨服務同步查詢時才划算，同進程情境沒有這筆成本可省，應優先考慮 [state stream](/ddd/knowledge-cards/state-stream/)。
