---
title: "Toxiproxy"
date: 2026-05-01
description: "TCP-level fault injection proxy（Shopify 開源）"
weight: 10
---

Toxiproxy 是 Shopify 開源的 TCP-level fault injection proxy、在 client 與 server 之間插入 proxy、注入 latency / bandwidth / connection drop / partition。適合 integration test 中模擬網路故障。

## 適用場景

- Integration test 中模擬網路故障
- TCP-level 細粒度 fault injection
- Database / cache / broker 連線故障測試
- CI 中 reproducible chaos

## 不適用場景

- 應用層 chaos（不是 pod kill / CPU stress）
- Production chaos（用 Chaos Mesh / Gremlin）

## 跟其他 vendor 的取捨

- vs `chaos-mesh` NetworkChaos：Toxiproxy CI-friendly；Chaos Mesh production-oriented
- vs Pumba（Docker-only chaos）：Toxiproxy 跨平台 TCP

## 預計實作話題

- Toxic types（latency / bandwidth / slow_close / timeout / slicer）
- API 與 client SDK（Go / Ruby / Python）
- Integration test pattern
- Docker Compose 整合
