---
title: "Load Balancer Contract"
tags: ["負載平衡協議", "Load Balancer Contract"]
date: 2026-04-23
description: "說明服務與負載平衡器之間的流量與健康檢查約定"
weight: 0
---

Load Balancer Contract 的核心概念是「服務如何告訴流量入口自己能否安全接流量」。它描述 [health check](health-check/)、排空、切流與超時行為。

## 概念位置

Load Balancer Contract 位在 application、load balancer、ingress 與 service discovery 之間。

## 可觀察訊號

系統需要 load balancer contract 的訊號是流量分散、rolling update、[draining](draining/) 或 [idle timeout](idle-timeout/) 直接影響使用者請求。

## 接近真實網路服務的例子

[health check](health-check/)、readiness、[draining](draining/) 與 [idle timeout](idle-timeout/) 都屬於 load balancer contract；[sticky session](sticky-session/) 則是另一種負載分派策略，應獨立理解。

## 設計責任

Load Balancer Contract 要定義什麼情況可接新流量、什麼情況要排空、切換需要等待多久，以及健康檢查失敗後的處理方式。

