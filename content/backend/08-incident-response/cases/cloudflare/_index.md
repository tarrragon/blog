---
title: "Cloudflare"
date: 2026-05-01
description: "Cloudflare 全球 edge 事故時間線與架構脈絡"
weight: 2
---

Cloudflare 是 anycast edge 的代表、單一配置 push 即可影響全球流量、是 configuration push 風險 / regex catastrophic backtracking / BGP 信任的教學標竿。Cloudflare 工程部落格公開度極高、post-mortem 細節豐富。

## 規劃重點

- 全球 configuration push 的 blast radius：為何 60 秒內可癱瘓全球流量
- Regex CPU 耗盡：catastrophic backtracking 如何繞過所有 timeout
- BGP 風險：路由洩漏如何把流量吸入錯誤 ASN
- Recovery 設計：為何 configuration rollback 需要 dataplane 層協作

## 預計收錄事故

| 年份 | 事故               | 教學重點                                     |
| ---- | ------------------ | -------------------------------------------- |
| 2019 | Regex CPU 27 分鐘  | catastrophic backtracking、WAF rule 部署流程 |
| 2020 | BGP route leak     | 跨 ASN 信任、網路層事故止血                  |
| 2022 | 配置 push 全球退化 | 變更節奏、staged rollout 的價值              |
| 2023 | R2 outage          | 新服務的 capacity 假設與 dependency 暴露     |

## 引用源

待補（Cloudflare blog、post-mortem URL）。
