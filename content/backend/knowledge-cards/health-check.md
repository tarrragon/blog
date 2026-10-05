---
title: "Health Check"
tags: ["健康檢查", "Health Check"]
date: 2026-04-24
description: "說明服務如何對外提供可供平台判斷狀態的健康回應"
weight: 134
---


Health Check 的核心概念是「讓平台用一個簡單回應判斷服務是否值得接流量或是否需要介入」。它是狀態判斷的入口語意，不等於 readiness、liveness 或 diagnostic endpoint 本身。可先對照 [Liveness](/backend/knowledge-cards/health-check-liveness/) 與 [Probe](/backend/knowledge-cards/probe/)。

## 概念位置

Health Check 位在 load balancer、platform、diagnostic endpoint 與 application 之間。平台會依這個回應決定是否導流、是否重啟，或是否需要進一步檢查；同一個回應被拿來做哪一件事，由讀它的平台決定。Kubernetes 把它拆成 [Readiness](/backend/knowledge-cards/readiness/)、[Liveness](/backend/knowledge-cards/health-check-liveness/) 與 [Startup Probe](/backend/knowledge-cards/startup-probe/) 三種探針；Docker 的 `HEALTHCHECK` 只有一個健康狀態，在 Compose 與 `docker run` 下只用來顯示與決定啟動順序、不會因此重啟容器，在 Swarm 模式下則會讓不健康的任務被取代。

## 可觀察訊號

系統需要 health check 的訊號是服務需要一個快速、低成本、可自動化的狀態回應，讓平台不用靠猜測判斷是否正常。

## 接近真實網路服務的例子

Load balancer 以 health check 判斷 instance 能否接新流量；運維工具以 health check 快速確認服務是否仍回應；Kubernetes 會把 health check 的責任拆到 readiness / liveness / startup probe。在 Compose 裡設了 `healthcheck` 與 `restart: unless-stopped` 的容器，回應卡住而程序沒結束時會一直停在 unhealthy、不會被重啟，這是把 health check 誤當成自動恢復最常見的情形。端點要回什麼、探多深見 [Health check endpoint 設計](/operations/04-service-health/health-check-endpoint/)，容器這一層的行為見 [容器的健康檢查](/operations/04-service-health/container-healthcheck/)。

## 設計責任

設計時要讓 health check 保持簡單、穩定、低成本，並且只反映它被設計要回答的問題。更細的流量條件交給 readiness，更細的存活條件交給 liveness，更完整的操作介面交給 diagnostic endpoint。
