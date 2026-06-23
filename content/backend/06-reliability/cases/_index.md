---
title: "可靠性服務案例庫"
date: 2026-05-01
description: "按服務組織的 SRE 實踐案例庫，累積架構脈絡與工程文化"
weight: 90
tags: ["backend", "reliability", "case-study"]
---

本案例庫以服務為單位、收錄公開 SRE 實踐（SRE Book / 工程部落格 / 演講 / paper）。每個服務一個資料夾，累積該服務的可靠性工程文化、failure mode 與 chaos / DR 案例。

服務分層依 [模組六 _index](/backend/06-reliability/) 的 T1 / T2 / T3 規劃。重複出現於 06 / 08 的服務（stripe / cloudflare / linkedin）資料夾住在主要教學模組、跨模組以連結互通。

## T1 服務

- [google](/backend/06-reliability/cases/google/)
- [netflix](/backend/06-reliability/cases/netflix/)
- [amazon](/backend/06-reliability/cases/amazon/)
- [stripe](/backend/06-reliability/cases/stripe/)
- [shopify](/backend/06-reliability/cases/shopify/)

## T1 第一批正文（已完成）

| 服務    | 正文入口                                                                                                          | 主題重點                         |
| ------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| Google  | [G1 Error Budget 與 Release Gating](/backend/06-reliability/cases/google/error-budget-policy-and-release-gating/) | 可靠性消耗如何直接決定發布節奏   |
| Netflix | [N1 Steady State、Chaos 與 FIT](/backend/06-reliability/cases/netflix/steady-state-chaos-and-fit/)                | 故障注入如何變成可證偽流程       |
| Amazon  | [A1 Shuffle Sharding 與 Cell 邊界](/backend/06-reliability/cases/amazon/shuffle-sharding-and-cell-boundary/)      | 多租戶故障如何被局部化           |
| Stripe  | [S1 Idempotency 與零停機遷移](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/)      | 交易重試與遷移如何共用一致性模型 |
| Shopify | [H1 BFCM 容量治理與 Game Day](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)                  | 峰值風險如何在活動前被消化       |

## T1 第二批正文（已完成）

| 服務    | 正文入口                                                                                                                  | 主題重點                         |
| ------- | ------------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| Amazon  | [A2 Static Stability 與 Constant Work](/backend/06-reliability/cases/amazon/static-stability-and-constant-work/)          | 控制面失效時資料面如何維持服務   |
| Stripe  | [S2 Canary Deploy 與 Progressive Rollout](/backend/06-reliability/cases/stripe/canary-deploy-and-progressive-rollout/)    | 金流場景的放行節奏與交易指標驅動 |
| Shopify | [H2 Pod Architecture 與 Resiliency Matrix](/backend/06-reliability/cases/shopify/pod-architecture-and-resiliency-matrix/) | 多租戶隔離與系統化失敗模式盤點   |

## T1 深挖批次（已完成）

| 服務    | 正文入口                                                                                                                    | 主題重點                              |
| ------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| Google  | [G2 Postmortem Action Item Closure 治理](/backend/06-reliability/cases/google/postmortem-action-item-closure-governance/)   | 事故教訓如何轉成有 owner 的改進項     |
| Google  | [G3 Toil Budget 與 Automation 投資政策](/backend/06-reliability/cases/google/toil-budget-and-automation-investment-policy/) | 值班壓力如何轉成工程投資決策          |
| Netflix | [N2 Business-Hours Chaos Guardrails](/backend/06-reliability/cases/netflix/chaos-monkey-business-hours-guardrails/)         | business hours 故障注入的安全邊界設計 |
| Netflix | [N3 FIT 證據交接與 Release Gate 回寫](/backend/06-reliability/cases/netflix/fit-failure-injection-evidence-handoff/)        | 故障注入結果如何結構化驅動放行決策    |

## T2 服務

- [linkedin](/backend/06-reliability/cases/linkedin/)
- [honeycomb](/backend/06-reliability/cases/honeycomb/)
- [cloudflare（住於 08）](/backend/08-incident-response/cases/cloudflare/)
- [microsoft](/backend/06-reliability/cases/microsoft/)

## T2/T3 第一批正文（已完成）

| 服務      | 正文入口                                                                                                          | 主題重點                |
| --------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------- |
| LinkedIn  | [L1 Capacity 與 On-call 分層](/backend/06-reliability/cases/linkedin/capacity-headroom-and-oncall-tiering/)       | 容量邊界與值班交接協同  |
| Honeycomb | [HC1 Burn Rate 驅動可靠性](/backend/06-reliability/cases/honeycomb/burn-rate-driven-reliability-operations/)      | 用 SLO 消耗速度驅動行動 |
| Microsoft | [MS1 變更治理與可靠性門檻](/backend/06-reliability/cases/microsoft/change-management-and-reliability-governance/) | 變更分層與 release gate |
| Spotify   | [SP1 平台工程與可靠性契約](/backend/06-reliability/cases/spotify/platform-engineering-and-reliability-contracts/) | 分散團隊共用可靠性基線  |
| Pinterest | [P1 快取可靠性與容量驚奇](/backend/06-reliability/cases/pinterest/cache-reliability-and-capacity-surprises/)      | 命中率崩落時的恢復節奏  |
| Meta      | [M1 Region Failover 邊界治理](/backend/06-reliability/cases/meta/region-failover-and-reliability-boundaries/)     | 跨區擴散與回復順序治理  |

## T2/T3 第二批正文（已完成）

| 服務      | 正文入口                                                                                                                                                  | 主題重點                             |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| LinkedIn  | [L2 Automated Load Testing 與 Capacity Forecasting](/backend/06-reliability/cases/linkedin/automated-load-testing-and-capacity-forecasting/)              | 持續壓測驅動容量預測                 |
| Meta      | [M2 BGP 事故與控制面恢復順序](/backend/06-reliability/cases/meta/bgp-control-plane-recovery-ordering/)                                                    | 回復工具依賴已故障系統的恢復困境     |
| Honeycomb | [HC2 Production Excellence 與 Test in Production](/backend/06-reliability/cases/honeycomb/production-excellence-and-test-in-production/)                  | observability-driven 生產驗證文化    |
| Microsoft | [MS2 Safe Deployment Practices 與 Resilience Patterns](/backend/06-reliability/cases/microsoft/safe-deployment-practices-and-resilience-patterns/)        | ring-based deployment 與韌性設計模式 |
| Spotify   | [SP2 Backstage Service Catalog 與 Reliability Metadata](/backend/06-reliability/cases/spotify/backstage-service-catalog-and-reliability-metadata/)        | service catalog 治理可靠性資訊       |
| Pinterest | [P2 Storage Migration 與 Data Infrastructure Reliability](/backend/06-reliability/cases/pinterest/storage-migration-and-data-infrastructure-reliability/) | 大規模儲存遷移的驗證流程             |

## T3 服務

- [spotify](/backend/06-reliability/cases/spotify/)
- [pinterest](/backend/06-reliability/cases/pinterest/)
- [meta](/backend/06-reliability/cases/meta/)
