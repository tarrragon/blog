---
title: "Probe"
date: 2026-04-23
description: "說明平台如何透過 probe 判斷服務狀態與接流量條件"
weight: 130
---

Probe 的核心概念是「平台主動探測服務狀態的訊號」。它常見於 readiness probe 與 liveness probe，也可能擴展到 startup probe。

## 概念位置

Probe 位在 platform 與 application 之間，讓調度系統知道 instance 是否可接流量、是否仍存活，或是否仍在啟動中。

## 可觀察訊號

系統需要 probe 的訊號是啟動、擴容、故障、健康檢查與回收流程需要自動化判斷。沒有 probe，平台只能用硬編碼規則猜測服務狀態。

## 接近真實網路服務的例子

Kubernetes 會用 probe 決定 instance 是否加入流量池。Readiness probe 檢查能否接流量；liveness probe 檢查 process 是否卡死；startup probe 則可保護啟動較慢的服務。

## 設計責任

設計時要讓 probe 簡單、快速、穩定，並且只反映它自己的責任範圍。Probe 不應該做昂貴查詢或深度業務判斷，否則平台訊號會不穩定。
