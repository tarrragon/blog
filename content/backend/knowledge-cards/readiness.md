---
title: "Readiness"
tags: ["就緒檢查", "Readiness"]
date: 2026-04-23
description: "說明 instance 何時可以安全接收流量，以及 readiness 如何和部署平台協作"
weight: 11
---

Readiness 的核心概念是「instance 是否已準備好接收正式流量」。部署平台或 load balancer 會根據 readiness 訊號決定是否把 request 導到該 instance。 可先對照 [Redelivery Loop](/backend/knowledge-cards/redelivery-loop/)。

## 跟其他概念的關係

Readiness 是 application 與平台之間的流量合約。Application 啟動成功只代表 process 存活；readiness 代表必要設定、連線、migration 狀態、背景初始化、cache warmup 或依賴檢查已達到接流量條件。 可先對照 [Redelivery Loop](/backend/knowledge-cards/redelivery-loop/)。

## 可觀察訊號

系統需要 readiness 合約的訊號是部署或擴容期間出現短暫錯誤。常見情境包括 pod 剛啟動就接流量、service discovery 尚未更新、cache 還在 warming、資料庫連線池尚未建立、背景 worker 尚未完成初始化。

## 接近真實網路服務的例子

Kubernetes rolling update 建立新 pod 後，若 readiness 太早通過，新 pod 可能在還沒載入設定時接到 checkout request。正確的 readiness 會等必要依賴可用、設定載入完成、核心路由可處理後再開放流量。

## 判斷條件與後果

Readiness 通過的時機決定新 instance 何時開始接流量。通過得太早（設定還沒載入、連線池還沒建立）時，新 pod 接到 request 卻處理不了，部署或擴容期間出現短暫錯誤。下游依賴的深度檢查放進 readiness 時，下游一次短暫波動讓所有 instance 同時變成 not ready，平台把流量全部撤走，下游的小波動擴大成整個服務不接流量。liveness 判斷的是 process 是否要重啟，readiness 判斷的是 instance 是否接流量，兩者混用時，暫時不能接流量的 instance 被重啟。所以 readiness 只反映接流量所需的最小條件。
