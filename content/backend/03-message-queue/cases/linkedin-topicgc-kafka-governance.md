---
title: "3.C3 LinkedIn：TopicGC 與 Kafka 治理轉換"
date: 2026-05-07
description: "Kafka topic 從手動治理轉自動治理對叢集的影響。"
weight: 3
---

這個案例的核心責任是說明 queue 系統的轉換也包含 metadata 治理。

## 觀察

LinkedIn 以 TopicGC 清理未使用 topic，降低 Kafka metadata 壓力並改善 produce/consume 效能。

## 判讀

當 queue 規模擴大，僅靠容量擴充不夠，topic 生命週期與治理自動化會成為可靠性關鍵。

## 策略

1. 定義 topic 活躍判準與回收條件。
2. 自動化清理流程並保留稽核紀錄。
3. 監控清理前後的性能與穩定性指標。

## 下一步路由

回 [3.4 consumer design](/backend/03-message-queue/consumer-design/) 與 [6.14 dependency reliability budget](/backend/06-reliability/dependency-reliability-budget/)。

## 引用源

- [TopicGC at LinkedIn](https://engineering.linkedin.com/content/engineering/en-us/blog/2022/topicgc_how-linkedin-cleans-up-unused-metadata-for-its-kafka-clu)
