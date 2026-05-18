---
title: "3.C21 Goldman Sachs：MSK 遷移 with MirrorMaker 2"
date: 2026-05-18
description: "Goldman Sachs Global Investment Research 從 on-prem Kafka 遷到 MSK、用 MM2 同步 topic/ACL/offset、atomic cutover 7 小時完成。"
weight: 21
tags: ["backend", "message-queue", "case-study", "kafka"]
---

這個案例的核心責任是說明 MM2 在 production cutover 的真實 tuning 與 LB 整合 pitfall。

## 觀察

Global Investment Research 把 ~12 microservice / 30 instance 從 on-prem Kafka 遷到 MSK；用 MM2 同步 topic / ACL / consumer group / offset、選擇 atomic cutover、整體耗時 ~7 小時。

## 判讀

把 MM2 預設的 prefixed topic 改成 identical name；遇到 flush timeout（5s → 30s）、request size、NLB idle timeout 350s vs client 540s 衝突。揭露 managed 服務遷移的細節風險集中在「LB / timeout / topic naming」這些 client 端配置、不在 broker 本身。

## 對應大綱

Kafka 進階主題：cross-region MirrorMaker / managed broker 遷移 / ACL 設計。

## 下一步路由

回 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/) 與 [3.C2 VMware → MSK](/backend/03-message-queue/cases/vmware-kafka-to-msk/)。

## 引用源

- [How Goldman Sachs Migrated from On-Premises Apache Kafka to Amazon MSK](https://aws.amazon.com/blogs/big-data/how-goldman-sachs-migrated-from-their-on-premises-apache-kafka-cluster-to-amazon-msk/)
