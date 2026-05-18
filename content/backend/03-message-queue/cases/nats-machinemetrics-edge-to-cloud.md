---
title: "3.C37 MachineMetrics：邊緣到雲端工廠資料管線"
date: 2026-05-18
description: "MachineMetrics 跨數百工廠、數千機台、1000Hz 採樣、Kinesis 無法跑在 edge、改 NATS Leaf Node + JetStream + KV + Object Store。"
weight: 37
tags: ["backend", "message-queue", "case-study", "nats"]
---

這個案例的核心責任是說明工業 IoT 完整的 edge-to-cloud NATS 整合（Leaf Node + JetStream + KV + Object Store + Auth）。

## 觀察

跨「數百個客戶廠區、數千台機台」的 Industrial IoT、單機產出最高 1000 Hz 採樣、工廠網路斷斷續續、Kinesis 等 cloud-only 工具無法跑在資源受限 edge 上。

## 判讀

用 Leaf Node 做 hub-and-spoke 把邊緣設備串到雲端、Edge 端用 JetStream 做本地持久化（取代 SQLite）抵抗網路斷線、用 KV store 做 config / 短期 cache、Object Store 派發 WASM 模組、Decentralized Auth 隔離客戶。揭露「broker 的功能集合」決定它能不能取代多套 edge 工具。

## 對應大綱

NATS 進階主題：Cluster + Supercluster + Leaf node / JetStream KV + Object Store / Subject-based ACL + 多租戶。

## 下一步路由

回 [NATS vendor 頁](/backend/03-message-queue/vendors/nats/) 與 [3.C36 Intelecy](/backend/03-message-queue/cases/nats-intelecy-industrial-iot/)（同類對照）。

## 引用源

- [MachineMetrics Customer Story (Synadia)](https://www.synadia.com/customer-stories/machinemetrics)
