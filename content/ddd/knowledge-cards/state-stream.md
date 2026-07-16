---
title: "State Stream（狀態流）"
tags: ["state-stream", "reactive", "ddd"]
date: 2026-07-16
description: "畫面刷新靠補償、或考慮拿既有事件當刷新訊號時使用。狀態流是持續發布「資料當前值」的觀測載體——新值蓋過舊值、錯過中間值無代價，回答「現在是什麼」。"
weight: 16
---

狀態流是持續發布「某份資料當前值」的觀測載體：新值蓋過舊值、只有最新值有意義、錯過中間值無代價——下一次快照涵蓋一切。與 [domain event](/ddd/knowledge-cards/domain-event/) 的分界在消費者的問題：狀態流回答「現在是什麼」、event 回答「發生了什麼」。與 [snapshot](/ddd/knowledge-cards/snapshot/) 的差別在時間方向：snapshot 凍結某一刻、保證歷史不隨現在漂移；狀態流永遠指向現在、舊值被覆蓋是設計語意。

## 概念位置

狀態流是 [觀測出口](/ddd/knowledge-cards/observation-outlet/) 的載體形態：觀測出口定義「資料變了、我能告訴你」這個能力歸屬哪一層、狀態流定義這個通知的語意——連續快照、不是離散事實。它的涵蓋面是寫入操作的集合：emit 掛在每個寫入方法尾端、新路徑必然經過、涵蓋不靠任何人記得發——與 domain event「業務語意決定發布點、逐事實設計」的涵蓋方式正交。

## 可觀察訊號

系統缺狀態流出口時，補償的形狀是訊號：導航返回點出現手動 reload、為了讓某頁刷新而補發事件、監聽端掛全事件過濾器。事件被誤用成狀態流的完整判讀訊號表在 [domain event 與狀態流](/ddd/domain-event-vs-state-stream/)。

## 設計責任

狀態流承擔「畫面、快取、衍生視圖對資料當前值的觀測」，錯過的代價為零是它跟 event 不可互換的原因——需要逐筆事實（審計、下游流程）的消費者拿快照會斷檔。載體選用判準展開見 [domain event 與狀態流](/ddd/domain-event-vs-state-stream/)、實作選型（broadcast、初始值、dispose）見 [StreamProvider 包 repository watch stream](/work-log/flutter_streamprovider_wraps_repository_watch/)。
