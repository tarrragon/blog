---
title: "3.C14 Yelp：Schematizer 自建 Schema Registry"
date: 2026-05-18
description: "Yelp data pipeline 強制所有 message 走 Avro、自建 Schematizer 做 schema evolution 與 topic 自動分配。"
weight: 14
tags: ["backend", "message-queue", "case-study", "kafka"]
---

這個案例的核心責任是說明 schema 治理是 data pipeline 的核心責任、不是 add-on。

## 觀察

Yelp data pipeline 一天數十億訊息、跨數百個 service、數千 schema、用自建 Schematizer 強制所有 message 走 Avro schema、訊息只帶 schema ID。

## 判讀

Schematizer 不只是 schema store、還做 schema evolution compatibility 與 topic 自動分配（不相容 schema 強制新 topic）。揭露 producer / consumer schema 治理要拉到平台層、靠工具強制、不靠人約定。

## 對應大綱

Kafka 進階主題：Schema Registry / Schema evolution。

## 下一步路由

回 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/) 與 [3.7 event contract / replay boundary](/backend/03-message-queue/event-contract-replay-boundary/)。

## 引用源

- [Yelp Schematizer: More than just a schema store](https://engineeringblog.yelp.com/2016/08/more-than-just-a-schema-store.html)
