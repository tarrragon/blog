---
title: "3.C36 Intelecy：工業 IoT 即時感測 + 多租戶"
date: 2026-05-18
description: "Intelecy 工廠 gateway 接數萬感測器、< 2 秒往返延遲做即時 ML、從 BoltDB 本地快取演進到 JetStream 持久化。"
weight: 36
tags: ["backend", "message-queue", "case-study", "nats"]
---

這個案例的核心責任是說明 edge gateway 從本地 KV 演進到 JetStream 的決策訊號。

## 觀察

Intelecy 在工廠端 gateway 接「數萬個 sensor」、要求 < 2 秒往返延遲做即時 ML 推論、需要多租戶安全隔離與雲端無鎖定方案。Gateway 把 process data 寫進 Synadia Cloud topic。

## 判讀

從 BoltDB 本地快取 → JetStream 持久化的演進、揭露「無 durable layer 時 edge gateway 自己要做存儲、加 JetStream 後可放掉本地 BoltDB」的決策訊號。

## 對應大綱

NATS 進階主題：JetStream stream 設計 / Subject-based ACL + 多租戶（sensor 隔離）。

## 下一步路由

回 [NATS vendor 頁](/backend/03-message-queue/vendors/nats/) 與 [3.C37 MachineMetrics](/backend/03-message-queue/cases/nats-machinemetrics-edge-to-cloud/)（同類對照）。

## 引用源

- [How Intelecy Optimizes Factory Processes with NATS, NGS and JetStream](https://www.synadia.com/blog/how-intelecy-optimizes-factory-processes-with-nats-ngs-and-jetstream)
