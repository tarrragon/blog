---
title: "Netflix"
date: 2026-05-01
description: "Netflix Chaos Engineering 起源：Simian Army / FIT / 規模化故障注入"
weight: 2
---

Netflix 是 Chaos Engineering 的起源、Chaos Monkey 跟 Simian Army 是領域標準工具的概念來源、FIT（Failure Injection Testing）是大規模 production chaos 的實作範本。教學重點在「故障注入如何作為 first-class 工程實踐」。

## 規劃重點

- Chaos Monkey 起點：在 production 隨機殺實例為何能改進架構
- Simian Army 工具鏈：Latency / Janitor / Conformity 等不同維度的 chaos
- FIT：把 chaos 從 instance 層升級到 request 層、攻擊更精細
- Chaos Maturity Model：團隊採用 chaos 的能力分級
- Steady state hypothesis：chaos 實驗的科學方法基礎

## 預計收錄實踐

| 議題                        | 教學重點                                 |
| --------------------------- | ---------------------------------------- |
| Chaos Monkey                | 起源、規則、為何在 weekday business hour |
| Simian Army                 | 多維度故障注入的設計                     |
| FIT                         | Request-level fault injection 的工程化   |
| Chaos Engineering Manifesto | hypothesis / scope / blast radius 控制   |
| Production chaos vs Staging | 為何 production 才有真實價值             |

## 引用源

待補（Netflix Tech blog / Chaos Engineering 書籍 / O'Reilly principlesofchaos.org）。
