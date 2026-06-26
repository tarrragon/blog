---
title: "Harbor"
date: 2026-06-26
description: "開源的 container image registry，支援映像掃描、RBAC、複製，斷網環境取代 Docker Hub 的方案"
weight: 49
tags: ["infra", "knowledge-cards"]
---

Harbor 是開源的 container image registry，由 CNCF 孵化。它在 Docker Registry 的基礎上加了企業級功能：Web UI、角色型存取控制（RBAC）、映像漏洞掃描（內建 Trivy）、映像簽章驗證、以及跨 registry 的映像複製。

## 概念位置

Harbor 在容器生態裡負責「映像的儲存、分發和安全把關」。連網環境裡這個角色通常由 Docker Hub、AWS ECR 或 GCR 擔任。斷網環境沒有公開 registry 可用、Harbor 是 self-hosted 的替代——所有 base image 和應用 image 都推進 Harbor、所有 docker pull 都從 Harbor 拉。

## 可觀察訊號

系統需要 Harbor 的訊號是：團隊開始用容器部署服務、且環境無法連到公開 registry（斷網或受限網路）、或需要在 pull 時自動掃描漏洞。如果只是幾個人在開發機上用 Docker、Docker Registry（無 UI、無掃描）就夠了。

## 設計責任

使用 Harbor 時要決定：project 的組織（按團隊、按環境、按產品線）、使用者認證（本地帳號 or LDAP 整合）、漏洞掃描政策（push 時自動掃、block 有 Critical CVE 的 image）、映像保留政策（保留最近 N 個 tag、自動清理舊 image）、以及 storage backend（本地磁碟或 NFS）。

## 鄰卡

- [ECS](/infra/knowledge-cards/ecs/)：ECS task 從 registry 拉 image
- [Fargate](/infra/knowledge-cards/fargate/)：Fargate task 同樣需要 registry
