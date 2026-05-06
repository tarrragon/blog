---
title: "Idle Timeout"
tags: ["閒置逾時", "Idle Timeout"]
date: 2026-04-24
description: "說明連線或會話在多久沒有活動後應該被回收"
weight: 132
---


Idle Timeout 的核心概念是「一段時間沒有活動就關閉連線或回收會話」。它和一般 request timeout 不同，重點不是等待單次操作完成，而是避免空閒連線長時間佔住資源。 可先對照 [Impact Scope](/backend/knowledge-cards/impact-scope/)。

## 概念位置

Idle Timeout 位在 socket、load balancer、proxy、application 與 connection pool 之間。它常用來保護連線資源，避免長時間閒置造成檔案描述符、memory 或 session state 浪費。 可先對照 [Impact Scope](/backend/knowledge-cards/impact-scope/)。

## 可觀察訊號

系統需要 idle timeout 的訊號是：

- 長連線長時間沒有資料交換
- 空閒連線數量持續累積
- load balancer 或 proxy 需要回收無效連線

## 接近真實網路服務的例子

WebSocket 連線、HTTP keep-alive、反向代理連線池或 application 內部 socket pool，常會透過 idle timeout 回收不再使用的連線。

## 設計責任

設計時要定義閒置判定條件、關閉前通知、重連策略與是否允許不同層級使用不同 timeout。Idle Timeout 應該和 read/write timeout、request timeout 區分開來，避免把不同問題混在一起。
