---
title: "Fastly"
date: 2026-05-01
description: "Fastly 全球配置 push 事故時間線"
weight: 7
---

Fastly 2021-06 的全球分鐘級配置 push 事故是 edge platform 的客戶配置觸發供應商 bug 的教學標竿。事件揭露了「客戶觸發供應商 bug」這類 IR 議題的特殊性、跟 Cloudflare 配置事故有對照價值。

## 規劃重點

- 客戶配置觸發供應商 bug：誰負責、誰補償、誰公開
- 全球 edge 分鐘級擴散：為何 edge platform 出事規模特別大
- Recovery 機制：客戶配置回退 vs 供應商 hotfix 的取捨
- 通訊責任：上下游服務（Reddit、Amazon、政府網站）受影響時的 status 揭露

## 預計收錄事故

| 年份    | 事故                     | 教學重點                                 |
| ------- | ------------------------ | ---------------------------------------- |
| 2021-06 | 全球分鐘級配置 push 失效 | 客戶配置觸發、edge platform blast radius |

## 引用源

待補（Fastly status / blog post-mortem）。
