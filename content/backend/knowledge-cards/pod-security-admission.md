---
title: "Pod Security Admission（Pod 安全准入）"
date: 2026-10-23
description: "Pod 因為安全設定被拒絕建立、要限制某個 namespace 不能跑 privileged 或掛載主機目錄的 Pod，或評估 kubectl debug 這類需要高權限的工具在叢集裡能不能用時，查 Pod Security Admission 的三個等級與 namespace label"
weight: 457
tags: ["backend", "kubernetes", "security", "knowledge-card"]
---

Pod Security Admission 是 Kubernetes 內建的准入控制器（admission controller，API server 在物件寫入之前檢查它的元件）：Pod 建立時，它依 Pod 所在 [namespace](/backend/knowledge-cards/namespace/) 的 label，檢查這個 Pod 的安全設定符不符合指定的等級，不符合就拒絕或警告。等級來自 Kubernetes 的 Pod Security Standards，分成 `privileged`（不限制）、`baseline`（擋下 [Privileged Container](/backend/knowledge-cards/privileged-container/)、掛載主機目錄、使用主機網路這類明顯的提權設定）與 `restricted`（再要求以非 root 執行、丟掉多數 Linux capability）三級。可先對照 [Kubernetes RBAC](/backend/knowledge-cards/kubernetes-rbac/)。

## 概念位置

[Kubernetes RBAC](/backend/knowledge-cards/kubernetes-rbac/) 決定誰能建 Pod，Pod Security Admission 決定建出來的 Pod 能帶什麼安全設定；兩者都通過，Pod 才寫得進叢集。它取代了 Kubernetes 1.25 移除的 PodSecurityPolicy。等級用 namespace 的 label 設定，每個等級有三種模式：`enforce`（違反就拒絕）、`warn`（允許但回警告）、`audit`（允許但寫進稽核紀錄）。

## 可觀察訊號與例子

- 建 Pod 時回 `Error from server (Forbidden): ... violates PodSecurity "baseline:latest": privileged (container "..." must not set securityContext.privileged=true)`：這個 namespace 設了 `baseline` 的 `enforce`。
- `kubectl get namespace <namespace> --show-labels` 看得到 `pod-security.kubernetes.io/enforce=baseline` 這類 label。
- `kubectl debug node/<node>` 建的 Pod 不論用哪個 profile 都使用主機的行程與網路 namespace（hostPID、hostNetwork）並掛載主機目錄（hostPath），`--profile=sysadmin` 再加上 privileged，所以在設了 `baseline` 或 `restricted` 的 namespace 裡一律被拒；GKE 上給節點除錯用的專用 namespace 怎麼建，見[GCP 上由 MIG 與 GKE 管理的 VM 的管理存取](/infra/03-network-foundation/gke-mig-management-access/)。
- 叢集沒有另外設定預設等級時，沒有 `pod-security.kubernetes.io/enforce` label 的 namespace（包括 `default`）不受限制，等同 `privileged`：特權 Pod 建得進去，能在那裡建 Pod 的帳號就能取得節點的 root 權限。

## 設計責任

一般工作負載的 namespace 至少設 `baseline` 的 `enforce`，能跑 privileged Pod 的 namespace 只留給確實需要的系統元件與維運用途，並用 [Kubernetes RBAC](/backend/knowledge-cards/kubernetes-rbac/) 限制誰能在那裡建 Pod。導入時先設 `warn` 與 `audit` 觀察既有工作負載有哪些會被擋，再切成 `enforce`，否則既有的部署會在下一次重建 Pod 時失敗。

## 鄰卡

- [Kubernetes RBAC](/backend/knowledge-cards/kubernetes-rbac/) — 決定誰能建 Pod，與本卡一起構成建 Pod 的兩道檢查
- [Privileged Container](/backend/knowledge-cards/privileged-container/) — `baseline` 等級擋下的主要對象
- [Namespace（命名空間）](/backend/knowledge-cards/namespace/) — 等級設定的單位
