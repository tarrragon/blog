---
title: "3.C41 i-flow：NATS 做 OT/IT 跨層整合 bus"
date: 2026-05-18
description: "i-flow 每日 4 億筆 data operation、200+ OT/IT connector、客戶含 Bosch / Sto / Lenze、NATS 當邊緣到 central 整合 bus。"
weight: 41
tags: ["backend", "message-queue", "case-study", "nats"]
---

這個案例的核心責任是說明 OT/IT 整合場景的多工廠 leaf node 拓樸。

## 觀察

i-flow 是工業數據整合平台、每日 4 億筆 data operation、提供 200+ OT/IT 系統 connector、客戶含 Fortune 500 工廠（Bosch、Sto、Lenze）。

## 判讀

用 NATS 當 OT/IT 跨層整合 bus、邊緣端負責 connect / harmonize / publish。揭露多工廠場景該用 leaf node hub-and-spoke、不該每工廠自管 cluster。**注意**：此案例技術細節較淺、引用時要補其他案例的具體 stream / consumer 設計。

## 對應大綱

NATS 進階主題：Cluster + Supercluster + Leaf node（多工廠 leaf node 連 central）。

## 下一步路由

回 [NATS vendor 頁](/backend/03-message-queue/vendors/nats/) 與 [3.C37 MachineMetrics](/backend/03-message-queue/cases/nats-machinemetrics-edge-to-cloud/)（技術細節更深的對照）。

## 引用源

- [i-flow Case Study](https://nats.io/blog/i-flow-case-study/)
