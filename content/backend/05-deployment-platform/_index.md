---
title: "模組五：部署平台與網路入口"
date: 2026-04-22
description: "整理 Kubernetes、systemd、load balancer、container 與服務生命週期合約"
weight: 5
---

部署平台模組的核心目標是說明服務如何和外部調度、網路入口與資源限制對齊。語言教材會處理 graceful shutdown、health/readiness endpoint 與 signal handling；本模組負責平台設定與操作語意。

## 暫定分類

| 分類              | 內容方向                                             |
| ----------------- | ---------------------------------------------------- |
| Container         | image build、runtime config、resource limit          |
| Kubernetes        | deployment、pod lifecycle、probe、rolling update     |
| systemd           | service unit、restart policy、signal、journal        |
| Load balancer     | idle timeout、draining、health check、sticky session |
| Service discovery | endpoint discovery、DNS、config rollout              |
| Runtime config    | environment variable、secret、feature flag           |

## 與語言教材的分工

語言教材處理程式內的生命週期與訊號。Backend deployment 模組處理 Kubernetes、systemd、load balancer 與 container 平台如何觸發、解讀與限制這些訊號。

## 相關語言章節

- [Go 進階：graceful shutdown 與 signal handling](../../go-advanced/06-production-operations/graceful-shutdown/)
- [Go 進階：健康檢查與診斷 endpoint](../../go-advanced/06-production-operations/health-diagnostics/)
- [Go 進階：Kubernetes、systemd 與 load balancer 合約](../../go-advanced/07-distributed-operations/deployment-contracts/)
