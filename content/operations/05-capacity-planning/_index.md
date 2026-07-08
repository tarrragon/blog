---
title: "模組五：容量規劃與壓力測試"
date: 2026-06-20
description: "要準備多少資源才夠 — 壓力測試方法、峰值估算、成本模型、規模拐點的判斷"
weight: 5
tags: ["devops", "capacity-planning", "load-testing", "peak-estimation", "cost-model"]
---

容量規劃的輸入是流量模型，輸出是資源規格與成本——回答「要準備多少資源才夠、多的時候怎麼加、少的時候怎麼省」。這個模組是「規模成長」「突發應對」「成本控制」三條學習路線的交會點。

## 章節

| 章節                                                                          | 回答什麼問題                                        |
| ----------------------------------------------------------------------------- | --------------------------------------------------- |
| [流量模型建立](/operations/05-capacity-planning/traffic-model/)               | 峰均比、到達型態、讀寫比、從 log 抽模型             |
| [峰值估算](/operations/05-capacity-planning/peak-estimation/)                 | 峰值五形狀、歷史倍率階梯、安全係數的飽和曲線根據    |
| [壓力測試工具與方法](/operations/05-capacity-planning/load-testing-tools/)    | 工具選型六維、k6/wrk 定位、怎麼讀延遲分布           |
| [規模拐點判斷](/operations/05-capacity-planning/scaling-inflection-point/)    | 飽和曲線三區間、膝點早期訊號、垂直 vs 水平          |
| [成本模型](/operations/05-capacity-planning/cost-model/)                      | on-demand/reserved/spot、單位請求成本、right-sizing |
| [容器化資源設計](/operations/05-capacity-planning/container-resource-design/) | memory/CPU/磁碟限制、overlay fs、OOMKill 排查       |

## 跨分類引用

- → [運維 模組二 水平擴展](/operations/02-horizontal-scaling/)：「規模成長」路線下一站——算出要多少容量後，怎麼靠加實例把容量長出來
- → [backend 效能容量](/backend/09-performance-capacity/)：Backend 的效能基準和容量估算
- → [運維 模組七 突發流量](/operations/07-burst-traffic/)：突發流量的容量預備
