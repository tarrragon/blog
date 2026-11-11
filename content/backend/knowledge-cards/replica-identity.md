---
title: "Replica Identity"
date: 2026-05-22
description: "說明 row-level 變更事件如何帶穩定 key，讓下游能正確套用 update 與 delete"
weight: 339
---

Replica Identity 的核心概念是一張表對外輸出 row-level 變更時，必須附帶一個穩定的 key，讓下游系統知道每個 update 或 delete 事件要套用到哪一列。它是 [Change Data Capture](/backend/knowledge-cards/change-data-capture/) 與 [Logical Replication](/backend/knowledge-cards/logical-replication/) 能否正確重建資料的前置契約，缺少它時 update / delete 事件無法定位目標列。

## 跟其他概念的關係

Replica Identity 位在變更事件的 schema 契約層。[Change Data Capture](/backend/knowledge-cards/change-data-capture/) 與 [Logical Replication](/backend/knowledge-cards/logical-replication/) 負責把變更傳出去，replica identity 決定那些事件本身帶不帶得出「改了哪一列」。多數情況 primary key 就是 replica identity；沒有 primary key 的表（某些 audit table、join table）要明確補一個唯一 key 或設定 full row image。

## 可觀察訊號與例子

需要檢查 replica identity 的訊號是下游套用 update / delete 時出現資料漂移或事件被丟棄。常見場景是一張沒有 primary key 的表進入 CDC pipeline，insert 事件正常、update / delete 事件卻無法對應目標列。這類問題通常是靜默的 — 資料慢慢不一致，而不是立刻報錯。

## 判斷條件與後果

一張要輸出變更的表是否有穩定的 key，決定下游是否定位得到 update 與 delete 事件的目標列。表有 primary key 時，事件帶著主鍵值，下游照它找到目標列；沒有 primary key、也沒有補唯一鍵時，insert 照常套用，update 與 delete 卻找不到要改的列，下游的資料慢慢漂移而不報錯，原因是事件裡沒有任何欄位對得上一列。改用 full row image 讓事件帶出整列的舊值來定位，代價是每個事件變大、下游比對的成本上升。這類失敗是靜默的，所以下游套用失敗或被略過的 update / delete 事件要有計數與告警。
