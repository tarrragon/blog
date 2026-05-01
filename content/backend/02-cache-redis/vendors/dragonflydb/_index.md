---
title: "DragonflyDB"
date: 2026-05-01
description: "高效能 Redis / Memcached 相容替代、多核架構"
weight: 4
---

DragonflyDB 是用 C++ 重寫的 in-memory store、Redis / Memcached protocol 相容、原生多核 / shared-nothing 架構，宣稱比 Redis 高 25 倍 throughput。Apache 2.0 → BSL 授權變動。

## 適用場景

- 需要極高 single-instance throughput
- 多核機器上希望充分利用 CPU
- Redis / Memcached drop-in 替換但要 scale up

## 不適用場景

- 需要 Redis 完整 module 生態
- 對授權限制敏感（BSL 非 OSI）
- 偏好 mature 社群與工具支援

## 跟其他 vendor 的取捨

- vs `redis` / `valkey`：DragonflyDB 效能更高、相容性與生態較淺
- vs Garnet（Microsoft）：類似定位的競品

## 預計實作話題

- Shared-nothing 多核架構
- Memory efficiency（vs Redis）
- Redis 相容邊界
- BSL 授權影響
