---
title: "3.C19 Wix：Multi-cluster Kafka zero-downtime 遷移"
date: 2026-05-18
description: "Wix metadata 從 5K topic 漲到 20K topic / 200K partition、controller startup 跟 broker stability 受壓垮、分多 cluster 解決。"
weight: 19
tags: ["backend", "message-queue", "case-study", "kafka"]
---

這個案例的核心責任是說明 single mega-cluster 的 metadata scaling ceiling 與分群策略。

## 觀察

Wix cluster metadata 從 2019 年 5K topic / 45K partition 漲到 20K topic / 200K partition、每日 record 從 450M 漲到 2.5B、controller startup 與 broker stability 受 metadata 量壓垮。

## 判讀

不用 MirrorMaker、自建 Replicator service + Migration Orchestrator、用 Kafka topic 當控制平面協調 consumer 切換 + offset mapping；按 SLA 切多 cluster。揭露「topic / partition 數量」是 broker 級別的物理上限、不能無限擴張。

## 對應大綱

Kafka 進階主題：cross-region MirrorMaker / topic 生命週期 / 分層叢集策略。

## 下一步路由

回 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/) 與 [3.C3 LinkedIn TopicGC](/backend/03-message-queue/cases/linkedin-topicgc-kafka-governance/)。

## 引用源

- [Migrating to a Multi-Cluster Managed Kafka with 0 Downtime](https://medium.com/wix-engineering/migrating-to-a-multi-cluster-managed-kafka-with-0-downtime-b936655f888e)
