---
title: "1.6 rate limiting 與背壓"
date: 2026-04-22
description: "用本地速率限制與背壓策略保護服務入口與下游依賴"
weight: 6
---

rate limiting 的核心責任是把過量輸入轉成可預期的服務行為。服務可以等待、排隊、拒絕、降級或取樣，但這些策略應由程式明確決定，而不是讓 goroutine、channel 或 memory 自行失控。

## 預計補充內容

1. 本地 rate limiter 和 channel buffer 的差異。
2. token bucket、semaphore 與簡化 ticker limiter 的概念。
3. HTTP handler、background worker、publisher 的不同限速策略。
4. timeout、context cancel 與 `429` / `503` 回應。
5. rate limit 行為如何用 table-driven test 驗證。

## 與 Backend 教材的分工

本章只處理 Go process 內的速率控制。API gateway、load balancer、service mesh、broker quota 與跨節點流量治理會放在 [Backend：部署平台與網路入口](../../backend/05-deployment-platform/)。
