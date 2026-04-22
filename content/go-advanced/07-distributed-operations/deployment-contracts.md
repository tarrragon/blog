---
title: "7.5 Kubernetes、systemd 與 load balancer 合約"
date: 2026-04-22
description: "理解部署平台如何影響 Go 服務的 shutdown、health 與資源限制"
weight: 5
---

# 7.5 Kubernetes、systemd 與 load balancer 合約

部署平台合約的核心責任是讓 Go 服務的生命週期和外部調度系統對齊。程式內部需要清楚的 context、shutdown timeout、readiness、health 與 memory limit；Kubernetes、systemd、load balancer 或雲端平台則決定這些訊號何時被觸發與如何被解讀。

## 前置章節

- [Go 進階：GC 與 memory limit](../03-runtime-profiling/gc-memory-limit/)
- [Go 進階：graceful shutdown 與 signal handling](../06-production-operations/graceful-shutdown/)
- [Go 進階：健康檢查與診斷 endpoint](../06-production-operations/health-diagnostics/)

## 後續撰寫方向

1. SIGTERM、shutdown timeout、readiness false 與 connection draining 的順序。
2. Kubernetes `terminationGracePeriodSeconds` 與 Go `http.Server.Shutdown` 如何配合。
3. Load balancer idle timeout 如何影響 WebSocket heartbeat 參數。
4. Container memory limit、Go memory limit 與 OOM killer 之間的關係。
5. systemd restart policy 與 health endpoint 的責任分工。

## 本章不處理

本章不會完整教 Kubernetes 或 systemd 操作。重點是讓 Go 程式設計能清楚暴露平台需要的生命週期訊號。
