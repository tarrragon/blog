---
title: "Ingress"
date: 2026-10-05
description: "要讓叢集外的 HTTP 請求依網域與路徑進到 Kubernetes 裡不同的服務、Ingress 建立了卻連不進去、或 ingress-nginx 結束維護後要換 controller 時：Ingress 物件與 Ingress controller 的分工、IngressClass，以及 Gateway API 的關係"
weight: 452
tags: ["backend", "deployment", "kubernetes", "knowledge-card"]
---

Ingress 的核心概念是「叢集外 HTTP 流量的路由規則」：一個 Ingress 物件寫明哪個 Host、哪個路徑要轉到哪個 [Kubernetes Service](/backend/knowledge-cards/kubernetes-service/)，由叢集裡的 Ingress controller 實際接收流量並照規則轉發。可先對照 [Request Routing](/backend/knowledge-cards/request-routing/) 與 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 概念位置

Ingress 是 Kubernetes 對 [Request Routing](/backend/knowledge-cards/request-routing/) 的標準描述格式，把路由規則與執行路由的反向代理分開：規則是 Ingress 物件，執行者是 Ingress controller（Traefik、NGINX 系列、Envoy 系列等），兩者靠 IngressClass 對應：IngressClass 物件登記叢集裡有哪些 controller，Ingress 用 `ingressClassName` 指定由哪一個處理。多個 HTTP 服務共用同一個對外入口時，只需要一個 [Load Balancer](/backend/knowledge-cards/load-balancer/) 把流量送到 controller。要在入口做驗證、限流與 API 管理時，入口的角色更接近 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 可觀察訊號與例子

- **Ingress 要有 controller 才生效**：叢集裡沒有 Ingress controller 時，Ingress 物件照樣建立成功，`kubectl get ingress` 的 `CLASS` 是 `<none>`、`ADDRESS` 是空的，`kubectl get ingressclass` 回 `No resources found`。有 controller 處理之後，`ADDRESS` 才有值。
- **Host 比對**：規則寫了 `host: web.localhost`，請求的 Host 標頭不符合時 controller 回自己的 404，請求不會到達任何 Pod。
- **後端選不到 Pod**：規則指向的 Service 沒有可接流量的 Pod 時，controller 回 503（Traefik 的內容是 `no available server`），原因要從 Service 的 EndpointSlice 查。
- **controller 的維護狀態**：社群的 ingress-nginx 在 2026 年 3 月結束維護、之後沒有新版本與安全修補；Ingress API 本身沒有棄用，其他 controller 照常支援（見 [Kubernetes 官方公告](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)）。Kubernetes 官方建議新設計改用 Gateway API，它把入口（Gateway）與路由規則（HTTPRoute）拆成兩種物件，分給平台團隊與服務團隊各自管理，並把依標頭、依權重分流寫進標準欄位。

實際的設定與各種失敗回應見 [Kubernetes 的元件與請求路徑](/backend/05-deployment-platform/vendors/kubernetes/components-and-request-path/)，本機叢集各自附了哪種 controller 見 [單機練習用的 Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/local-practice-clusters/)。

## 設計責任

選 controller 時確認它的維護狀態與 Gateway API 支援；路由以外的功能（改寫路徑、限流、驗證）多半寫在 controller 專屬的 annotation（物件 metadata 裡的自由鍵值，由各 controller 自行解讀）裡，換 controller 時要逐條改寫，所以這類設定要記錄它依賴哪一個 controller。
