---
title: "Docker"
date: 2026-05-01
description: "Container runtime / image 標準"
weight: 2
---

Docker 是最早 popularize container 的工具、提供 build（Dockerfile）/ run / image registry。在 production orchestration 多被 Kubernetes + containerd 取代、但 dev workflow 與 image build 仍是主流。OCI image 是事實標準。

## 適用場景

- Local dev / CI 的 container 工具
- Image build（Dockerfile / BuildKit / Buildx）
- Compose 編排小規模 dev 環境
- Container registry（Docker Hub / private）

## 不適用場景

- Production orchestration（用 k8s）
- 多節點調度（用 k8s / Nomad）
- Rootless / 安全強化場景（看 podman）

## 跟其他 vendor 的取捨

- vs `kubernetes`：Docker 是 runtime / build；k8s 是 orchestration
- vs Podman：Podman 是 daemon-less、rootless 替代
- vs containerd / CRI-O：k8s production 的 container runtime

## 預計實作話題

- Dockerfile best practice（multi-stage / cache / layer）
- BuildKit / Buildx
- Docker Compose 適用場景
- Image registry 選擇
- Image scanning / SBOM
- Docker Desktop 授權變動
