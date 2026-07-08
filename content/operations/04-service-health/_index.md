---
title: "模組四：服務探活與自動恢復"
date: 2026-06-20
description: "服務掛了怎麼自動發現和恢復 — health check 設計、liveness vs readiness、systemd watchdog、process supervisor"
weight: 4
tags: ["devops", "health-check", "liveness", "readiness", "systemd", "auto-recovery"]
---

回答「服務掛了怎麼知道、知道了怎麼自動恢復」。探活是所有自動恢復機制的前提——重啟靠它判斷該不該重啟、負載平衡靠它決定要不要送流量、告警靠它知道什麼時候該叫人。這個模組是「單服務營運」路線的第一站，也是模組六 failover 的觸發前提。

## 章節

| 章節                                                                                   | 回答什麼問題                                                  |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| [Health check endpoint 設計](/operations/04-service-health/health-check-endpoint/)     | 端點回什麼算健康、check 要探到多深、依賴要不要一起檢查        |
| [Liveness 與 Readiness](/operations/04-service-health/liveness-vs-readiness/)          | 活著、準備好接流量、啟動中——三種健康對應三種探針              |
| [systemd watchdog 與自動重啟](/operations/04-service-health/systemd-watchdog-restart/) | 單機上主動報活與被動拉起兩套機制、為何先重啟才告警            |
| [Process supervisor 選型](/operations/04-service-health/process-supervisor-selection/) | systemd、supervisord、Docker、Kubernetes 之間按生命週期粒度選 |
| [Graceful shutdown](/operations/04-service-health/graceful-shutdown/)                  | SIGTERM 到 SIGKILL 的 grace period、退場順序、drain 窗口      |

## 跨分類引用

- → [運維 模組三 流量管控](/operations/03-traffic-management/)：「單服務營運」路線下一站——服務活著之後，流量超過處理能力怎麼防過載
- → [運維 模組六 高可用](/operations/06-high-availability/)：failover 的觸發條件是探活，本模組是它的前提
- → [運維 模組一 負載平衡](/operations/01-load-balancing/)：LB 怎麼用 health check 決定路由，是本模組 endpoint 的消費側
- → [monitoring 模組四 Dashboard DevOps](/monitoring/04-collector/dashboard-devops/)：DevOps dashboard 的服務狀態卡依賴 health check
- → [backend 部署平台生命週期契約](/backend/05-deployment-platform/platform-lifecycle-contract/)：startup / readiness / liveness / drain 的平台端契約
- → [Linux 除錯：服務掛了怎麼自動知道](/linux/debug/service-failure-monitoring/)：本模組的概念（探活、WatchdogSec、Restart=on-failure）在單機 systemd 層的具體實作——`OnFailure=` 鉤子 + 推播、canary 驗證管線
- → [Linux 除錯：ntfy 推送通知](/linux/debug/ntfy-push-notification-service/)：把服務失效告警推到手機的最小可用通道
