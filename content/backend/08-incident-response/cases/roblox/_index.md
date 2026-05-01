---
title: "Roblox"
date: 2026-05-01
description: "Roblox 73 小時事故時間線與架構脈絡"
weight: 6
---

Roblox 2021 的 73 小時事故是 Consul 流量模式 + long-tail recovery 的教學標竿。事故 post-mortem 詳細揭露根因發現過程、適合作為「為何根因難找」「為何 recovery 比預期慢」的敘事範本。

## 規劃重點

- Consul 流量模式：streaming + 大量 watch 的非預期行為
- 根因發現延遲：72 小時內為何無法定位 streaming 是兇手
- Long-tail recovery：服務恢復後為何效能未恢復、cache cold start 影響
- 廠商協作：HashiCorp 介入時機、第三方協助的 IR 流程
- Postmortem 公開度：Roblox 罕見的詳細工程敘事

## 預計收錄事故

| 年份 | 事故           | 教學重點                               |
| ---- | -------------- | -------------------------------------- |
| 2021 | 73 小時 outage | 根因難尋、long-tail recovery、廠商協作 |

## 引用源

待補（Roblox Tech blog post-mortem URL）。
