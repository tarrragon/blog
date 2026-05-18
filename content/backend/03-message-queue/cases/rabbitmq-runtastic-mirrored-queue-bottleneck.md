---
title: "3.C30 Runtastic：Mirrored queue 網路負載瓶頸"
date: 2026-05-18
description: "Runtastic 2020 lockdown 流量暴增、performance test 揭露 mirroring 邏輯把網路元件壓垮、調整 mirroring 配置消除瓶頸。"
weight: 30
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

這個案例的核心責任是說明 mirrored queue 的網路成本被低估、是規模化的隱藏瓶頸。

## 觀察

2020 lockdown 期間 concurrent user 暴增、出現高延遲與服務中斷。Microservice 架構核心是 RabbitMQ。

## 判讀

透過 performance test 發現 mirroring 邏輯把網路元件壓垮、調整 mirroring 配置消除瓶頸、用 RabbitMQ 3.8 Prometheus integration 監控。揭露 mirrored queue 不是免費的可靠性升級、網路成本要量化。也是「為何後來該遷到 Quorum queue」的典型動機。

## 對應大綱

RabbitMQ 進階主題：Mirrored queue → Quorum queue 遷移 / Prefetch + consumer 併發 / 監控觀測。

## 下一步路由

回 [RabbitMQ vendor 頁](/backend/03-message-queue/vendors/rabbitmq/) 與 [3.1 broker basics](/backend/03-message-queue/broker-basics/)。

## 引用源

- [Runtastic RabbitMQ Performance Case Study](https://seventhstate.io/portfolio/portfolio-runtastic/)
