---
title: "Nobl9"
date: 2026-05-01
description: "SLO platform、跨 data source、企業 SLO 治理"
weight: 11
tags: ["backend", "reliability", "vendor"]
---

Nobl9 是商業 SLO 平台、承擔三個責任：跨 data source SLO 統一治理（Datadog / Prometheus / New Relic / CloudWatch / Splunk 等）、error budget + burn rate alerting、organizational SLO governance（service catalog / project / role）。設計取捨偏向「multi-source + governance + OpenSLO standard」、創辦人來自 Google SRE、推動 OpenSLO 標準。

## 本章目標

讀完本章後、你應該能：

1. 在 Nobl9 定義 SLO（SLI / target / time window）
2. 配置 error budget + burn rate alert（multi-window）
3. 設計 composite SLO（跨服務組合）
4. 用 OpenSLO YAML 管 SLO as code
5. 評估 Nobl9 vs Sloth / Pyrra / vendor 內建 SLO

## 最短路徑：5 分鐘把 Nobl9 跑起來

```bash
# 1. 註冊 Nobl9 + connect data source
# TODO: app.nobl9.com、connect Datadog / Prometheus

# 2. 寫 SLO YAML（OpenSLO）
# TODO: SLO spec with service / indicator / objective

# 3. sloctl apply
# TODO: sloctl apply -f slo.yaml
```

## 日常操作與決策形狀

### SLO 定義

子議題：

- SLI（Service Level Indicator）：metric to measure
- Objective：target percentage
- Time window：rolling / calendar
- 對應 [knowledge cards burn-rate](/backend/knowledge-cards/burn-rate/)

### Error budget

子議題：

- Budget = (1 - SLO target) × time window
- Consumed budget / remaining budget
- 跟 release gate 對應（budget 用完 → freeze deploy）

### Burn rate alert

子議題：

- Multi-window multi-burn-rate alert
- Fast burn alert（短期 high rate）+ slow burn alert（長期 low rate）
- 對應 Google SRE burn rate alerting

## 進階主題（按需閱讀）

### Composite SLO

子議題：

- 跨多 service 組合成單一 SLO
- 適合：user journey SLO（不只單一 service）

### OpenSLO 標準

子議題：

- Vendor-neutral SLO spec
- YAML 配置
- 跟 Nobl9 主導
- 對應 vendor lock-in 取捨

### Data source 整合

子議題：

- Datadog / Prometheus / New Relic / CloudWatch / Splunk / AppDynamics / Honeycomb / Lightstep
- 多 source SLO 統一 view
- 對應 [04 observability](/backend/04-observability/) 模組

### Alert routing

子議題：

- 跟 PagerDuty / Opsgenie / Slack 整合
- 跟 [08 incident response](/backend/08-incident-response/) 對應

### Service catalog + governance

子議題：

- Project / Service / SLO 階層
- Role-based access
- Audit log

### SLO as code

子議題：

- sloctl CLI
- YAML version control
- CI integration

## 排錯快速判讀

### SLO calculation 不準

操作原則：SLI query 不對 / data source 延遲。判讀：raw metric vs SLO calculation 比對。

### Alert noise

操作原則：burn rate window 設過短 / threshold 過嚴。

### Data source disconnect

操作原則：API key / network / quota。

### Composite SLO 行為不符預期

操作原則：composite 算法（AND / OR / custom）不對。

## 何時改走其他服務

| 需求形狀                 | 改走                                                    |
| ------------------------ | ------------------------------------------------------- |
| OSS / 預算敏感           | [Sloth](/backend/06-reliability/vendors/sloth/) / Pyrra |
| 單一 vendor 環境         | Datadog SLO / Honeycomb SLO / Grafana SLO               |
| K8s-native CRD           | Pyrra（K8s Operator）                                   |
| 純 Prometheus            | Sloth（Prometheus generator）                           |
| Enterprise + multi-cloud | Nobl9（本頁）                                           |

## 不在本頁內的主題

- OpenSLO 完整 spec
- Nobl9 pricing
- sloctl 完整 CLI reference

## 案例回寫

| 案例方向                                                          | 對應主題     |
| ----------------------------------------------------------------- | ------------ |
| [Google reliability cases](/backend/06-reliability/cases/google/) | SRE SLO 治理 |

**待補 Nobl9 customer case**：企業 SLO 治理採用案例、OpenSLO adopter。

## 下一步路由

- 上游概念：[knowledge cards burn-rate](/backend/knowledge-cards/burn-rate/)
- 平行 vendor：[Sloth](/backend/06-reliability/vendors/sloth/)
- 下游能力：[04 observability](/backend/04-observability/)、[08 incident response](/backend/08-incident-response/)
