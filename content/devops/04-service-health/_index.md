---
title: "模組四：服務探活與自動恢復"
date: 2026-06-20
description: "服務掛了怎麼自動發現和恢復 — health check 設計、liveness vs readiness、systemd watchdog、process supervisor"
weight: 4
tags: ["devops", "health-check", "liveness", "readiness", "systemd", "auto-recovery"]
---

回答「服務掛了怎麼知道、知道了怎麼自動恢復」。探活是所有自動恢復機制的前提。

## 待寫章節

- [ ] Health check endpoint 設計（什麼算健康、什麼算不健康、check 的深度）
- [ ] Liveness vs Readiness（活著 vs 準備好接流量 — Kubernetes 的兩種 probe）
- [ ] systemd watchdog + 自動重啟（WatchdogSec + Restart=on-failure）
- [ ] Process supervisor 的選型（systemd / supervisord / Docker restart policy）
- [ ] Graceful shutdown（收到 SIGTERM 後的清理流程）

## 跨分類引用

- → [monitoring 模組四 Dashboard DevOps](/monitoring/04-collector/dashboard-devops/)：DevOps dashboard 的服務狀態卡依賴 health check
- → [backend 部署平台](/backend/05-deployment-platform/)：部署平台的 health check 整合
- → [Linux 除錯：服務掛了怎麼自動知道](/linux/debug/service-failure-monitoring/)：本模組的概念（探活、WatchdogSec、Restart=on-failure）在單機 systemd 層的具體實作——`OnFailure=` 鉤子 + 推播、canary 驗證管線
- → [Linux 除錯：ntfy 推送通知](/linux/debug/ntfy-push-notification-service/)：把服務失效告警推到手機的最小可用通道
