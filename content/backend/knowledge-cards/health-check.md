---
title: "Health Check"
tags: ["健康檢查", "Health Check"]
date: 2026-04-24
description: "說明服務如何對外提供可供平台判斷狀態的健康回應"
weight: 133
---

Health Check 的核心概念是「讓平台用一個簡單回應判斷服務是否值得接流量或是否需要介入」。它是狀態判斷的入口語意，不等於 readiness、liveness 或 diagnostic endpoint 本身。

## 概念位置

Health Check 位在 load balancer、platform、diagnostic endpoint 與 application 之間。平台會依這個回應決定是否導流、是否重啟，或是否需要進一步檢查。

## 可觀察訊號

系統需要 health check 的訊號是服務需要一個快速、低成本、可自動化的狀態回應，讓平台不用靠猜測判斷是否正常。

## 接近真實網路服務的例子

Load balancer 以 health check 判斷 instance 能否接新流量；運維工具以 health check 快速確認服務是否仍回應；Kubernetes 會把 health check 的責任拆到 readiness / liveness / startup probe。

## 設計責任

設計時要讓 health check 保持簡單、穩定、低成本，並且只反映它被設計要回答的問題。更細的流量條件交給 readiness，更細的存活條件交給 liveness，更完整的操作介面交給 diagnostic endpoint。

