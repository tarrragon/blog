---
title: "3.C27 Zalando：RabbitMQ on AWS 自動化 master selection"
date: 2026-05-18
description: "Zalando 用 sidekick 服務查 AWS API 動態識別 cluster、指定最老 instance 當 master、跨版本升級用 federation 過渡。"
weight: 27
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

這個案例的核心責任是說明雲端 cluster 治理在 K8s 之前的工程模式。

## 觀察

Communication platform 用 RabbitMQ cluster、跑在 EC2 / Docker container 上、用 supervisord 並行 sidekick + RabbitMQ。AWS 帳號限制每 region 5 個 Elastic IP。

## 判讀

自建 sidekick 服務查 AWS API 動態識別 cluster、指定最老 instance 當 master、master 死後晉升下一個最老 node。跨版本升級用 federation 上游接到新 cluster 過渡。揭露「cluster master selection」跟「IP 限制」是雲端部署的早期關鍵限制。

## 對應大綱

RabbitMQ 進階主題：Erlang clustering + network partition / Federation + Shovel / RabbitMQ Cluster Operator（K8s 之前的雲端 cluster 治理）。

## 下一步路由

回 [RabbitMQ vendor 頁](/backend/03-message-queue/vendors/rabbitmq/) 與 [3.1 broker basics](/backend/03-message-queue/broker-basics/)。

## 引用源

- [Rabbit in the Cloud (Zalando Engineering)](https://engineering.zalando.com/posts/2018/02/rabbit-in-the-cloud.html)
