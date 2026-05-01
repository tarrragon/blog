---
title: "Stripe"
date: 2026-05-01
description: "Stripe Deploy Strategy / Game Day / Idempotency 實踐"
weight: 4
---

Stripe 是金流場景的可靠性教學標竿、deploy strategy 與 idempotency 設計是 API platform 的工程典範。教學重點在「金流不可重複扣款 / 不可漏扣款」如何透過工程實踐保證。

## 規劃重點

- Deploy strategy：canary / staged rollout 的實作節奏
- Game Day：Stripe 公開的 game day 設計與運作
- Idempotency Key：API 設計層面的 retry safety
- Increasing reliability：從 99% 到 99.999% 的逐階段工程投資
- Capture the flag：內部紅藍演練（這是 Stripe 自有的、不是套 07 的紅藍）

## 預計收錄實踐

| 議題                      | 教學重點                           |
| ------------------------- | ---------------------------------- |
| Idempotency Key           | API 重試安全的工程實作             |
| Game Day                  | 演練設計、scope、後續 action items |
| Canary Deploy             | rollout 節奏、自動 rollback 條件   |
| Database online migration | 高頻交易場景的 schema 變更         |
| Monitoring & Alerting     | 金流場景的訊號設計                 |

## 引用源

待補（Stripe Engineering blog URL、增加可靠性系列文章）。
