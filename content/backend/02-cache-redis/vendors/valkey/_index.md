---
title: "Valkey"
date: 2026-05-01
description: "Redis fork、Linux Foundation 託管、BSD 授權"
weight: 2
---

Valkey 是 2024 年從 Redis 7.2.4 fork 的開源專案、由 Linux Foundation 託管、AWS / Google / Oracle / Ericsson 等支援。維持 Redis API 相容、避免 Redis 授權變動的疑慮。

## 適用場景

- 既有 Redis 使用案例、需要 OSI 認可的開源授權
- 多雲 / 跨平台部署、避免 vendor lock-in
- 開源合規需求（公部門 / 企業政策）

## 不適用場景

- 依賴 Redis Stack 商業 modules（RedisJSON / Search 等）— 部分有 fork 但生態未跟上
- 需要 Redis Inc 商業支援

## 跟其他 vendor 的取捨

- vs `redis`：API 相容、授權自由；功能可能落後 Redis Inc 版本（如新 module）
- vs `dragonflydb`：Valkey 是 Redis 直系；DragonflyDB 是重寫高效能版本

## 預計實作話題

- 從 Redis 遷移
- 授權合規評估
- Module 生態相容性
- 雲端 managed 支援（AWS ElastiCache for Valkey）
