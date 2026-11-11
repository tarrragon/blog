---
title: "Domain Event"
tags: ["domain-event", "event-driven", "ddd"]
date: 2026-07-16
description: "系統裡出現「為了讓某頁刷新而補發事件」或「監聽端掛全事件過濾器」時使用。domain event 是已發生的業務事實——過去式命名、發布後不可變、錯過代表事實遺失。"
weight: 15
aliases: ["/ddd/knowledge-cards/domain-event/"]
---

domain event 是一筆已發生的業務事實的記錄：過去式命名（`BookAdded`、`OrderPaid`）、發布後不可變、消費者關心「發生了什麼」。跟 [snapshot](/software-design/ddd/knowledge-cards/snapshot/) 的差別在時間語意：snapshot 記的是某時刻的狀態（現在式），event 記的是某時刻發生的事（過去式）。與狀態流的差別在錯過的代價：event 錯過代表事實遺失（審計斷檔、下游流程沒觸發），狀態流錯過無代價（下一次快照涵蓋一切）。

## 跟其他概念的關係

domain event 是 [aggregate root](/software-design/ddd/knowledge-cards/aggregate-root/) 執行業務操作後的副產品——aggregate 保證一致性、event 把「剛才發生的事」通知外界。event 的消費者是跨 domain 流程、審計、通知等「需要知道發生了什麼」的角色。它跟 [read model](/software-design/ddd/knowledge-cards/read-model/) 在 CQRS 第四階交會：讀模型由事件同步時，消費者問的確實是「發生了什麼」（用事實重建投影），這是 event 的合法消費。

## 可觀察訊號

event 被借用成 UI 刷新訊號時會出現四個判讀訊號：為了讓某頁刷新而補發事件、監聽端掛全事件過濾器、移除事件前要查有沒有畫面靠它刷新、event payload 開始塞當前完整狀態。任一出現，回到載體判斷標準重新選——消費者問「現在是什麼」時，正確載體是狀態流。

## 判斷條件與後果

選 domain event 還是 [狀態流](/software-design/ddd/knowledge-cards/state-stream/) 當載體，看消費者要知道的是「發生了什麼」還是「現在是什麼」。審計、跨 domain 流程這類消費者要的是逐筆事實：event 漏掉一筆，審計就斷檔、下游流程就沒有被觸發，原因是事實只在發生的那一刻被記錄一次。只要資料當前值的消費者（畫面刷新）拿 event 當訊號時，event 的發布點由業務語意決定（「這件事值得記錄、有下游需要它」），涵蓋面是業務事實的集合，跟寫入操作的集合不相等，某個寫入路徑沒有對應的事件，那個畫面就停在舊值；狀態流的 emit 寫在每個寫入方法尾端，涵蓋面等於寫入操作的集合，所以這類消費者的載體是狀態流。載體選用標準、案例演進與判讀訊號展開在 [domain event 與狀態流](/software-design/ddd/domain-event-vs-state-stream/)；事件對命令與查詢的責任結構分界展開在 [domain event 與命令、查詢](/software-design/ddd/domain-event-vs-command-and-query/)。命名的過去式約定展開在 [Domain Event 命名的過去式](/work-log/domain_event_naming_past_tense/)。
