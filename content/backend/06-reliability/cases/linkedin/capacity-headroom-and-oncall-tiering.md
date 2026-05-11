---
title: "LinkedIn：Capacity Headroom 與 On-call 分層"
date: 2026-05-07
description: "把容量預測與值班分層綁在一起，降低高峰時段的升級混亂與恢復延遲。"
weight: 31
tags: ["backend", "reliability", "case-study"]
---

LinkedIn 案例的核心責任是讓容量治理與 on-call 分工一起運作。高流量服務的穩定性不只靠擴容，還靠清楚的接手邏輯。

## 問題場景

當流量逼近上限時，技術瓶頸與協作瓶頸會同時出現。若只有容量模型，沒有分層值班，恢復節奏仍會失控。

## 決策機制

| 機制                  | 核心問題         | 交付結果       |
| --------------------- | ---------------- | -------------- |
| Headroom 預算         | 何時進入風險區   | 擴容與限流門檻 |
| Primary/Secondary/SME | 何時由誰接手     | 升級路徑       |
| 自動化壓測            | 模型是否貼近現況 | 驗證循環       |

## 可觀測訊號

| 訊號                    | 判讀重點               | 對應章節                                                        |
| ----------------------- | ---------------------- | --------------------------------------------------------------- |
| replication latency     | 是否接近容量邊界       | [6.9](/backend/06-reliability/capacity-cost/)                   |
| on-call handoff latency | 分層交接是否順暢       | [8.12](/backend/08-incident-response/ic-handoff-long-incident/) |
| load-test drift         | 模型與真實壓力是否偏移 | [6.2](/backend/06-reliability/load-testing/)                    |

## 下一步路由

把容量假設寫進 [6.22](/backend/06-reliability/steady-state-definition/)，再把交接規則對齊 [8.2](/backend/08-incident-response/incident-command-roles/)。
