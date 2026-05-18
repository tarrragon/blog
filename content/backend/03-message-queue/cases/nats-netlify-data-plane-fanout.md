---
title: "3.C34 Netlify：NATS 當全球 metrics/logs 統一資料平面"
date: 2026-05-18
description: "Netlify 70K+ 網站、10 億 PV/月、跨多雲、NATS 當 all-purpose data plane fan-out bus、超 RabbitMQ 評估。"
weight: 34
tags: ["backend", "message-queue", "case-study", "nats"]
---

這個案例的核心責任是說明 NATS 作為跨雲 metrics / logs fan-out 平面的選型理由。

## 觀察

Netlify 為 70,000+ 網站、近月 10 億 PV 的全球多雲（Rackspace / AWS / GCP / Digital Ocean）架構建立統一資料平面、把所有服務的 metrics / logs 集中到 NATS 後再分發。評估過 RabbitMQ、最後因為「效能、setup 簡單、client code 乾淨」選 NATS。

## 判讀

把 NATS 當「all-purpose data plane fan-out bus」、用 logrus NATS hook + log-tail 收兩種 producer、用一個 elastinats consumer 訂閱 channel 推到 Elasticsearch。揭露 NATS 在「subject-based fan-out + 多 consumer 訂閱」場景的優勢來自協議極簡。

## 對應大綱

NATS 進階主題：Core NATS vs JetStream（純 Core NATS 做觀測 fan-out）/ Request/Reply pattern / subject-based routing。

## 下一步路由

回 [NATS vendor 頁](/backend/03-message-queue/vendors/nats/) 與 [3.1 broker basics](/backend/03-message-queue/broker-basics/)。

## 引用源

- [Why Netlify chose NATS](https://nats.io/blog/netlify-nats-blog/)
