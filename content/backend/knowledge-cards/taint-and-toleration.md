---
title: "Taint 與 Toleration"
date: 2026-10-05
description: "節點故障後 Pod 等了幾分鐘才搬走、Pod 排不上某些節點、或看到 node.kubernetes.io/not-ready 這類鍵名時：taint 如何把 Pod 擋在節點外或趕出節點、toleration 如何讓 Pod 容忍它"
weight: 455
tags: ["backend", "deployment", "kubernetes", "knowledge-card"]
---

Taint 與 Toleration 的核心概念是「節點宣告不歡迎哪些 Pod，Pod 宣告能容忍哪些宣告」。Taint 是加在節點上的標記，帶一個效果：`NoSchedule` 不讓新 Pod 排上來，`NoExecute` 連已經在上面的 Pod 都要驅逐。Toleration 是寫在 [Pod](/backend/knowledge-cards/pod/) 上的宣告，表示它可以容忍某個 taint，`NoExecute` 的 toleration 還可以設定容忍多久。可先對照 [Control Loop（控制迴圈）](/backend/knowledge-cards/control-loop/) 與 [Pod](/backend/knowledge-cards/pod/)。

## 概念位置

Taint 與 toleration 是 Kubernetes 排程與驅逐的規則之一，由控制平面的 [Control Loop](/backend/knowledge-cards/control-loop/) 執行。它有兩種常見用途：管理者手動在節點加 taint，保留節點給特定工作負載（例如只讓帶對應 toleration 的 GPU 工作排上去）；控制平面在節點出狀況時自動加 taint，把 Pod 趕到健康的節點。後一種用途決定了節點故障後 Pod 多久才搬走，和 [Readiness](/backend/knowledge-cards/readiness/) 決定的「多久不送流量」是兩個不同的時間。

## 可觀察訊號與例子

- **節點故障後的等待時間**：節點停止回應約一分鐘後被標成 NotReady，控制平面同時加上 `node.kubernetes.io/not-ready` 或 `node.kubernetes.io/unreachable` 這類 `NoExecute` taint。Pod 預設帶這兩個鍵的 toleration，各容忍 300 秒，所以 Pod 在標成 NotReady 之後約五分鐘才被驅逐、在別的節點重建。用 `kubectl get pod <名稱> -o jsonpath='{.spec.tolerations}'` 可以看到這兩條預設 toleration。
- **Pod 一直 Pending**：`kubectl describe pod` 的事件寫著節點有 Pod 不容忍的 taint，代表可用的節點都帶著 taint，而 Pod 沒有對應的 toleration。
- **縮短或延長搬移等待**：在 Pod 範本裡自己寫這兩個鍵的 toleration、改 `tolerationSeconds`，可以讓狀態可以快速重建的服務更早搬走，或讓搬移代價高的服務多等一會。

實測的時間線見 [Kubernetes 的元件與請求路徑](/backend/05-deployment-platform/vendors/kubernetes/components-and-request-path/)。

## 設計責任

調短 `tolerationSeconds` 會讓節點短暫的網路抖動也觸發大量搬移，調長則讓故障節點上的副本缺席更久，兩者都要配合副本數的餘量決定。保留節點用的 taint 要記錄在叢集的設定文件裡，否則新服務排不上那些節點時，原因不容易查到。
