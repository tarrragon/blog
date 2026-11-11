---
title: "Idle Timeout"
tags: ["閒置逾時", "Idle Timeout"]
date: 2026-04-24
description: "說明連線或會話在多久沒有活動後應該被回收"
weight: 133
---

Idle Timeout 的核心概念是「一段時間沒有活動就關閉連線或回收會話」。它和一般 request timeout 不同，重點是避免空閒連線長時間佔住資源，跟等待單次操作完成的 request timeout 不同。 可先對照 [Impact Scope](/backend/knowledge-cards/impact-scope/)。

## 跟其他概念的關係

Idle Timeout 位在 socket、load balancer、proxy、application 與 connection pool 之間。它常用來保護連線資源，避免長時間閒置造成檔案描述符、memory 或 session state 浪費。 可先對照 [Impact Scope](/backend/knowledge-cards/impact-scope/)。

## 可觀察訊號

系統需要 idle timeout 的訊號是：

- 長連線長時間沒有資料交換
- 空閒連線數量持續累積
- load balancer 或 proxy 需要回收無效連線

## 接近真實網路服務的例子

WebSocket 連線、HTTP keep-alive、反向代理連線池或 application 內部 socket pool，常會透過 idle timeout 回收不再使用的連線。

## 判斷條件與後果

Idle timeout 的判斷條件是連線路徑上各層的閒置判定是否一致。load balancer、proxy 與 application 各自設 idle timeout 時，最短的那一層先關閉連線，另一端仍以為連線可用，下一個請求送進已關閉的連線而失敗；client 有重連策略時，這次失敗換成一次重連，沒有時直接變成錯誤。關閉之前沒有通知對端時（WebSocket 的 close frame 這類），對端要等下一次讀寫才發現連線斷了。idle timeout 量的是兩次活動之間的空檔，read/write timeout 與 request timeout 量的是單次操作的等待，兩者混用時，為了一種情形調整數值會改到另一種：為了讓慢查詢做完而拉長 idle timeout，閒置連線也跟著佔住資源更久。
