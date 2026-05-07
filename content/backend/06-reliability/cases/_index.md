---
title: "可靠性服務案例庫"
date: 2026-05-01
description: "按服務組織的 SRE 實踐案例庫，累積架構脈絡與工程文化"
weight: 90
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

## T3 服務

- [spotify](/backend/06-reliability/cases/spotify/)
- [pinterest](/backend/06-reliability/cases/pinterest/)
- [meta](/backend/06-reliability/cases/meta/)
