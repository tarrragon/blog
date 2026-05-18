---
title: "3.C31 Mozilla Pulse：命名前綴 + ACL 取代 vhost 多租戶"
date: 2026-05-18
description: "Mozilla Pulse 不用 vhost、改用權限 + 命名前綴 (exchange/{user}/*) 做隔離、CloudAMQP 託管、PulseGuardian 管使用者。"
weight: 31
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

這個案例的核心責任是說明多租戶隔離可用「ACL + naming convention」取代 vhost、適合社群協作場景。

## 觀察

Pulse 是 Mozilla 自動化 / 基礎設施工具間的 managed RabbitMQ cluster、用 AMQP 0-9-1 + RabbitMQ 擴充、由 CloudAMQP 託管於 pulse.mozilla.org:5671（AMQP over TLS）。

## 判讀

技術上不需 vhost、改用權限限制 + 命名前綴（`exchange/<username>/*`、`queue/<username>/*`）做隔離。PulseGuardian 跑在 Heroku 管理使用者 / queue / exchange。揭露多租戶隔離不一定要 vhost、權限粒度可以拉到 resource naming 層。

## 對應大綱

RabbitMQ 進階主題：多 vhost + 多租戶（反向案例：用 ACL + naming 取代 vhost）。

## 下一步路由

回 [RabbitMQ vendor 頁](/backend/03-message-queue/vendors/rabbitmq/) 與 [3.C23 Bloomberg vhost 多租戶](/backend/03-message-queue/cases/rabbitmq-bloomberg-multi-tenant-vhost/)（對照）。

## 引用源

- [Mozilla Pulse Wiki](https://wiki.mozilla.org/Auto-tools/Projects/Pulse)
- [Pulse API](https://pulse.mozilla.org/api/)
