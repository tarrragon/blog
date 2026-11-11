---
title: "Helm"
date: 2026-06-26
description: "Kubernetes 的套件管理工具，用 chart 打包一組 K8s 資源的部署定義"
weight: 50
tags: ["infra", "knowledge-cards"]
aliases: ["/infra/knowledge-cards/helm/"]
---

Helm 是 Kubernetes 的套件管理工具。它用 chart（一組模板檔案 + 預設值）把多個 K8s 資源（Deployment、Service、ConfigMap、Ingress 等）打包成一個可安裝、可升級、可回退的單位。跟非 K8s 路線的 [ECS](/devops/infra/knowledge-cards/ecs/) 屬於不同容器編排選型。

## 跟其他概念的關係

Helm 在 K8s 生態裡的角色類似 apt 在 Linux、npm 在 Node.js——把「安裝一個應用」從「逐一 apply 多個 YAML」變成「一條 `helm install` 指令」。chart 可以參數化（values.yaml），同一份 chart 在不同環境用不同參數部署。

公開 chart 從 Artifact Hub 下載。斷網環境裡用 `helm pull` 在外部下載 chart tarball、搬進內網、從本地檔案安裝，或用 [Harbor](/devops/infra/knowledge-cards/harbor/) 的 OCI chart 支援當內部 chart registry。

## 可觀察訊號

系統需要 Helm 的訊號是：用 K8s 部署的應用超過 3 個、每個應用由 5+ 個 K8s 資源組成、且需要在多個環境（dev/staging/prod）用不同參數部署同一套定義。如果只有 1-2 個簡單應用、直接 `kubectl apply` 就好。

## 判斷條件與後果

chart 的粒度一旦定下，各環境的 values file 與版本號都依附在它上面，事後拆分或合併 chart 要連同這些一起改，所以 Helm 的設計從粒度開始。一個 chart 包一整個平台時，改其中一個微服務也要升級整個 chart，整個平台一起重新部署；一個 chart 對一個微服務時，各服務各自升級，代價是 chart 數量多，服務之間的版本相容要另外追蹤。values 依環境各放一份 values file 時，環境之間的差異集中在這幾個檔案裡，對照得出來。chart version 記錄部署定義（模板）的版本，app version 記錄裡面那個應用的版本；只維護其中一個時，從版本號分不出這次變更改的是模板還是應用。`helm upgrade --atomic` 在升級失敗時自動回退到上一個 release；不帶它時，失敗的升級留下標成 failed 的 release，已經套用的資源要手動 rollback。

## 鄰卡

- [ECS](/devops/infra/knowledge-cards/ecs/)：ECS 是非 K8s 的容器編排替代
