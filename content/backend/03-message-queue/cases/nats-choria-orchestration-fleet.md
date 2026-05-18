---
title: "3.C39 Choria：NATS 管 50 萬 server fleet"
date: 2026-05-18
description: "Choria 替代 Puppet MCollective、NATS 單 binary 無 Zookeeper、4GB node 可達 50 萬 server、wildcard + queue group 做 scatter-gather RPC。"
weight: 39
tags: ["backend", "message-queue", "case-study", "nats"]
---

這個案例的核心責任是說明 fire-and-forget RPC + scatter-gather pattern 是 NATS Core 的典型場景。

## 觀察

Choria 是 Puppet MCollective 的現代化替代品、目標管理數萬到數十萬節點的 fleet 同時下指令。評估過多個 broker、選 NATS 因為「單 binary、無 Zookeeper 依賴、Ruby client 品質好」、實測「單 server 300MB RAM 管 2000+ 機器」、4GB 節點可達 50 萬 server。

## 判讀

MCollective 的 fire-and-forget RPC 語意正好對應 NATS Core 的 stateless best-effort + request-reply pattern、用 wildcard subject + queue group 做 parallel scatter-gather RPC。揭露 server orchestration 場景不需要 persistence、Core NATS 已足夠。

## 對應大綱

NATS 進階主題：Request/Reply pattern / Queue groups / Cluster + Supercluster + Leaf node（Choria Federation Broker = 跨地理 federation）。

## 下一步路由

回 [NATS vendor 頁](/backend/03-message-queue/vendors/nats/) 與 [3.1 broker basics](/backend/03-message-queue/broker-basics/)。

## 引用源

- [NATS for the Marionette Collective (Choria)](https://nats.io/blog/nats-for-the-marionette-collective/)
- [Choria Architecture Docs](https://choria.io/docs/concepts/)
