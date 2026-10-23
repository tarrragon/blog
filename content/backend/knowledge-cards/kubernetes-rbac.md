---
title: "Kubernetes RBAC（角色型存取控制）"
date: 2026-10-23
description: "要決定誰能對叢集裡的哪些物件做什麼、或查某個帳號為什麼被拒絕或為什麼權限過大時，查 Kubernetes RBAC 的 Role、ClusterRole、binding 與動詞資源的組成"
weight: 456
tags: ["backend", "kubernetes", "security", "access", "knowledge-card"]
---

Kubernetes RBAC（Role-Based Access Control）是 API server 判斷「這個已通過認證的身分，能不能對這個物件做這個動作」的機制：權限寫成「哪些動詞（verb，例如 `get`、`list`、`create`、`delete`）可以作用在哪些資源（resource，例如 `pods`、`secrets`、`nodes`）」，收在 Role 或 ClusterRole 裡，再用 RoleBinding 或 ClusterRoleBinding 把它綁給使用者、群組或 service account。可先對照 [Pod](/backend/knowledge-cards/pod/) 與 [Namespace（命名空間）](/backend/knowledge-cards/namespace/)。

## 概念位置

RBAC 位在認證之後：誰在呼叫 API（使用者、群組、service account）由認證決定，雲端託管的叢集通常把這一步交給雲端的 IAM；RBAC 決定這個身分在叢集裡能做什麼。Role 與 RoleBinding 只在一個 [namespace](/backend/knowledge-cards/namespace/) 裡生效，ClusterRole 與 ClusterRoleBinding 作用於整個叢集或叢集層級的資源（節點、namespace 本身）。最小權限的原則見 [Least Privilege](/backend/knowledge-cards/least-privilege/)。

## 可觀察訊號與例子

- `kubectl` 回 `Error from server (Forbidden): pods is forbidden: User "..." cannot create resource "pods" in API group "" in the namespace "..."`：認證通過、RBAC 拒絕，訊息裡寫出了被拒的動詞、資源與 namespace。
- `kubectl auth can-i create pods --namespace=<namespace>` 回 `yes` 或 `no`，用來確認自己的帳號有沒有某個權限；管理員加 `--as=<user>` 替別人查。
- 能在某個 namespace `create` `pods` 的身分，能用 [Privileged Container](/backend/knowledge-cards/privileged-container/) 取得節點的 root 權限（除非 [Pod Security Admission](/backend/knowledge-cards/pod-security-admission/) 擋下），所以 `pods` 的 `create` 是敏感權限，不只是「能部署」。

## 設計責任

權限綁給群組而不是個人，人員異動在群組裡處理；ClusterRoleBinding 綁 `cluster-admin` 的對象要逐一列得出來，因為它涵蓋叢集裡的一切。內建的 `edit`、`admin` 這類 ClusterRole 範圍很寬，綁在 namespace 層的 RoleBinding 上可以把範圍收在那個 namespace。service account 的權限常被忽略：跑在 Pod 裡的程式用的就是它，權限過大時，那個 Pod 被入侵等於持有那份權限。

## 鄰卡

- [Pod Security Admission](/backend/knowledge-cards/pod-security-admission/) — RBAC 允許建 Pod 之後，決定這個 Pod 的安全設定能不能被接受
- [Privileged Container](/backend/knowledge-cards/privileged-container/) — 能建 Pod 的權限最需要防的那一種 Pod
- [Least Privilege](/backend/knowledge-cards/least-privilege/) — RBAC 設計的原則
