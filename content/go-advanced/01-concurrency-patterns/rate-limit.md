---
title: "1.6 rate limiting 與背壓"
date: 2026-04-22
description: "用本地速率限制與背壓策略保護服務入口與下游依賴"
weight: 6
---

rate limiting 的核心責任是把過量輸入轉成可預期的服務行為。服務可以等待、排隊、拒絕、降級或取樣，但這些策略應由程式明確決定，而不是讓 goroutine、channel 或 memory 自行失控。

## 預計補充內容

這些背壓邊界會在下列章節展開：

- [Go 入門：channel：事件流與背壓](../../go/04-concurrency/channel/)：先理解 channel buffer 和等待機制，才知道限流不是只有一種做法。
- [Go 進階：非阻塞送出與事件丟棄策略](non-blocking-send/)：當系統必須在滿載時做出明確選擇，這裡會處理 drop、覆蓋與回錯的語意。
- [Backend：部署平台與網路入口](../../backend/05-deployment-platform/)：跨節點流量治理、gateway 與 quota，屬於平台層責任。

## 本章不處理

本章先處理單一 process 內的輸入控制與背壓；跨節點流量治理、gateway 與 quota 的平台責任，會放在 [Backend：部署平台與網路入口](../../backend/05-deployment-platform/)。

## 與 Backend 教材的分工

本章只處理 Go process 內的速率控制。API gateway、load balancer、service mesh、broker quota 與跨節點流量治理會放在 [Backend：部署平台與網路入口](../../backend/05-deployment-platform/)。

## 和 Go 教材的關係

這一章承接的是 channel 背壓、non-blocking send 與 worker capacity；如果你要先回看語言教材，可以讀：

- [Go：channel：資料傳遞與背壓](../../go/04-concurrency/channel/)
- [Go：select：同時等待多種事件](../../go/04-concurrency/select/)
- [Go：非阻塞送出與事件丟棄策略](non-blocking-send/)
- [Go：bounded worker pool](worker-pool/)
