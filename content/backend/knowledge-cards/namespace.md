---
title: "Namespace（命名空間）"
date: 2026-10-05
description: "看到 kubectl 的 -n、kube-system、default，或跨 namespace 的 Service 名稱連不到時：namespace 劃分物件名稱的範圍、預設用哪一個、對 DNS 名稱與權限的影響"
weight: 454
tags: ["backend", "deployment", "kubernetes", "knowledge-card"]
---

Namespace（命名空間）的核心概念是「Kubernetes 叢集裡劃分物件名稱的範圍」：同一個 namespace 裡兩個同種物件不能同名，不同 namespace 裡可以。多數物件（[Pod](/backend/knowledge-cards/pod/)、Deployment、[Kubernetes Service](/backend/knowledge-cards/kubernetes-service/)）屬於某個 namespace，節點與 namespace 本身這類叢集層級的物件不屬於任何 namespace。可先對照 [Kubernetes Service](/backend/knowledge-cards/kubernetes-service/) 與 [Control Plane](/backend/knowledge-cards/control-plane/)。

## 概念位置

Namespace 是同一個叢集裡切分團隊、環境或元件時最常用的單位。系統元件（CoreDNS、kube-proxy，以及部分發行版的 [Control Plane](/backend/knowledge-cards/control-plane/) 元件）放在 `kube-system`；使用者沒指定時，物件建在 `default`。[Kubernetes Service](/backend/knowledge-cards/kubernetes-service/) 的 DNS 名稱帶著 namespace，存取權限與資源配額也常以 namespace 為單位設定。Namespace 只劃分名稱與管理範圍，不隔離網路：不同 namespace 的 Pod 預設仍然互相連得到，要限制連線另用 NetworkPolicy。

## 可觀察訊號與例子

- **`-n` 指定 namespace**：`kubectl get pods` 只列 `default` 裡的 Pod，`kubectl get pods -n kube-system` 列系統元件，`kubectl get pods -A` 列全部 namespace。物件「不見了」時，先確認查的是不是它所在的 namespace。
- **Service 名稱的完整形式**：`web.default.svc.cluster.local` 依序是 Service 名稱、namespace、固定的 `svc` 與叢集網域。同一個 namespace 裡寫 `web` 就連得到，跨 namespace 至少要寫到 `web.default`。
- **刪除 namespace 會刪除裡面的全部物件**，練習環境常用這個方式一次清掉一組實驗。

`kube-system` 裡有哪些系統元件、Service 的 DNS 名稱怎麼寫，見 [Kubernetes 的元件與請求路徑](/backend/05-deployment-platform/vendors/kubernetes/components-and-request-path/)。

## 設計責任

namespace 的切法要在第一批服務部署前決定（依團隊、依環境或依產品線），因為 Service 名稱、權限設定與監控的分組都會帶著它，之後改切法要同時改這些地方。
