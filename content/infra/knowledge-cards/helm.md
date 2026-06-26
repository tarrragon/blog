---
title: "Helm"
date: 2026-06-26
description: "Kubernetes 的套件管理工具，用 chart 打包一組 K8s 資源的部署定義"
weight: 50
tags: ["infra", "knowledge-cards"]
---

Helm 是 Kubernetes 的套件管理工具。它用 chart（一組模板檔案 + 預設值）把多個 K8s 資源（Deployment、Service、ConfigMap、Ingress 等）打包成一個可安裝、可升級、可回退的單位。

## 概念位置

Helm 在 K8s 生態裡的角色類似 apt 在 Linux、npm 在 Node.js——把「安裝一個應用」從「逐一 apply 多個 YAML」變成「一條 `helm install` 指令」。chart 可以參數化（values.yaml），同一份 chart 在不同環境用不同參數部署。

公開 chart 從 Artifact Hub 下載。斷網環境裡用 `helm pull` 在外部下載 chart tarball、搬進內網、從本地檔案安裝，或用 Harbor 的 OCI chart 支援當內部 chart registry。

## 可觀察訊號

系統需要 Helm 的訊號是：用 K8s 部署的應用超過 3 個、每個應用由 5+ 個 K8s 資源組成、且需要在多個環境（dev/staging/prod）用不同參數部署同一套定義。如果只有 1-2 個簡單應用、直接 `kubectl apply` 就好。

## 設計責任

使用 Helm 時要決定：chart 的粒度（一個 chart = 一個微服務 or 一整個平台）、values 的組織（per-environment values file）、chart 版本管理（chart version vs app version）、以及升級策略（`helm upgrade --atomic` 失敗自動回退）。

## 鄰卡

- [ECS](/infra/knowledge-cards/ecs/)：ECS 是非 K8s 的容器編排替代
