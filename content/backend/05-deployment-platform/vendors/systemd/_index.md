---
title: "systemd"
date: 2026-05-01
description: "Linux init system、VM / 單機 service lifecycle"
weight: 3
---

systemd 是 Linux 主流 init system、管理 service unit、restart policy、signal、journal、socket activation。適合 VM / bare metal 上單機服務、不需要 cluster orchestration 的場景。

## 適用場景

- VM / bare metal 上服務 lifecycle 管理
- 不需要多實例 / cluster orchestration
- 需要與 OS 深度整合（journald / cgroups）
- 邊緣節點 / appliance / 嵌入式

## 不適用場景

- 多實例 cluster（用 k8s）
- 需要 rolling update / canary
- Container 為主的 workflow

## 跟其他 vendor 的取捨

- vs `kubernetes`：systemd 單機；k8s cluster
- vs Docker / podman：可組合（systemd run podman / docker container）
- vs OpenRC / runit：systemd 是主流 distro 預設

## 預計實作話題

- Service unit 設計（Type / Restart / ExecStart）
- Signal handling 與 graceful shutdown
- journald 日誌
- cgroups v2 與 resource limit
- Socket activation
- systemd timer（cron 替代）
