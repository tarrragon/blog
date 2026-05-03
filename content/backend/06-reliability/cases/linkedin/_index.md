---
title: "LinkedIn"
date: 2026-05-01
description: "LinkedIn Capacity Planning 與 On-call 結構"
weight: 11
---

LinkedIn 是大規模社交平台、capacity planning 與 [on-call](/backend/knowledge-cards/on-call/) 結構的工程文章公開度高、是「中型公司如何規模化 SRE」的教學標竿。

## 規劃重點

- Capacity Planning：跨 region / 跨服務的容量預測方法
- On-call 結構：primary / secondary / SME escalation
- Operability culture：把可運維性納入服務設計門檻
- Internal tooling：LinkedIn engineering blog 公開的內部工具設計

## 預計收錄實踐

| 議題                    | 教學重點                        |
| ----------------------- | ------------------------------- |
| Capacity Planning       | 預測模型、headroom、growth rate |
| On-call Tiers           | 多層 escalation 設計            |
| Site Reliability Eng    | LinkedIn SRE 組織演化           |
| Internal Chaos / Drills | Project Waterbear 等內部演練    |

## 案例定位

LinkedIn 這個案例在講的是中大型平台如何把容量規劃、自動化壓測與 metrics 收集做成可運營的系統。讀者先抓 capacity planning、[on-call](/backend/knowledge-cards/on-call/) tiers 與 self-service metrics 的關係，再看它們怎麼把 operability 變成團隊責任。

## 判讀重點

當 replication latency 上升時，先看 headroom 是否足夠，再看壓測與自動化是否真的覆蓋了常見瓶頸。當 [on-call](/backend/knowledge-cards/on-call/) 需要多層升級時，重點不是階層本身，而是每一層是否知道何時接手、何時回退。

## 可操作判準

- 能否把容量預測連到實際 growth rate
- 能否讓 load testing 自動化到可重用
- 能否把 metrics collection 做成 self-service
- 能否清楚劃分 primary、secondary 與 SME escalation

## 與其他案例的關係

LinkedIn 的焦點是把 operability 變成日常流程，這和 Shopify 的峰值準備、Microsoft 的治理模式、Spotify 的平台化做法都很接近。差別在於 LinkedIn 更強調內部工具與 metrics pipeline，適合拿來當「中型平台如何長大」的範本。

## 代表樣本

- automated load testing 把壓測變成日常流程，而不是臨時活動。
- self-service metrics 讓團隊不用等平台工程師才能看見關鍵訊號。
- [on-call](/backend/knowledge-cards/on-call/) tiers 讓升級與接手邏輯有固定路徑。
- capacity planning 讓 replication latency 與 headroom 直接相連。
- site reliability engineering 讓中型平台開始形成自己的可靠性職能。
- internal tooling 讓 operability 變成平台化能力而不是個人技巧。
- project waterbear 類演練讓內部故障情境能被規律化測試。
- primary / secondary / SME escalation 讓責任與知識分工更清楚。

## 引用源

- [Welcome to the LinkedIn Engineering Blog](https://engineering.linkedin.com/20/welcome-linkedin-engineering-blog)：LinkedIn Engineering Blog 的入口。
- [Taming Database Replication Latency by Capacity Planning](https://engineering.linkedin.com/performance/taming-database-replication-latency-capacity-planning)：容量規劃與 replication latency 的經典案例。
- [Eliminating toil with fully automated load testing](https://engineering.linkedin.com/content/engineering/en-us/blog/2019/eliminating-toil-with-fully-automated-load-testing)：自動化壓測與 operability 的實踐。
- [Scaling the collection of self-service metrics](https://engineering.linkedin.com/metrics/scaling-collection-self-service-metrics)：metrics pipeline 與可運維性基礎。
