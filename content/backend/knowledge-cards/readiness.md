---
title: "Readiness"
date: 2026-04-23
description: "說明 instance 何時可以安全接收流量，以及 readiness 如何和部署平台協作"
weight: 10
---

Readiness 的核心概念是「instance 是否已準備好接收正式流量」。部署平台或 load balancer 會根據 readiness 訊號決定是否把 request 導到該 instance。

## 概念位置

Readiness 是 application 與平台之間的流量合約。Application 啟動成功只代表 process 存活；readiness 代表必要設定、連線、migration 狀態、背景初始化、cache warmup 或依賴檢查已達到接流量條件。

## 可觀察訊號

系統需要 readiness 合約的訊號是部署或擴容期間出現短暫錯誤。常見情境包括 pod 剛啟動就接流量、service discovery 尚未更新、cache 還在 warming、資料庫連線池尚未建立、背景 worker 尚未完成初始化。

## 接近真實網路服務的例子

Kubernetes rolling update 建立新 pod 後，若 readiness 太早通過，新 pod 可能在還沒載入設定時接到 checkout request。正確的 readiness 會等必要依賴可用、設定載入完成、核心路由可處理後再開放流量。

## 設計責任

Readiness endpoint 要反映接流量所需的最小條件，並且控制下游短暫波動對流量調度的影響。設計時要分清 readiness、liveness 與深度依賴檢查，讓平台能做穩定調度。

## 英文術語對照
- Readiness
- Readiness check
