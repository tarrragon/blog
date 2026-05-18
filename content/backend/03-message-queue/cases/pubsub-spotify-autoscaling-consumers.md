---
title: "3.C61 Spotify：Autoscaling Pub/Sub consumer 反效果"
date: 2026-05-18
description: "Spotify 下游失敗時 consumer 不 ack 仍耗 CPU、autoscaling 越拉越高、解法是 exponential backoff 抑制 CPU。"
weight: 61
tags: ["backend", "message-queue", "case-study", "google-pubsub"]
---

這個案例的核心責任是說明「subscription backlog 不等於 consumer healthy」、autoscaling 跟 ack deadline 的耦合風險。

## 觀察

下游 Cloud Storage export 失敗時、consumer 不 ack 仍持續消耗 CPU 處理同批訊息、造成 autoscaling 把 CPU 越拉越高的反效果；解法是 exponential backoff 抑制 CPU 消耗。

## 判讀

「Subscription backlog 不等於 consumer healthy」— 訊息未 ack 累積跟 autoscaling 的耦合風險。揭露 autoscale signal 該看「處理成功率」而非「CPU + backlog」。

## 對應大綱

Pub/Sub 進階主題：Ack deadline / autoscaling signal 設計。

## 下一步路由

回 [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/) 與 [3.5 紅隊章](/backend/03-message-queue/red-team-delivery-layer/)。

## 引用源

- [Autoscaling Pub/Sub Consumers](https://engineering.atspotify.com/2017/11/autoscaling-pub-sub-consumers)
