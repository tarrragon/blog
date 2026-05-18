---
title: "New Relic → Datadog：APM schema 對位 + agent 替換 + dashboard 重建"
date: 2026-05-19
description: "New Relic → Datadog 是 Type A schema diff migration — APM schema / NRQL ↔ Datadog query / agent / dashboard 全要對位；本文涵蓋 6-phase phased translation + 5 個 production 踩雷（NRQL 不直接對位 / synthetic alert 重建 / 計費模型反轉 / dashboard 自動轉失敗 / cross-platform metric 命名）"
weight: 11
tags: ["backend", "observability", "new-relic", "datadog", "apm", "migration", "type-a"]
---

> 本文是跨 vendor migration playbook、cross-link [New Relic](https://newrelic.com/) 跟 [Datadog](/backend/04-observability/vendors/datadog/)。跑 [migration-playbook-methodology 6 維 audit](/posts/migration-playbook-methodology/) 後對映 *Schema = High（NRQL ↔ Datadog query、APM agent 不同）→ Type A phased translation*。

## 問題情境

中型 SaaS 跑 New Relic 3-5 年、production observability 飽和、團隊發現幾個問題：cost 暴漲（per-host APM + custom event + synthetic）、APM trace 對 Kubernetes-native workload 不夠細、跟 PagerDuty / Slack integration 雖然有但 latency 偏高。同期 Datadog 在 K8s monitoring + APM 端深度整合、cost model 在 100-500 host 規模更可預測。

評估遷移時、發現 New Relic → Datadog 不是「換個 agent 就好」 — APM schema、NRQL 查詢語言、custom dashboard、synthetic monitoring rule 全部要 *重新對位*；application code 端的 agent 也要 *完全換 binary*。是 Type A 高 schema 差 migration、不是 drop-in。

## 為什麼遷：cost / k8s-native / vendor consolidation 三條 driver

| Driver               | 觸發場景                                                          |
| -------------------- | ----------------------------------------------------------------- |
| **Cost**             | New Relic per-host pricing + custom event + synthetic 加總爆、Datadog 在 K8s 場景單 host 多 container 更划算 |
| **K8s-native**       | Datadog agent 對 K8s sidecar / DaemonSet / autodiscovery 更深     |
| **Vendor consolidation** | 已用 Datadog log / metric、APM 統一 vendor 降工具切換 cost     |

反向 driver（Datadog → New Relic）：

- New Relic 對 *full-stack observability*（APM + browser + mobile + synthetic）的整合包仍領先
- 已深用 New Relic NRQL 跟 New Relic University 培訓的 organization、不切

## Schema 對位

| New Relic concept    | Datadog 對應                                              |
| -------------------- | --------------------------------------------------------- |
| APM agent (NR Java / Python / Node)    | Datadog agent + APM tracer library     |
| NRQL query           | Datadog query (Metric / Log / Trace)                      |
| Synthetic monitor    | Datadog Synthetic Tests                                   |
| Custom event         | Datadog custom metric / log event                         |
| NRQL alert condition | Datadog monitor                                           |
| New Relic dashboard  | Datadog dashboard (need rebuild)                          |
| Apdex score          | Datadog APM `apm.service.errors` + `apm.service.latency`  |
| Distributed trace    | Datadog APM trace（OpenTelemetry-compatible）             |

## Phase 0：Audit + classify

- 列所有 application 跟對應 NR agent version
- 列所有 NRQL alert / dashboard / synthetic monitor
- 估每月 cost 跟 Datadog 對比

## Phase 1：Schema 對位 + Datadog cluster 建置

- Datadog organization 申請 / IAM integration
- VPC peering / private link (如果用 self-hosted agent)

## Phase 2：Translation pipeline (3-tier)

- Tier 1: Datadog 端 import tool（API-based NRQL → Datadog query 轉換、cover ~40-60%）
- Tier 2: LLM-assisted（剩餘 query / dashboard）
- Tier 3: manual (synthetic / complex correlation)

## Phase 3：Parallel run (dual-agent 4-8 週)

兩個 agent 跑同 application、metric / trace / log 雙端輸出、SOC 比對 detection coverage / alert / dashboard 一致性。

## Phase 4：Cutover + cleanup

- Application 端切 agent
- New Relic license downgrade / cancel
- Decommission timeline 3-6 個月（保留歷史查詢能力）

## Production 故障演練

### Case 1：NRQL 不直接對位 Datadog query

**徵兆**：NRQL `SELECT count(*) FROM Transaction FACET name WHERE duration > 5 SINCE 1 hour ago` 在 Datadog 端需要拆 metric query + filter + group by；翻譯後語意對等但 syntax 完全不同、SOC analyst 學習曲線陡。

**修法**：

1. 翻譯腳本 + LLM-assisted、保留 NRQL 字面 + Datadog query 對照表（runbook）
2. SOC training，1-2 週 hands-on
3. 部分 query 改 *Datadog dashboard widget*、不用直接 query

### Case 2：Synthetic monitor 對位失敗

**徵兆**：NR Synthetic 跑 100+ ping / browser / API test、切 Datadog Synthetic 後發現 *step-based* monitor 對應的「Browser Test」配置複雜、setup 工作量 2-3 倍預估。

**修法**：

1. Pre-cutover 跑 sample synthetic、估真實 setup cost
2. 優先遷 critical synthetic、其他評估退役
3. 用 Datadog API + Terraform 自動化、避免 UI 手動建

### Case 3：Cost 模型反轉

**徵兆**：cutover 後第一個月 Datadog 帳單比 NR 高 30%；breakdown 後發現 *log retention + custom metric series + log indexing* 三個項目超預估。

**修法**：

1. Pre-migration 估 Datadog cost 必須含 *log indexing pricing*（按 indexed event 計）、不是純 ingest
2. Application 端 log scrub PII + sample debug log、降 ingest GB
3. Custom metric cardinality control（tag combination 爆 series count）

### Case 4：Dashboard 自動轉失敗、人工 rebuild 80%

**徵兆**：用 Datadog import tool 跑 NR dashboard、80% widget 缺 / 對應錯；team 估 2 週 dashboard rebuild、實際跑 6-8 週。

**修法**：

1. **接受重建**：production dashboard 必須人工重建、不要期待自動轉
2. **Prioritize**：先重建 SOC critical 30%、其他 deprecate
3. **Migration window 增 4-6 週**：dashboard rebuild 是 underestimated effort

### Case 5：Cross-platform metric 命名差

**徵兆**：NR 端 metric `Apdex/Apdex` 在 Datadog 沒對應、application code 寫死 metric name 失效；alert query 對 NR-specific metric 全失效。

**修法**：

1. Pre-cutover 列所有 NR-specific metric、application code 改用 OpenTelemetry-style metric 命名
2. Datadog query 端 rebuild、用 application-level metric name 而非 vendor-specific
3. 長期：metric naming 用 OpenTelemetry semantic conventions、避免 vendor lock

## Capacity / cost

| 維度                | New Relic                          | Datadog                                   |
| ------------------- | ---------------------------------- | ----------------------------------------- |
| Pricing model       | per-host + custom event / synthetic | per-host APM + log indexing + custom metric |
| K8s-friendly        | 中、autodiscovery 有但配置複雜      | 高、K8s-native autodiscovery first-class   |
| Migration cost      | -                                   | 2-4 FTE × 2-3 個月                        |
| Operational FTE     | 0.3-0.6                             | 0.3-0.6（相當）                            |

## 整合 / 下一步

### 跟 [Datadog → Grafana Stack migration](/backend/04-observability/vendors/datadog/migrate-to-grafana-stack/) 對位

兩種 Datadog 端的後續路線：

- 切到 Datadog 後 *繼續用*（穩定 multi-year）
- 切到 Datadog 後 *再切 Grafana Stack* 省 cost（multi-tool 拆分、Type D）

多數 organization 第一輪 NR → Datadog 已花 2-3 個月、不會立刻再切；至少穩定 1-2 年。

### 跟 OpenTelemetry 對齊

Migration 順便升 OTel 化 application、避免下次 vendor 切換重複工作量。

## 相關連結

- Target vendor：[Datadog](/backend/04-observability/vendors/datadog/)
- 平行 migration playbook (Type A)：[Splunk → Elastic Security](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) / [MySQL → PostgreSQL](/backend/01-database/vendors/mysql/migrate-to-postgresql/)
- 平行 migration playbook (D-type 對位)：[Datadog → Grafana Stack](/backend/04-observability/vendors/datadog/migrate-to-grafana-stack/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)
