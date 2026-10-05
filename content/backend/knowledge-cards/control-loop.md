---
title: "Control Loop（控制迴圈）"
date: 2026-10-05
description: "讀到「期望狀態」「reconcile」，或 Kubernetes 的 apply 成功了服務卻沒起來時：控制迴圈如何持續比對期望狀態與實際狀態並修正落差，以及它和只在下指令時比對一次的宣告式工具差在哪"
weight: 453
tags: ["backend", "deployment", "kubernetes", "knowledge-card"]
---

Control Loop（控制迴圈）的核心概念是「持續比對期望狀態與實際狀態，發現落差就動手修正」的程式結構。使用者只描述要什麼（三個副本、這個版本），由控制迴圈負責讓實際狀態追上它，並在之後任何時候偏離時再拉回來。這種只描述結果、不寫步驟的寫法叫宣告式（declarative），比對與修正的動作在 Kubernetes 文件裡叫 reconcile。可先對照 [Control Plane](/backend/knowledge-cards/control-plane/) 與 [Pod](/backend/knowledge-cards/pod/)。

## 概念位置

控制迴圈是 Kubernetes [Control Plane](/backend/knowledge-cards/control-plane/) 的運作方式：控制平面由許多控制迴圈組成，各自負責一種物件：ReplicaSet controller 維持 [Pod](/backend/knowledge-cards/pod/) 的數量、Deployment controller 執行 [Rolling Update](/backend/knowledge-cards/rolling-update/)、node controller 把失聯的節點標成 NotReady、EndpointSlice controller 依 [Readiness](/backend/knowledge-cards/readiness/) 更新 [Kubernetes Service](/backend/knowledge-cards/kubernetes-service/) 的後端清單。Docker Compose 的設定檔同樣是宣告式的，差別在比對的時機：`docker compose up` 只在指令執行時比對一次，控制迴圈在之後的任何時候都持續比對。名稱相近的 [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/) 講的是兩份資料的對帳，是另一件事。

## 可觀察訊號與例子

- **刪掉的 Pod 自己回來**：手動刪掉一個三副本服務的 Pod，幾秒內 ReplicaSet 建立一個新的，事件紀錄是 `SuccessfulCreate`。沒有人下重建的指令。
- **apply 成功不代表服務起來了**：`kubectl apply` 只把期望狀態存進 API server。image 拉不到、資源不足排不上節點，都發生在之後的控制迴圈裡，要看物件的 `status` 與事件。
- **每個控制迴圈只修正它負責的那個量**：ReplicaSet 只維持 Pod 的數量。直接改一個 Pod 的 image，ReplicaSet 不會把它改回範本；改掉一個 Pod 的標籤，ReplicaSet 會另外補一個新 Pod，被改的那個脫離管理。Deployment 會把 ReplicaSet 的副本數改回期望值。所以要改行為就改最上層的 Deployment，手動改下層物件的結果，取決於哪個控制迴圈負責那個欄位。
- **修正前有刻意的等待時間**：控制器在物件一改變時就收到通知，但有些修正會先等一段寬限時間。節點失聯約一分鐘才被標成 NotReady，之後再等約五分鐘才把上面的 Pod 搬走（見 [Taint 與 Toleration](/backend/knowledge-cards/taint-and-toleration/)），用意是避免短暫的抖動觸發大規模搬移。

實測輸出見 [Kubernetes 的元件與請求路徑](/backend/05-deployment-platform/vendors/kubernetes/components-and-request-path/)。

## 設計責任

用控制迴圈管理的系統，變更要改期望狀態（設定檔、Git 裡的 manifest），不直接改實際狀態，否則下一次比對會把手動改動蓋掉。排查問題時從期望狀態與實際狀態的差距讀起：哪個物件的 `status` 追不上 `spec`、對應的控制迴圈留下了什麼事件。
