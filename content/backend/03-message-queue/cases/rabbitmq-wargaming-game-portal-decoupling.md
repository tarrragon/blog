---
title: "3.C33 Wargaming：World of Tanks 戰後 dossier 解耦"
date: 2026-05-18
description: "Wargaming WoT server 全 Linux、戰後 dossier 寫 RabbitMQ、portal 顯示統計而不增 game server load。"
weight: 33
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

這個案例的核心責任是說明 game server / web portal 異步解耦、queue 吸收戰後事件 burst。

## 觀察

World of Tanks server 全 Linux、用 RabbitMQ 作為 web service stack 核心。每場戰鬥結束後玩家 tank dossier 寫入 message queue、讓 game portal 顯示最新統計而不增加 game server load。

## 判讀

Queue 是 game server 與 portal 的解耦邊界、subscription 也走 RabbitMQ。揭露遊戲場景的「戰後事件 burst」適合用 queue 吸收、不該打到 game server 內部狀態。

## 對應大綱

RabbitMQ 進階主題：Federation + Shovel（多 region game server 同步）/ 多 vhost + 多租戶（多遊戲共用 broker）。

## 下一步路由

回 [RabbitMQ vendor 頁](/backend/03-message-queue/vendors/rabbitmq/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [Wargaming Mobilizes with Linux and Open Source (Linux Foundation)](https://www.linuxfoundation.org/blog/blog/wargaming-mobilizes-with-linux-and-open-source)
- [Wargaming Public API](http://ftr.wot-news.com/2014/07/17/wargaming-public-api-part-2/)
