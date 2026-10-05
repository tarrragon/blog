---
title: "Kubernetes Service"
date: 2026-10-05
description: "在 Kubernetes 裡要讓其他服務連到一組會換 IP 的 Pod、或排查請求為什麼沒有送到 Pod 時：Service 如何用標籤選 Pod、ClusterIP 與 DNS 名稱、EndpointSlice 與 ready 狀態"
weight: 451
tags: ["backend", "deployment", "kubernetes", "knowledge-card"]
---

Kubernetes Service 的核心概念是「替一組 Pod 提供固定的位址」：它用標籤選出一組 [Pod](/backend/knowledge-cards/pod/)，給這組 Pod 一個不變的虛擬 IP（ClusterIP）與 DNS 名稱，送到這個位址的請求被分派到其中一個可以接流量的 Pod。這張卡講的是 Kubernetes 的 `Service` 物件，不是一般語意的「服務」。可先對照 [Service Discovery](/backend/knowledge-cards/service-discovery/) 與 [Load Balancer](/backend/knowledge-cards/load-balancer/)。

## 概念位置

Service 是 Kubernetes 內建的 [Service Discovery](/backend/knowledge-cards/service-discovery/) 加上叢集內的 [Load Balancer](/backend/knowledge-cards/load-balancer/)。Pod 的 IP 隨重建改變，Service 的 IP 與名稱不變，所以服務之間互連時寫的是 Service 名稱。叢集外的 HTTP 流量通常先經過 [Ingress](/backend/knowledge-cards/ingress/)，再由 Ingress controller 依 Service 找到 Pod。Pod 能不能被選進流量池，由 [Readiness](/backend/knowledge-cards/readiness/) 決定。

## 可觀察訊號與例子

- **標籤是 Service 與 Pod 之間唯一的連結**：Service 的 `selector` 寫 `app: web`，就選出所有帶 `app=web` 標籤的 Pod，與 Pod 由誰建立、叫什麼名字無關。selector 打錯一個字，Service 照樣建立成功，只是選不到任何 Pod。
- **EndpointSlice 記錄選到了誰**：`kubectl get endpointslices -l kubernetes.io/service-name=web` 列出 Service 目前選到的 Pod 位址，每個位址帶一個 `ready` 狀態。位址清單是空的代表 selector 選不到 Pod；有位址但全部 `ready=false` 代表 Pod 都沒通過 readiness 檢查。兩種情形透過 Ingress 從外面看都是 503，要靠這裡分辨。
- **DNS 名稱**：同一個 [namespace](/backend/knowledge-cards/namespace/)（叢集裡劃分物件名稱的範圍）裡用 `web` 就連得到，跨 namespace 用 `web.<namespace>.svc.cluster.local`，由叢集裡的 CoreDNS 解析成 ClusterIP。
- **型別決定從哪裡連得到**：`ClusterIP`（預設）只在叢集內可達；`NodePort` 在每個節點開一個 30000–32767 範圍的埠；`LoadBalancer` 由雲端或替代實作建立外部負載平衡器。

實際的分派與 readiness 摘除輸出見 [Kubernetes 的元件與請求路徑](/backend/05-deployment-platform/vendors/kubernetes/components-and-request-path/)。

## 設計責任

Deployment 範本的標籤與 Service 的 selector 要一起設計、一起改。readiness 檢查要反映「這個 Pod 現在能不能處理請求」，Service 依它決定流量去向。服務之間的連線設定寫 Service 名稱，不寫 IP。
