---
title: "realtime 流派：server 推 client 的對外承諾差異"
date: 2026-07-04
description: "server 推 client 各機制對消費者承諾什麼：持久連線推送的重連與投遞、webhook 的投遞保證與 consumer 責任"
weight: 6
tags: ["backend", "api-design", "realtime"]
---

server 要主動推給 client 的機制分兩種形狀：持久連線（WebSocket、SSE、long-polling）與事件式的 webhook。選型的核心是各機制對消費者承諾了什麼 —— 重連誰負責、訊息會不會漏、投遞保不保證 —— 而不在能不能推。本目錄兩篇分這兩種形狀，各自把承諾攤開、對到消費者形狀。中性選型判準見 [11.2 風格選型總覽](/backend/11-api-design/api-style-selection/)。

| 文章                                                                                  | 主題                                            | 案例支撐 |
| ------------------------------------------------------------------------------------- | ----------------------------------------------- | -------- |
| [持久連線推送](/backend/11-api-design/styles/realtime/realtime-push-mechanisms/)      | WebSocket / SSE / long-polling 的重連與投遞承諾 | C55-C59  |
| [webhook 對外承諾](/backend/11-api-design/styles/realtime/realtime-webhook-contract/) | 投遞保證不是預設、consumer 扛去重 / ack / 對帳  | C60-C63  |
