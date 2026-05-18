---
title: "3.C12 Pinterest：Shallow Mirror 優化 MirrorMaker"
date: 2026-05-18
description: "Pinterest 跨 3 region MirrorMaker、原版解壓+重壓造成 CPU/memory 2-10x spike、改 RecordBatch 層淺迭代。"
weight: 12
tags: ["backend", "message-queue", "case-study", "kafka"]
---

這個案例的核心責任是說明 cross-region replication 的 CPU/memory 成本是被低估的工程議題。

## 觀察

Pinterest 三個 AWS region（us-east-1 / us-east-2 / eu-west-1）跑 MirrorMaker v1、原版設計把 record 解壓+重壓、memory 用量 2-10x 於網路 bytes、CPU spike 與 OOM 頻繁。

## 判讀

Shallow Mirror 在 RecordBatch 層淺迭代 + ByteBuffer pointer 共享、避開 deserialize/re-compress。揭露「跨區同步不是純 I/O 問題、是 CPU + memory + 網路三維壓力」。

## 對應大綱

Kafka 進階主題：cross-region MirrorMaker / MirrorMaker 2 配置。

## 下一步路由

回 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/) 與 [3.C1 Meta FOQS](/backend/03-message-queue/cases/meta-foqs-global-migration/)。

## 引用源

- [Pinterest Shallow Mirror](https://medium.com/pinterest-engineering/shallow-mirror-f543b14bb25)
