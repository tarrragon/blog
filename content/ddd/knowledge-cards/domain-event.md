---
title: "Domain Event"
tags: ["domain-event", "event-driven", "ddd"]
date: 2026-07-16
description: "系統裡出現「為了讓某頁刷新而補發事件」或「監聽端掛全事件過濾器」時使用。domain event 是已發生的業務事實——過去式命名、發布後不可變、錯過代表事實遺失。"
weight: 15
---

domain event 是一筆已發生的業務事實的記錄：過去式命名（`BookAdded`、`OrderPaid`）、發布後不可變、消費者關心「發生了什麼」。跟 [snapshot](/ddd/knowledge-cards/snapshot/) 的差別在時間語意：snapshot 記的是某時刻的狀態（現在式），event 記的是某時刻發生的事（過去式）。與狀態流的差別在錯過的代價：event 錯過代表事實遺失（審計斷檔、下游流程沒觸發），狀態流錯過無代價（下一次快照涵蓋一切）。

## 概念位置

domain event 是 [aggregate root](/ddd/knowledge-cards/aggregate-root/) 執行業務操作後的副產品——aggregate 保證一致性、event 把「剛才發生的事」通知外界。event 的消費者是跨 domain 流程、審計、通知等「需要知道發生了什麼」的角色。它跟 [read model](/ddd/knowledge-cards/read-model/) 在 CQRS 第四階交會：讀模型由事件同步時，消費者問的確實是「發生了什麼」（用事實重建投影），這是 event 的合法消費。

## 可觀察訊號

event 被借用成 UI 刷新訊號時會出現四個判讀訊號：為了讓某頁刷新而補發事件、監聽端掛全事件過濾器、移除事件前要查有沒有畫面靠它刷新、event payload 開始塞當前完整狀態。任一出現，回到載體判準重新選——消費者問「現在是什麼」時，正確載體是狀態流。

## 設計責任

domain event 記錄業務事實、服務審計與跨 domain 通訊。event 的發布時機由業務語意決定（「這件事值得記錄、有下游需要它」），涵蓋面是業務事實的集合——跟狀態流的涵蓋面（寫入操作的集合，結構性涵蓋）正交。載體選用判準、案例演進與判讀訊號展開在 [domain event 與狀態流](/ddd/domain-event-vs-state-stream/)；事件對命令與查詢的責任結構分界展開在 [domain event 與命令、查詢](/ddd/domain-event-vs-command-and-query/)。命名的過去式約定展開在 [Domain Event 命名的過去式](/work-log/domain_event_naming_past_tense/)。
