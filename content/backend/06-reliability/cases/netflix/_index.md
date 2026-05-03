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

## 案例定位

Netflix 這個案例在講的是故障注入如何從實驗變成工程制度。讀者要先分辨 steady state、hypothesis、blast radius 與回復條件各自扮演的角色，才能理解為什麼 chaos 不是演示，而是驗證服務韌性的方法。

## 判讀重點

當團隊只在 staging 做演練時，先看測試是否真的碰到生產流量的分布與依賴關係。當問題需要更細的干預時，再往 FIT 這種 request-level fault injection 移動，讓故障落在真正會被客戶碰到的路徑上。

## 可操作判準

- 能否先寫出 steady state，再設計實驗
- 能否說清楚 blast radius 與 rollback 條件
- 能否說明為何在 business hour 做 chaos 反而更安全
- 能否判斷問題需要 instance-level 還是 request-level 注入

## 與其他案例的關係

Netflix 把「先驗證再承擔風險」這件事做成制度，和 AWS S3、Cloudflare 這類事故頁形成對照。前者是在可控條件下主動打破假設，後者是在失敗後回頭整理假設，因此兩者一起讀才能看懂 reliability 與 incident response 的分工。

## 代表樣本

- Chaos Monkey 直接驗證實例被殺掉後，服務是否仍能維持 steady state。
- FIT 把故障注入從 instance 級推進到 request 級，讓實驗更貼近真實流量路徑。
- Simian Army 讓不同故障類型有各自的注入面。
- business-hour chaos 讓測試更接近真實營運節奏。
- chaos maturity model 讓團隊知道自己在採用故障注入的哪個階段。
- steady state hypothesis 讓實驗不是演示，而是可證偽的工程判斷。
- latency monkey 讓延遲問題成為可以主動驗證的故障型態。
- janitor / conformity 類工具把環境清理與架構規則也納入韌性管理。

## 引用源

- [Netflix/chaosmonkey](https://github.com/Netflix/chaosmonkey)：Chaos Monkey 的現行開源實作。
- [Netflix/SimianArmy Wiki: Chaos Monkey](https://github.com/Netflix/SimianArmy/wiki/Chaos-Monkey)：Simian Army 舊版 wiki，說明 business-hours chaos 的基本規則。
- [Netflix/SimianArmy](https://github.com/Netflix/SimianArmy)：Simian Army 套件入口，補齊多種 monkey 的整體脈絡。
