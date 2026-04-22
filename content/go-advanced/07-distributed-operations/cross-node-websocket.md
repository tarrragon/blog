---
title: "7.3 跨節點 WebSocket、presence 與重連協定"
date: 2026-04-22
description: "把單一 server 的 WebSocket hub 擴展到多節點推送與連線狀態"
weight: 3
---

跨節點 WebSocket 的核心責任是把連線狀態、訂閱狀態與推送路徑從單一記憶體 hub 延伸到多台 server。單一 process 內的 read pump、write pump、heartbeat 與 slow client 策略仍然有效，但跨節點後還需要 broker、presence store、重連協定與授權邊界。

## 前置章節

- [Go 進階：read pump / write pump 模式](../02-networking-websocket/read-write-pump/)
- [Go 進階：heartbeat、deadline 與連線清理](../02-networking-websocket/heartbeat-deadline/)
- [Go 進階：訂閱模型與訊息路由](../02-networking-websocket/subscription-routing/)
- [Go 進階：慢客戶端與 send buffer 管理](../02-networking-websocket/slow-client/)

## 後續撰寫方向

1. 多台 server 如何知道某個 topic 的訂閱者在哪些節點。
2. Presence store 如何記錄 client online、offline 與最後活動時間。
3. Broker fan-out 如何和每個節點本地 send buffer 策略銜接。
4. Client reconnect 如何使用 cursor、last event ID 或 snapshot 補資料。
5. Topic ACL 與 subscription authorization 應放在 router、usecase 還是 gateway。

## 本章不處理

本章不會選定特定 broker 或 presence database。重點是先讓跨節點責任可見，再依服務需求選擇 Redis、NATS、Kafka、PostgreSQL 或其他基礎設施。
