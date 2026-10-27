---
title: "Privileged Container（特權容器）"
date: 2026-10-23
description: "在 Pod 設定裡看到 securityContext.privileged=true、要判斷某個除錯或系統元件為什麼需要它，或評估誰能建這種 Pod 等於持有節點 root 權限時，查特權容器能做什麼與它的權限邊界"
weight: 458
tags: ["backend", "kubernetes", "security", "container", "knowledge-card"]
---

特權容器（privileged container）是 `securityContext.privileged: true` 的容器：容器執行環境不替它套用一般容器的隔離限制，它拿得到主機上所有的裝置與 Linux capability，配合掛載主機的根目錄，就能像節點上的 root 一樣讀寫節點的檔案、改節點的設定。可先對照 [Container](/backend/knowledge-cards/container/) 與 [Pod](/backend/knowledge-cards/pod/)。

## 概念位置

一般的 [Container](/backend/knowledge-cards/container/) 靠 namespace、cgroup 與 capability 限制和主機隔開，特權容器把這些限制拿掉，所以它與主機之間實質上沒有隔離邊界。需要它的多半是要直接操作節點的元件：網路外掛、儲存驅動、節點監控代理，以及 `kubectl debug node --profile=sysadmin` 這類節點除錯工具。誰能建特權容器由兩道檢查決定：[Kubernetes RBAC](/backend/knowledge-cards/kubernetes-rbac/) 允許這個身分在那個 namespace 建 Pod，[Pod Security Admission](/backend/knowledge-cards/pod-security-admission/) 允許那個 namespace 接受特權設定。

## 可觀察訊號與例子

- Pod 的 YAML 裡有 `securityContext: { privileged: true }`，常伴隨 `hostPID: true`、`hostNetwork: true` 或掛載 `hostPath: /`。
- `kubectl debug node/<node>` 用預設的 `general` profile 或 `sysadmin` 建出的 Pod 都把節點的根目錄掛在 `/host`，`chroot /host` 之後就是節點的 shell；`--profile=sysadmin` 另外讓它成為特權容器，可以用 `nsenter` 進入節點的 namespace。GKE 上這個做法需要的權限見[GCP 上由 MIG 與 GKE 管理的 VM 的管理存取](/devops/infra/cloud-providers/gcp/gke-mig-management-access/)，專用 namespace 的建法見[GCP 上 MIG 與 GKE 管理存取的實測紀錄](/devops/infra/cloud-providers/gcp/hands-on/mig-gke-access-walkthrough/)。
- GKE Autopilot 這類由雲端管理節點的模式，預設拒絕特權容器，只對列入允許清單的工作負載例外。

## 設計責任

能建特權容器等於持有每個它排得上去的節點的 root 權限，所以這個能力只給負責維運節點的群組，並限制在特定的 namespace。用特權容器除錯之後要刪掉那個 Pod，留著的特權 Pod 是一個隨時能進節點的入口。工作負載本身需要特權時，先查它實際需要的是哪一項 capability，只給那一項（`securityContext.capabilities.add`）通常就夠，不必整個開成特權。

## 鄰卡

- [Pod Security Admission](/backend/knowledge-cards/pod-security-admission/) — `baseline` 以上的等級擋下特權容器
- [Kubernetes RBAC](/backend/knowledge-cards/kubernetes-rbac/) — 決定誰能建 Pod
- [Container](/backend/knowledge-cards/container/) — 一般容器的隔離方式
