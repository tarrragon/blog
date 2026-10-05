---
title: "Pod"
date: 2026-10-05
description: "在 Kubernetes 的輸出或設定裡看到 Pod，要知道它和容器的關係、為什麼它的 IP 與名稱會變、以及誰負責替補它時"
weight: 450
tags: ["backend", "deployment", "kubernetes", "knowledge-card"]
---

Pod 的核心概念是「Kubernetes 排程與執行的最小單位」：一個 Pod 包含一個或多個容器，這些容器共用同一個網路位址、一定排在同一個節點上。Kubernetes 不直接排程容器，排程的是 Pod。可先對照 [Container](/backend/knowledge-cards/container/) 與 [Kubernetes Service](/backend/knowledge-cards/kubernetes-service/)。

## 概念位置

Pod 位在 [Container](/backend/knowledge-cards/container/) 之上、工作負載物件之下。容器是被執行的程式與它的執行環境；Pod 是把幾個必須住在一起的容器包成一個排程單位，給它們一個共用的 IP，讓它們能用 `localhost` 互連、共用掛載的磁碟區。Pod 通常不由使用者直接建立，而是由 ReplicaSet（維持固定數量）或其上層的 Deployment（負責換版本，見 [Rolling Update](/backend/knowledge-cards/rolling-update/)）依 Pod 範本建立。其他服務找到一組 Pod 的方式是 [Kubernetes Service](/backend/knowledge-cards/kubernetes-service/)。

## 可觀察訊號與例子

- **容器重啟與 Pod 替補是兩件事**：Pod 裡的容器掛掉時，kubelet 依 `restartPolicy`（預設 `Always`）在原地重啟它，Pod 的名稱與 IP 不變。Pod 被刪除、被驅逐或所在節點故障時，替補的是一個新名字、新 IP 的 Pod。名稱裡的亂數字尾每次都不同，所以設定與程式不能寫死某個 Pod 的名稱或 IP。
- **名稱帶著它的來源**：由 Deployment 建立的 Pod 叫 `web-8649b5b67b-k6h6m`，前兩段 `web-8649b5b67b` 是它所屬 ReplicaSet 的名稱，其中 `8649b5b67b` 是 Pod 範本的雜湊值；範本一改，新的 Pod 就帶新的雜湊值。
- **READY 與 STATUS 是兩件事**：`STATUS` 是 `Running` 代表容器在跑，`READY` 是 `0/1` 代表 readiness 檢查沒過、不接流量。兩者分開讀，見 [Readiness](/backend/knowledge-cards/readiness/)。
- **一個 Pod 放多個容器的情形**：主要容器旁邊加一個收 log 或代理流量的輔助容器（sidecar），或在主要容器啟動前先跑一次性的初始化容器（init container）。彼此獨立擴縮的服務各放在自己的 Pod。

完整的元件與物件關係見 [Kubernetes 的元件與請求路徑](/backend/05-deployment-platform/vendors/kubernetes/components-and-request-path/)。

## 設計責任

服務要能承受 Pod 隨時被替換：狀態存在 Pod 外面（資料庫、快取、物件儲存），啟動時能自己讀到設定，收到終止訊號時把進行中的請求處理完。每個 Pod 範本要寫 `resources.requests`，排程器依此決定 Pod 放在哪個節點，HPA（[Autoscaling](/backend/knowledge-cards/autoscaling/) 在 Kubernetes 裡的實作）的 CPU 使用率百分比也以它為分母。
