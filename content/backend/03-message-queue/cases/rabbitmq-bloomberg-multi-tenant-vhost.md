---
title: "3.C23 Bloomberg：多租戶 vhost + 自助平台化"
date: 2026-05-18
description: "Bloomberg 從幾個團隊推到上百個團隊、靠自助 vhost 註冊跟專用叢集分離應用與 broker。"
weight: 23
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

這個案例的核心責任是說明 broker 服務數百個 team 時、責任邊界該劃在 vhost 層。

## 觀察

Bloomberg 5000+ 工程師、每天數十億筆資料請求、單週 2 億條訊息、尖峰每秒數萬條。RabbitMQ Summit 2019 由 Will Hoy 與 David Liu 共同分享。

## 判讀

把 RabbitMQ 從幾個團隊推到上百個團隊、靠完全受管平台 + 自助 vhost 註冊（vhost 名稱、免費配額、連線端點）。應用與 broker 分離成「專用叢集」、責任邊界劃在 vhost 層。揭露多租戶治理該前置、不是事後補。

## 對應大綱

RabbitMQ 進階主題：多 vhost + 多租戶 / Erlang clustering + datacenter 容災。

## 下一步路由

回 [RabbitMQ vendor 頁](/backend/03-message-queue/vendors/rabbitmq/) 與 [3.C6 Uber Kafka 平台](/backend/03-message-queue/cases/uber-kafka-infrastructure-evolution/)（多租戶對照）。

## 引用源

- [Growing a Farm of Rabbits at Bloomberg](https://www.cloudamqp.com/blog/growing-a-farm-of-rabbits.html)
