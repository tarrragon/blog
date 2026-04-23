---
title: "7.3 跨節點 WebSocket、presence 與重連協定"
date: 2026-04-22
description: "把單一 server 的 WebSocket hub 擴展到多節點推送與連線狀態"
weight: 3
---

跨節點 WebSocket 的核心責任是把連線狀態、訂閱狀態與推送路徑從單一記憶體 hub 延伸到多台 server。單一 process 內的 read pump、write pump、heartbeat 與 slow client 策略仍然有效，但跨節點後還需要 broker、presence store、重連協定與授權邊界。

## 本章目標

學完本章後，你將能夠：

1. 理解單節點 hub 為什麼不夠
2. 看懂 presence store 與 broker 在系統中的角色
3. 設計 reconnect 後的補資料流程
4. 分辨訂閱路由、連線管理與授權邊界
5. 讓多台 server 在語意上看起來像同一個訊息系統

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

## 【觀察】跨節點 WebSocket 的核心問題是狀態協調

WebSocket 協定解決的是單一連線的雙向通訊，但跨節點之後，真正麻煩的是狀態分散在多台 server。某個 client 可能連到 A 節點，但它關注的 topic 事件卻從 B 節點產生，這時就需要能夠路由、轉送與補資料。

所以跨節點 WebSocket 的問題不只是「能不能推送」，而是：

- 這個 client 現在在哪台 server
- 它訂閱了哪些 topic
- 推送失敗後要不要重送
- 重新連線後要從哪裡補回遺漏事件

## 【判讀】presence store 是操作查詢

presence store 的用途是讓系統知道某個 client 或節點目前大概在線上還是離線。它通常是操作性資料，不一定是業務真相。

常見欄位包括：

- client ID
- node ID
- connected at
- last seen
- subscription keys

這類資料要允許過期與清理，因為斷線、網路抖動與 crash 都可能讓狀態暫時不準。

## 【策略】reconnect 一定要有補資料設計

只靠重新連上 WebSocket 並不能保證使用者不漏訊息。當連線中斷時，常見的補資料方式有：

- last event ID
- cursor / offset
- snapshot + delta

選哪一種，取決於你的事件是否可排序、是否可回放，以及業務能容忍多大的缺口。

## 【執行】推送路徑通常要分三層

跨節點場景下，推送路徑常見會分成：

1. 事件產生端把訊息交給 broker 或 routing layer。
2. 節點收到後，交給本機 hub / connection manager。
3. write pump 再把訊息送到單一 client。

這樣可以維持單一寫入者原則，避免多個 goroutine 同時寫 WebSocket。

## 【延伸】授權應該在進入路由前就處理

Topic ACL 不是事後濾掉訊息而已，而是要在訂閱建立時就知道這個 client 是否有資格加入。這能減少不必要的 fan-out 與敏感資料外流。

## 本章不處理

本章不會選定特定 broker 或 presence database。重點是先讓跨節點責任可見，再依服務需求選擇 Redis、NATS、Kafka、PostgreSQL 或其他基礎設施。

## 和 Go 教材的關係

這一章承接的是 WebSocket 連線架構與事件路由；如果你要先回看語言教材，可以讀：

- [Go 進階：read/write pump 模式](../02-networking-websocket/read-write-pump/)
- [Go 進階：heartbeat、deadline 與連線清理](../02-networking-websocket/heartbeat-deadline/)
- [Go 進階：訂閱模型與訊息路由](../02-networking-websocket/subscription-routing/)
- [Go 進階：慢客戶端與 send buffer 管理](../02-networking-websocket/slow-client/)
