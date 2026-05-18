---
title: "3.C18 Wix：Greyhound TLLSR 解 consumer 卡住"
date: 2026-05-18
description: "Wix 2000+ microservice 66B msg/day、自建 Greyhound 抽象、TLLSR 框架解 single-partition lag / poison pill / handler 卡住。"
weight: 18
tags: ["backend", "message-queue", "case-study", "kafka"]
---

這個案例的核心責任是說明大規模 multi-tenant Kafka 的營運可視性需求遠超原生 metric。

## 觀察

Wix 2000+ microservice、每天 66 billion Kafka 訊息、用自建 Greyhound（JVM library + polyglot sidecar）抽象 Kafka；troubleshooting 痛點是「卡住的 consumer 看不到原因、只能寫 DB 修復腳本」。

## 判讀

TLLSR 框架（Trace / Lookup / Longest-running / Skip-replay / Redistribute）解 single-partition lag、單筆 poison pill、handler 卡住等情境；consumer lag alert > 30 分鐘觸發。揭露原生 lag metric 無法定位「卡在哪」、需要 message-level trace + 操作介面。

## 對應大綱

Kafka 進階主題：consumer lag / observability / multi-tenant / poison message。

## 下一步路由

回 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/) 與 [3.5 紅隊章](/backend/03-message-queue/red-team-delivery-layer/)。

## 引用源

- [Troubleshooting Kafka for 2000 Microservices at Wix](https://medium.com/wix-engineering/troubleshooting-kafka-for-2000-microservices-at-wix-986ee382fd1e)
