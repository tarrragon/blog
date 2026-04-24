---
title: "7.5 Kubernetes、systemd 與 load balancer 合約"
date: 2026-04-22
description: "理解部署平台如何影響 Go 服務的 shutdown、health 與資源限制"
weight: 5
---

部署平台合約的核心責任是讓 Go 服務的生命週期和外部調度系統對齊。程式內部需要清楚的 context、shutdown [timeout](/backend/knowledge-cards/timeout/)、[readiness](/backend/knowledge-cards/readiness/)、[health / liveness](/backend/knowledge-cards/health-check-liveness/) 與 memory limit；Kubernetes、systemd、load balancer 或雲端平台則決定這些訊號何時被觸發與如何被解讀。

## 本章目標

學完本章後，你將能夠：

1. 理解 shutdown、[readiness](/backend/knowledge-cards/readiness/) 與 connection draining 的順序
2. 看懂平台 timeout 對 Go server 的影響
3. 分辨 health 與 readiness 的不同責任
4. 把 memory limit 與 Go runtime 的資源管理接在一起
5. 讓部署平台和程式彼此遵守同一份合約

## 前置章節

- [Go 進階：GC 與 memory limit](/go-advanced/03-runtime-profiling/gc-memory-limit/)
- [Go 進階：graceful shutdown 與 signal handling](/backend/knowledge-cards/graceful-shutdown/)
- [Go 進階：健康檢查與診斷 endpoint](/go-advanced/06-production-operations/health-diagnostics/)
- [Backend：Graceful Shutdown](/backend/knowledge-cards/graceful-shutdown/)
- [Backend：Failover](/backend/knowledge-cards/failover/)

## 後續撰寫方向

1. SIGTERM、shutdown timeout、readiness false 與 connection draining 的順序。
2. Kubernetes `terminationGracePeriodSeconds` 與 Go `http.Server.Shutdown` 如何配合。
3. Load balancer idle timeout 如何影響 [WebSocket](/backend/knowledge-cards/websocket/) heartbeat 參數。
4. Container memory limit、Go memory limit 與 OOM killer 之間的關係。
5. systemd restart policy 與 health endpoint 的責任分工。

## 【觀察】平台會主動改變服務生命週期

Go 程式不會在真空裡執行。Kubernetes、systemd、load balancer、container runtime 都會影響服務何時接新請求、何時開始收尾、何時被強制終止。這表示程式不只要「能跑」，還要能跟平台協調。

常見的生命週期訊號有：

- SIGTERM
- readiness false
- HTTP shutdown
- connection draining
- memory pressure

## 【判讀】health 與 readiness 有不同合約

health 通常表示服務自己還活著，readiness 則表示它是否適合接新流量。

- health 可以用來讓平台知道 process 還活著。
- readiness 可以用來讓 load balancer 停止送新請求。

如果兩者混在一起，部署時就容易出現「服務還沒收尾就被塞新流量」或「其實還能接流量卻被誤判下線」的問題。

## 【策略】shutdown 應該是可預期流程

典型的 shutdown 順序是：

1. 接收到停止訊號。
2. 先把 readiness 關掉。
3. 停止接新流量。
4. 讓現有 request / worker / websocket 收尾。
5. 超時後強制結束。

這個順序能讓平台有時間把流量移走，也讓應用有時間清理資源。

## 【執行】資源限制要和 runtime 觀念一起看

container memory limit 不只是部署平台的事，也會影響 Go runtime 的行為。當可用記憶體變少時，應用更需要控制：

- goroutine 數量
- [buffer](/backend/knowledge-cards/buffer/) 大小
- cache 體積
- in-memory [queue](/backend/knowledge-cards/queue/) 長度

如果這些沒有限制，平台的 OOM killer 可能會比你的 [graceful shutdown](/backend/knowledge-cards/graceful-shutdown/) 先來。

## 【延伸】平台合約要被測試

部署平台合約需要在測試或預備環境驗證。至少要確認：

- shutdown 時 request 是否停止接入
- worker 是否有機會收尾
- WebSocket 是否有 close path
- health 與 readiness 是否分工清楚

## 本章不處理

本章不會完整教 Kubernetes 或 systemd 操作。重點是讓 Go 程式設計能清楚暴露平台需要的生命週期訊號。

## 和 Go 教材的關係

這一章承接的是 Go 的 shutdown 與 runtime 限制；如果你要先回看語言教材，可以讀：

- [Go 進階：GC 與 memory limit](/go-advanced/03-runtime-profiling/gc-memory-limit/)
- [Go 進階：graceful shutdown 與 signal handling](/backend/knowledge-cards/graceful-shutdown/)
- [Go 進階：健康檢查與診斷 endpoint](/go-advanced/06-production-operations/health-diagnostics/)
