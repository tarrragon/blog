---
title: "Deployment Contract"
date: 2026-04-23
description: "說明服務與部署平台之間的生命週期約定"
weight: 0
---

Deployment Contract 的核心概念是「application 與平台對啟動、存活、接流量與停止方式達成一致」。它把服務生命週期變成可預期的協作規則。

## 概念位置

Deployment Contract 位在 application、container、Kubernetes、systemd 與 rollout control 之間。

## 可觀察訊號

系統需要 deployment contract 的訊號是發版、擴容、回滾或停止流程會影響流量與狀態保存。

## 接近真實網路服務的例子

readiness、shutdown、[draining](../draining/) 與 [resource limit](../resource-limit/) 都屬於 deployment contract。實際發版節奏與批次切換則交給 [rolling update](../rolling-update/) 或 cutover 類卡片處理。

## 設計責任

Deployment Contract 要明確定義何時可接流量、何時應停止接流量、資源不足時如何回應，以及變更失敗時如何回復。
