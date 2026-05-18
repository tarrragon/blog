---
title: "3.C26 GoCardless：Hutch + 單一 topic exchange service mesh"
date: 2026-05-18
description: "GoCardless 單一 RabbitMQ cluster 作所有 service 通訊中樞、routing key 用 service.subject.action 格式、JSON 多語言可讀。"
weight: 26
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

這個案例的核心責任是說明小規模時單 vhost + 統一 routing key 規範可作為 service mesh 基礎。

## 觀察

單一 RabbitMQ cluster 作為所有服務之間的通訊中樞、自家 Hutch（Ruby lib）2013 從 production 抽出開源。

## 判讀

routing key 格式 `service.subject.action`（如 `paysvc.payment.chargedback`）、單一 topic exchange、JSON 序列化（多語言可讀）。揭露小規模單 cluster 可以用「routing key 命名規範」取代複雜 exchange 拓樸。

## 對應大綱

RabbitMQ 進階主題：Exchange types 與 routing 設計 / 多 vhost（單 vhost 服務 mesh 的反向案例）。

## 下一步路由

回 [RabbitMQ vendor 頁](/backend/03-message-queue/vendors/rabbitmq/) 與 [3.C23 Bloomberg](/backend/03-message-queue/cases/rabbitmq-bloomberg-multi-tenant-vhost/)（規模化後的對照）。

## 引用源

- [Hutch: Inter-Service Communication with RabbitMQ](https://gocardless.com/blog/hutch-inter-service-communication-with-rabbitmq/)
