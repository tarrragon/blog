---
title: "模組三案例正文"
date: 2026-05-07
description: "訊息佇列與事件傳遞的轉換案例入口。"
weight: 80
---

這個資料夾的核心責任是把 broker、queue 與語義治理的轉換壓力落到可執行判讀。

## 案例列表

| 章節                                                                              | 主題                        | 核心責任                                          |
| --------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------- |
| [3.C1](/backend/03-message-queue/cases/meta-foqs-global-migration/)               | Meta FOQS 全域遷移          | 區域佇列如何升級到 disaster-ready 架構            |
| [3.C2](/backend/03-message-queue/cases/vmware-kafka-to-msk/)                      | VMware Kafka -> MSK         | 自管 broker 轉 managed streaming 的治理重點       |
| [3.C3](/backend/03-message-queue/cases/linkedin-topicgc-kafka-governance/)        | LinkedIn TopicGC            | topic 生命週期治理如何影響叢集可靠性              |
| [3.C4](/backend/03-message-queue/cases/linkedin-kafka-tiered-clusters/)           | LinkedIn Kafka 分層         | 把單叢集使用模式轉成分層叢集治理                  |
| [3.C5](/backend/03-message-queue/cases/slack-job-queue-kafka-redis/)              | Slack Job Queue             | 背景工作通道轉成 Kafka + Redis 組合               |
| [3.C6](/backend/03-message-queue/cases/uber-kafka-infrastructure-evolution/)      | Uber Kafka 基礎設施         | 把事件平台演進成多租戶共享能力                    |
| [3.C7](/backend/03-message-queue/cases/linkedin-kafka-self-healing-automation/)   | LinkedIn Self-healing Kafka | 把手動維運轉成自動修復治理                        |
| [3.C8](/backend/03-message-queue/cases/cloudflare-queues-global-delivery-model/)  | Cloudflare Queues           | 把全球佇列傳遞模型轉成可治理交付路徑              |
| [3.C9](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) | 反例：語義切換失敗          | at-least-once / exactly-once 語義誤配造成資料錯亂 |
| [3.C10](/backend/03-message-queue/cases/contrast-queue-model-by-scale/)           | 對照：規模差異下佇列模型    | 同一佇列模型在不同規模下有不同治理與失敗邊界      |
