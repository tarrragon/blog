---
title: "Microsoft / Azure SRE"
date: 2026-05-01
description: "Microsoft Azure SRE Practices 與 Resilience Patterns"
weight: 13
---

Microsoft Azure 的 SRE 文章與 Resilience patterns 文件是大型雲端供應商的可靠性工程公開素材。教學重點在「企業導向 cloud 的可靠性 patterns 與 governance」。

## 規劃重點

- Azure Well-Architected Framework：Reliability pillar 的設計指導
- Resilience patterns：retry、circuit breaker、bulkhead 的官方範例
- Site Reliability Engineering at Microsoft：內部 SRE 組織與實踐
- Compliance-driven reliability：企業客戶要求下的可靠性 SLA

## 預計收錄實踐

| 議題                       | 教學重點                              |
| -------------------------- | ------------------------------------- |
| Well-Architected Framework | Reliability pillar 結構與審查流程     |
| Resilience Design Patterns | retry / breaker / bulkhead 等實作範例 |
| Azure SRE Engineering      | Microsoft 內部 SRE 演化               |
| Chaos Studio               | Azure 平台原生 chaos 工具             |

## 案例定位

Microsoft 這個案例在講的是企業雲端如何把可靠性寫進架構規範與設計模式。讀者先抓 reliability pillar、self-healing 與 design patterns 的分工，再把它們視為治理語言，而不是單純的文件清單。

## 判讀重點

當服務要面對企業客戶的 SLA 要求時，先看設計模式能否對應 failure mode，再看治理流程是否能把 pattern 真的落到架構審查。當團隊需要做 retry 或 bulkhead 時，重點是能不能選到正確的位置與層級。

## 可操作判準

- 能否從 failure mode 反推適合的 reliability pattern
- 能否把 self-healing 寫成可驗證的設計要求
- 能否把架構審查和 SLA 約束對齊
- 能否把 Azure SRE 實踐轉成團隊可用的治理語言

## 與其他案例的關係

Microsoft 這頁和 Stripe、Google 的差異在於它更偏治理與設計審查，而不是單一事故。讀者若先懂這頁，再看 Azure AD 和 M365，就能把 identity 失效與企業雲端的 reliability pattern 串成同一條理解路徑。

## 代表樣本

- self-healing 把故障轉成可恢復的設計要求，而不是單靠人工補救。
- reliability pillar 讓團隊在架構審查時就對齊失效模式與補救方式。
- retry / circuit breaker / bulkhead 提供可重複使用的設計模式。
- compliance-driven reliability 把 SLA 約束寫進雲端治理。
- chaos studio 讓雲端平台本身提供測試失效的工具。
- Well-Architected Framework 讓可靠性審查變成標準流程。
- health check / retry policy 讓應用層能和平台層恢復節奏對齊。
- governance 語言把企業 SLA 與技術決策連起來。

## 引用源

- [Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/)：Azure 架構中心總入口。
- [Reliability quick links](https://learn.microsoft.com/en-us/azure/well-architected/resiliency/overview)：Azure Well-Architected Reliability 入口。
- [Design for self-healing](https://learn.microsoft.com/en-us/azure/architecture/guide/design-principles/self-healing)：self-healing 與 failover 的官方設計原則。
- [Architecture design patterns that support reliability](https://learn.microsoft.com/en-gb/azure/well-architected/reliability/design-patterns)：可靠性設計模式總覽。
