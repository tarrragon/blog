---
title: "5.4 service discovery"
date: 2026-04-23
description: "整理 endpoint discovery 與 DNS"
weight: 4
---

## 大綱

- DNS / registry
- [Internal Endpoint](../knowledge-cards/internal-endpoint/) discovery
- failure [fallback](../knowledge-cards/fallback)

## 定位

Service discovery 只處理「怎麼找到目前可用的服務實例」。如果問題已經變成設定分發、版本切換或來源開關，應改看 [Config Rollout](../knowledge-cards/config-rollout/) 或部署平台其他章節。
